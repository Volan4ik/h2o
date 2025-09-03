import hmac
import hashlib
import urllib.parse
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlmodel import select, delete

from src.shared.config import settings
from src.shared.db import session
from src.shared.models import User, WaterLog
from src.domain.hydration.service import HydrationService as HS

router = APIRouter(prefix="/api/webapp", tags=["webapp"])

# --- Telegram initData validation ---

def _secret_key_for_webapp(bot_token: str) -> bytes:
    """
    WebApp secret key: HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
    (НЕ путать с Login Widget, где просто SHA256(BOT_TOKEN))
    """
    return hmac.new(key=b"WebAppData", msg=bot_token.encode(), digestmod=hashlib.sha256).digest()

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

    secret_key = _secret_key_for_webapp(settings.BOT_TOKEN)
    calc_hash = hmac.new(secret_key, dcs.encode(), hashlib.sha256).hexdigest()

    if calc_hash != received_hash:
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

async def tg_user_dep(
    x_tg_init_data: str | None = Header(default=None, alias="X-Tg-Init-Data"),
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    init_data: str | None = None,  # на случай передачи через query во время отладки
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
    # Для локальной отладки разрешаем также query-параметр
    raw = raw or init_data
    if not raw:
        if getattr(settings, "DEV_ALLOW_NO_INITDATA", False):
            # Dev bypass: синтетический пользователь
            return {"raw": {}, "user": {"id": getattr(settings, "DEV_USER_ID", 0)}}
        raise HTTPException(401, "init_data required")
    return validate_init_data(raw, getattr(settings, "INITDATA_TTL", 3600))

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
