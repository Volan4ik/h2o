from __future__ import annotations
from datetime import datetime, time as dtime, timedelta
import re
import pytz
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlmodel import select
from .db import get_session
from .models import User, WaterLog
from .keyboards import kb_today, kb_remind_settings
from .reminders import schedule_next, user_now

router = Router()

class Onboarding(StatesGroup):
    Goal = State()
    Window = State()
    Glass = State()

# --- utils ---
OZ_TO_ML = 29.5735

def parse_amount(text: str, units: str = "ml") -> int | None:
    t = text.strip().lower().replace(",", ".")
    m = re.match(r"^(\d+(?:\.\d+)?)(ml|l|oz)?$", t)
    if not m:
        return None
    val = float(m.group(1))
    suf = m.group(2) or ("oz" if units == "oz" else "ml")
    if suf == "ml":
        return int(round(val))
    if suf == "l":
        return int(round(val * 1000))
    if suf == "oz":
        return int(round(val * OZ_TO_ML))
    return None

# --- helpers ---

def get_or_create_user(tg_id: int) -> User:
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == tg_id)).first()
        if u:
            return u
        u = User(tg_id=tg_id)
        s.add(u)
        s.commit(); s.refresh(u)
        return u

# --- commands ---
@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    u = get_or_create_user(msg.from_user.id)
    await msg.answer(
        "Привет! Я помогу пить воду без спама. Начнём с короткой настройки.\n\n" \
        "1) Введите дневную цель (например, 2000 мл или 2l)."
    )
    await state.set_state(Onboarding.Goal)

@router.message(Onboarding.Goal)
async def set_goal(msg: Message, state: FSMContext):
    amount = parse_amount(msg.text, units="ml")
    if not amount or amount < 800 or amount > 5000:
        await msg.answer("Введите число от 800 мл до 5000 мл (например, 1800, 2l, 64oz).")
        return
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        u.goal_ml = amount
        s.add(u); s.commit()
    await msg.answer("2) Укажите окно бодрствования в формате HH:MM-HH:MM (например, 08:00-23:00).")
    await state.set_state(Onboarding.Window)

@router.message(Onboarding.Window)
async def set_window(msg: Message, state: FSMContext):
    m = re.match(r"^(\d{1,2}):(\d{2})\-(\d{1,2}):(\d{2})$", msg.text.strip())
    if not m:
        await msg.answer("Формат такой: 08:00-23:00")
        return
    w_h, w_m, s_h, s_m = map(int, m.groups())
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        u.wake_at = dtime(hour=w_h, minute=w_m)
        u.sleep_at = dtime(hour=s_h, minute=s_m)
        s.add(u); s.commit()
    await msg.answer("3) Размер быстрого стакана? (например, 200 или 250 мл)")
    await state.set_state(Onboarding.Glass)

@router.message(Onboarding.Glass)
async def set_glass(msg: Message, state: FSMContext):
    amount = parse_amount(msg.text, units="ml")
    if not amount or amount < 50 or amount > 1000:
        await msg.answer("Введите число от 50 до 1000 мл")
        return
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        u.default_glass_ml = amount
        s.add(u); s.commit()
    await state.clear()
    await msg.answer("Готово! Используйте /today чтобы посмотреть прогресс или просто пришлите число (например, 300). \nУмные напоминания включены. Можно настроить в /remind.")

@router.message(Command("today"))
async def cmd_today(msg: Message):
    with get_session() as s:
        u = get_or_create_user(msg.from_user.id)
        now = user_now(u)
        # Соберём статистику за день
        from .reminders import local_day_bounds, to_utc
        start_local, end_local = local_day_bounds(u)
        rows = s.exec(select(WaterLog).where((WaterLog.user_id==u.id) & (WaterLog.ts>=to_utc(start_local)) & (WaterLog.ts<to_utc(end_local)))).all()
        consumed = sum(r.amount_ml for r in rows)
        pct = int(consumed * 100 / max(1, u.goal_ml))
    dose = max(150, min(350, int(0.12 * u.goal_ml)))
    await msg.answer(f"💧Цель: {u.goal_ml} мл · Выпито: {consumed} мл ({pct}%)\n",
                     reply_markup=kb_today(dose))

