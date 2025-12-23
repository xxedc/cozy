from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from src.utils.translations import get_text

def get_main_kb(lang: str = "ru", is_trial_used: bool = False):
    keyboard = [
        [KeyboardButton(text=get_text(lang, "buy_btn"))]
    ]
    
    if not is_trial_used:
        keyboard.append([KeyboardButton(text=get_text(lang, "trial_btn"))])
        
    keyboard.append([KeyboardButton(text=get_text(lang, "profile_btn"))])
    keyboard.append([
        KeyboardButton(text=get_text(lang, "status_btn")),
        KeyboardButton(text=get_text(lang, "help_btn"))
    ])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder=get_text(lang, "choose_action")
    )