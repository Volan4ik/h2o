import hmac
import hashlib
import urllib.parse
import json
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel
from sqlmodel import select, delete

from src.shared.config import settings
from src.shared.db import session
from src.shared.models import User, WaterLog
from src.domain.hydration.service import HydrationService as HS

router = APIRouter(prefix="/api/webapp", tags=["webapp"])
logger = logging.getLogger(__name__)

# --- Telegram initData validation ---

def _secret_key_for_webapp(bot_token: str) -> bytes:
    """
    WebApp secret key: HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
    (НЕ путать с Login Widget, где просто SHA256(BOT_TOKEN))
    """
    return hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256).digest()

def _try_tokens_for_signature(init_data: str, tokens: list[str]) -> tuple[bool, str | None]:
    """Пробует верифицировать подпись initData по списку токенов.
    Возвращает (ok, matched_token_or_none)."""
    parsed = _parse_init_data(init_data)
    received_hash = parsed.get("hash")
    if not received_hash:
        return False, None
    dcs = _data_check_string_raw(init_data)
    for t in tokens:
        try:
            secret_key = _secret_key_for_webapp(t)
            calc_hash = hmac.new(secret_key, dcs.encode(), hashlib.sha256).hexdigest()
            if calc_hash == received_hash:
                return True, t
        except Exception:
            continue
    return False, None

def _parse_init_data(init_data: str) -> dict:
    # Нужен только чтобы достать hash/auth_date/user как значения
    return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

def _data_check_string_raw(init_data: str) -> str:
    """
    Собираем data_check_string из СЫРОЙ строки init_data:
    - фильтруем параметр hash
    - сортируем пары по имени ключа (левая часть до '=')
    - сами пары НЕ декодируем и не перекодируем
    """
    parts = init_data.split("&")
    pairs = []
    for p in parts:
        # пропускаем ровно hash, signature игнорируем на всякий случай
        if p.startswith("hash=") or p.startswith("signature="):
            continue
        pairs.append(p)
    pairs.sort(key=lambda s: s.split("=", 1)[0])
    return "\n".join(pairs)

def validate_init_data(init_data: str, lifetime: int = 3600) -> dict:
    parsed = _parse_init_data(init_data)

    # hash обязателен
    received_hash = parsed.get("hash")
    if not received_hash:
        raise HTTPException(401, "init_data missing hash")

    # TTL (можно увеличить на время отладки настройкой INITDATA_TTL)
    auth_date = parsed.get("auth_date")
    if auth_date:
        try:
            auth_ts = int(auth_date)
        except ValueError:
            raise HTTPException(401, "bad auth_date")
        delta = datetime.now(timezone.utc) - datetime.fromtimestamp(auth_ts, tz=timezone.utc)
        if delta > timedelta(seconds=lifetime):
            raise HTTPException(401, "init_data expired")

    # data_check_string должен быть собран из сырой строки
    dcs = _data_check_string_raw(init_data)

    # Поддержка нескольких токенов (если один backend обслуживает несколько ботов)
    tokens: list[str] = [settings.BOT_TOKEN]
    if settings.ADDITIONAL_BOT_TOKENS:
        tokens += [t.strip() for t in settings.ADDITIONAL_BOT_TOKENS.split(",") if t.strip()]

    ok, matched = _try_tokens_for_signature(init_data, tokens)
    if not ok:
        logger.warning(
            "init_data signature mismatch: tried %d token(s); auth_date=%s; keys=%s",
            len(tokens), parsed.get("auth_date"), ",".join(sorted(k for k in parsed.keys() if k != "hash"))
        )
        raise HTTPException(401, "bad init_data signature")

    # user как JSON (как делает Telegram)
    user = json.loads(parsed.get("user", "{}")) if "user" in parsed else {}

    # fallback для dev-инструментов (если пришли плоские поля)
    if not user and "user_id" in parsed:
        try:
            user = {"id": int(parsed["user_id"])}
        except Exception:
            pass

    return {"raw": parsed, "user": user}

