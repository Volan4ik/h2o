import hmac, hashlib, urllib.parse, json
from fastapi import APIRouter, HTTPException, Header, Depends
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from sqlmodel import select, delete
from pydantic import BaseModel

from src.shared.config import settings
from src.shared.db import session
from src.shared.models import User, WaterLog
from src.domain.hydration.service import HydrationService as HS

router = APIRouter(prefix="/api/webapp", tags=["webapp"])

# --- Telegram initData validation ---

def _secret_key(token: str) -> bytes:
    return hmac.new(key=b"WebAppData", msg=token.encode(), digestmod=hashlib.sha256).digest()

def _parse_init_data(init_data: str) -> dict:
    return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))

def _data_check_string(parsed: dict) -> str:
    kv = []
    for k in sorted(k for k in parsed.keys() if k not in ("hash", "signature")):
        kv.append(f"{k}={parsed[k]}")
    return "\n".join(kv)

def validate_init_data(init_data: str, lifetime: int = 3600) -> dict:
    parsed = _parse_init_data(init_data)
    if "hash" not in parsed:
        raise HTTPException(401, "init_data missing hash")
    if "auth_date" in parsed:
        try:
            auth_ts = int(parsed["auth_date"])
            if datetime.now(timezone.utc) - datetime.fromtimestamp(auth_ts, tz=timezone.utc) > timedelta(seconds=lifetime):
                raise HTTPException(401, "init_data expired")
        except Exception:
            raise HTTPException(401, "bad auth_date")
    dcs = _data_check_string(parsed)
    sk = _secret_key(settings.BOT_TOKEN)
    calc = hmac.new(sk, dcs.encode(), hashlib.sha256).hexdigest()
    if calc != parsed["hash"]:
        raise HTTPException(401, "bad init_data signature")
    user = json.loads(parsed.get("user", "{}")) if "user" in parsed else {}
    # Support signed "unsafe" header from tg-mini-apps dev tools if provided
    if not user and "user_id" in parsed:
        try:
            user = {"id": int(parsed["user_id"])}
        except Exception:
            pass
    return {"raw": parsed, "user": user}

async def tg_user_dep(x_tg_init_data: str = Header(None), init_data: str | None = None):
    raw = x_tg_init_data or init_data
    if not raw:
        if settings.DEV_ALLOW_NO_INITDATA:
            # Dev bypass: synthesize a user
            return {"raw": {}, "user": {"id": settings.DEV_USER_ID}}
        raise HTTPException(401, "init_data required")
    return validate_init_data(raw, settings.INITDATA_TTL)

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
            s.add(u); s.commit(); s.refresh(u)
        start, end = HS.local_bounds(u)
        logs = s.exec(select(WaterLog).where((WaterLog.user_id==u.id) & (WaterLog.ts_utc>=HS.to_utc(start)) & (WaterLog.ts_utc<HS.to_utc(end)))).all()
        consumed = sum(l.amount_ml for l in logs)
    return {"goal_ml": u.goal_ml, "consumed_ml": consumed, "default_glass_ml": u.default_glass_ml}

@router.post("/log")
async def log(payload: LogRequest, data=Depends(tg_user_dep)):
    uid = data["user"].get("id")
    if payload.amount_ml == 0:
        raise HTTPException(400, "amount_ml != 0 required")
    with session() as s:
        u = s.exec(select(User).where(User.tg_id == uid)).first()
        if not u:
            raise HTTPException(404, "user not found")
        s.add(WaterLog(user_id=u.id, ts_utc=datetime.utcnow().replace(tzinfo=timezone.utc), amount_ml=payload.amount_ml, source="webapp"))
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
        start_local = (end_local - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        logs = s.exec(select(WaterLog).where((WaterLog.user_id==u.id) & (WaterLog.ts_utc>=HS.to_utc(start_local)) & (WaterLog.ts_utc<=HS.to_utc(end_local)))).all()
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
        # удалить все записи за сегодня
        start, end = HS.local_bounds(u)
        s.exec(
            delete(WaterLog).where(
                (WaterLog.user_id == u.id) &
                (WaterLog.ts_utc >= HS.to_utc(start)) &
                (WaterLog.ts_utc < HS.to_utc(end))
            )
        )
        s.commit()
    return {"ok": True}
