from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

def kb_today(dose: int = 250) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"+{dose} мл", callback_data=f"add:{dose}")
    kb.button(text="+250", callback_data="add:250")
    kb.button(text="+500", callback_data="add:500")
    kb.button(text="Пауза 1ч", callback_data="mute:60")
    kb.adjust(3, 1)
    return kb.as_markup()

def kb_remind_settings(is_on: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if is_on:
        kb.button(text="Выключить умные напоминания", callback_data="remind:off")
    else:
        kb.button(text="Включить умные напоминания", callback_data="remind:on")
    kb.adjust(1)
    return kb.as_markup()