def _raw_query_param(request: Request, name: str) -> str | None:
    """Возвращает значение параметра из сырой query-строки без декодирования percent-escape.
    Нужен, чтобы подпись Telegram считалась по оригинальной init_data строке.
    """
    try:
        q = request.scope.get("query_string", b"") or b""
        target = name.encode() + b"="
        for part in q.split(b"&"):
            if part.startswith(target):
                # Берём всё после первого '=' как есть
                return part.split(b"=", 1)[1].decode("utf-8", errors="ignore")
    except Exception:
        pass
    return None

def _extract_init_data_raw(
    request: Request,
    x_tg_init_data: str | None = Header(default=None, alias="X-Tg-Init-Data"),
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    init_data: str | None = None,  # на случай передачи через query во время отладки (уже декодированная)
):
    # Пытаемся вытащить initData из нескольких стандартных мест:
    # - "X-Tg-Init-Data" (наш кастомный заголовок)
    # - "Telegram-Init-Data" / "X-Telegram-Init-Data" (встречается в примерах)
    # - "Authorization: tma <initData>" (рекомендация Telegram Mini Apps)
    raw = x_tg_init_data or telegram_init_data or x_telegram_init_data
    if not raw and authorization:
        try:
            scheme, value = authorization.split(" ", 1)
            if scheme.lower() in {"tma", "bearer"}:
                raw = value.strip()
        except ValueError:
            pass
    # Для локальной/вебвью отладки пробуем сырые query-параметры без декодирования
    if not raw:
        for key in ("init_data", "initData", "tgWebAppData"):
            q_raw = _raw_query_param(request, key)
            if q_raw:
                # Значение в query закодировано для URL. Декодируем РОВНО один раз,
                # чтобы восстановить исходную строку initData (как в WebApp).
                raw = urllib.parse.unquote_plus(q_raw)
                break
    # Последний шанс — уже декодированное значение из зависимостей FastAPI
    raw = raw or init_data
    return raw

async def tg_user_dep(
    request: Request,
    x_tg_init_data: str | None = Header(default=None, alias="X-Tg-Init-Data"),
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    init_data: str | None = None,
):
    raw = _extract_init_data_raw(
        request,
        x_tg_init_data=x_tg_init_data,
        telegram_init_data=telegram_init_data,
        x_telegram_init_data=x_telegram_init_data,
        authorization=authorization,
        init_data=init_data,
    )
    if not raw:
        if getattr(settings, "DEV_ALLOW_NO_INITDATA", False):
            return {"raw": {}, "user": {"id": getattr(settings, "DEV_USER_ID", 0)}}
        raise HTTPException(401, "init_data required")
    try:
        return validate_init_data(raw, getattr(settings, "INITDATA_TTL", 3600))
    except HTTPException as e:
        # Логируем причину для диагностики
        logger.warning("auth failed: %s", e.detail)
        raise

@router.get("/debug/auth")
async def debug_auth(
    request: Request,
    x_tg_init_data: str | None = Header(default=None, alias="X-Tg-Init-Data"),
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    init_data: str | None = None,
):
    """DEBUG: возвращает разбор initData и результат валидации. Включать только в DEV!"""
    if not (settings.DEBUG_AUTH or settings.DEV_ALLOW_NO_INITDATA):
        raise HTTPException(404)
    raw = _extract_init_data_raw(
        request,
        x_tg_init_data=x_tg_init_data,
        telegram_init_data=telegram_init_data,
        x_telegram_init_data=x_telegram_init_data,
        authorization=authorization,
        init_data=init_data,
    )
    info: dict = {"received": bool(raw)}
    if not raw:
        info["error"] = "init_data missing"
        return info
    parsed = _parse_init_data(raw)
    info["keys"] = sorted(parsed.keys())
    info["auth_date"] = parsed.get("auth_date")

    # TTL check
    ttl = getattr(settings, "INITDATA_TTL", 3600)
    info["ttl"] = ttl
    if parsed.get("auth_date"):
        try:
            auth_ts = int(parsed["auth_date"])
            delta = datetime.now(timezone.utc) - datetime.fromtimestamp(auth_ts, tz=timezone.utc)
            info["age_seconds"] = int(delta.total_seconds())
            info["expired"] = delta > timedelta(seconds=ttl)
        except Exception:
            info["age_seconds"] = None
            info["expired"] = None

    tokens: list[str] = [settings.BOT_TOKEN]
    if settings.ADDITIONAL_BOT_TOKENS:
        tokens += [t.strip() for t in settings.ADDITIONAL_BOT_TOKENS.split(",") if t.strip()]
    ok, matched = _try_tokens_for_signature(raw, tokens)
    info["signature_ok"] = ok
    info["tokens_tried"] = len(tokens)
    info["matched"] = bool(matched)
    return info

