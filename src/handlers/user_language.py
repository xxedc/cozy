from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from src.keyboards.builders import language_kb
from src.database.requests import update_user_language
from src.utils.translations import get_text
from src.keyboards.reply import get_main_kb

router = Router()

@router.message(Command("language"))
async def cmd_language(message: Message, t):
    await message.answer(t("choose_lang"), reply_markup=language_kb())

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Обновляем язык в БД
    await update_user_language(user_id, lang_code)
    
    # Получаем текст ответа на НОВОМ языке
    text = get_text(lang_code, "lang_changed")
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=get_main_kb(lang_code))
    await callback.answer()