@router.message(Command("add"))
async def cmd_add(msg: Message):
    u = get_or_create_user(msg.from_user.id)
    # текст после команды
    payload = msg.text.split(maxsplit=1)
    if len(payload) == 1:
        await msg.answer("Пришлите объём: например, 300, 0.5l или 8oz.")
        return
    amount = parse_amount(payload[1], u.units)
    if not amount:
        await msg.answer("Не понял объём. Пример: 300, 0.5l, 8oz")
        return
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        log = WaterLog(user_id=u.id, ts=datetime.utcnow().replace(tzinfo=pytz.UTC), amount_ml=amount, source="manual")
        s.add(log); s.commit()
    from .reminders import schedule_next
    schedule_next(u)
    await msg.answer(f"Зачёл {amount} мл 💧")

@router.message(Command("remind"))
async def cmd_remind(msg: Message):
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first() or get_or_create_user(msg.from_user.id)
    text = "Умные напоминания сейчас включены." if u.smart_on else "Умные напоминания сейчас выключены."
    await msg.answer(text, reply_markup=kb_remind_settings(u.smart_on))

@router.message(Command("mute"))
async def cmd_mute(msg: Message):
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first() or get_or_create_user(msg.from_user.id)
        u.mute_until = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(hours=1)
        s.add(u); s.commit()
    await msg.answer("Ок, помолчу 1 час.")

@router.message(Command("unmute"))
async def cmd_unmute(msg: Message):
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first() or get_or_create_user(msg.from_user.id)
        u.mute_until = None
        s.add(u); s.commit()
    await msg.answer("Напоминания разблокированы.")

@router.message(F.text.regexp(r"^\d+(?:[\.,]\d+)?(?:ml|l|oz)?$"))
async def any_amount(msg: Message):
    u = get_or_create_user(msg.from_user.id)
    amount = parse_amount(msg.text, u.units)
    if not amount:
        return
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == msg.from_user.id)).first()
        log = WaterLog(user_id=u.id, ts=datetime.utcnow().replace(tzinfo=pytz.UTC), amount_ml=amount, source="manual")
        s.add(log); s.commit()
    schedule_next(u)
    await msg.answer(f"Зачёл {amount} мл 💧", reply_markup=kb_today(max(150, min(350, int(0.12 * u.goal_ml)))))

# --- callbacks ---
@router.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery):
    u = get_or_create_user(call.from_user.id)
    amount = int(call.data.split(":")[1])
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == call.from_user.id)).first()
        log = WaterLog(user_id=u.id, ts=datetime.utcnow().replace(tzinfo=pytz.UTC), amount_ml=amount, source="quick")
        s.add(log); s.commit()
    schedule_next(u)
    await call.message.edit_text(f"Добавил {amount} мл. Держим темп!", reply_markup=kb_today(max(150, min(350, int(0.12 * u.goal_ml)))))
    await call.answer()

@router.callback_query(F.data.startswith("mute:"))
async def cb_mute(call: CallbackQuery):
    minutes = int(call.data.split(":")[1])
    until = datetime.utcnow().replace(tzinfo=pytz.UTC) + timedelta(minutes=minutes)
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == call.from_user.id)).first()
        u.mute_until = until
        s.add(u); s.commit()
    await call.message.edit_text("Ок, сделаю паузу.")
    await call.answer("Бот на паузе")

@router.callback_query(F.data.startswith("remind:"))
async def cb_remind(call: CallbackQuery):
    action = call.data.split(":")[1]
    with get_session() as s:
        u = s.exec(select(User).where(User.tg_id == call.from_user.id)).first()
        u.smart_on = (action == "on")
        s.add(u); s.commit()
    if u.smart_on:
        schedule_next(u)
        await call.message.edit_text("Умные напоминания включены.")
    else:
        await call.message.edit_text("Умные напоминания выключены.")
    await call.answer()