# --- Pydantic модели ---
class LogRequest(BaseModel):
    amount_ml: int

class GoalRequest(BaseModel):
    goal_ml: int

@router.get("/today")
async def today(data=Depends(tg_user_dep)):
    uid = data["user"].get("id")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            u = User(tg_id=uid)
            s.add(u)
            s.commit()
            s.refresh(u)

        start, end = HS.local_bounds(u)
        logs = s.exec(
            select(WaterLog).where(
                (WaterLog.user_id == u.id)
                & (WaterLog.ts_utc >= HS.to_utc(start))
                & (WaterLog.ts_utc < HS.to_utc(end))
            )
        ).all()
        consumed = sum(l.amount_ml for l in logs)
    return {
        "goal_ml": u.goal_ml,
        "consumed_ml": consumed,
        "default_glass_ml": u.default_glass_ml,
    }

@router.post("/log")
async def log(payload: LogRequest, data=Depends(tg_user_dep)):
    uid = data["user"].get("id")
    if payload.amount_ml == 0:
        raise HTTPException(400, "amount_ml != 0 required")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            raise HTTPException(404, "user not found")
        s.add(
            WaterLog(
                user_id=u.id,
                ts_utc=datetime.utcnow().replace(tzinfo=timezone.utc),
                amount_ml=payload.amount_ml,
                source="webapp",
            )
        )
        s.commit()
    return {"ok": True}

@router.get("/stats/days")
async def stats_days(days: int = 7, data=Depends(tg_user_dep)):
    days = max(1, min(31, days))
    uid = data["user"].get("id")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            raise HTTPException(404, "user not found")
        end_local = HS.user_now(u).replace(hour=23, minute=59, second=59, microsecond=0)
        start_local = (end_local - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        logs = s.exec(
            select(WaterLog).where(
                (WaterLog.user_id == u.id)
                & (WaterLog.ts_utc >= HS.to_utc(start_local))
                & (WaterLog.ts_utc <= HS.to_utc(end_local))
            )
        ).all()

    totals = defaultdict(int)
    for l in logs:
        d_local = HS.from_utc(l.ts_utc, u).date().isoformat()
        totals[d_local] += l.amount_ml

    out = []
    cur = start_local.date()
    while cur <= end_local.date():
        iso = cur.isoformat()
        out.append({"date": iso, "ml": totals.get(iso, 0)})
        cur = cur + timedelta(days=1)

    return {"days": out, "goal_ml": u.goal_ml}

@router.post("/goal")
async def update_goal(payload: GoalRequest, data=Depends(tg_user_dep)):
    uid = data["user"].get("id")
    if payload.goal_ml < 500 or payload.goal_ml > 10000:
        raise HTTPException(400, "goal_ml must be between 500 and 10000")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            raise HTTPException(404, "user not found")
        u.goal_ml = payload.goal_ml
        s.add(u)
        s.commit()
    return {"ok": True}

@router.post("/reset")
async def reset(data=Depends(tg_user_dep)):
    uid = data["user"].get("id")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            raise HTTPException(404, "user not found")
        # удалить все записи за сегодня (в локальном дне пользователя)
        start, end = HS.local_bounds(u)
        s.exec(
            delete(WaterLog).where(
                (WaterLog.user_id == u.id)
                & (WaterLog.ts_utc >= HS.to_utc(start))
                & (WaterLog.ts_utc < HS.to_utc(end))
            )
        )
        s.commit()
    return {"ok": True}
