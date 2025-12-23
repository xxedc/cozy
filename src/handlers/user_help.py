from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.utils.translations import get_text
from src.keyboards.builders import help_kb, guides_kb

router = Router()

@router.message(F.text.in_([get_text("ru", "help_btn"), get_text("en", "help_btn")]))
async def help_menu(message: Message, t, lang):
    await message.answer(
        t("help_text"),
        reply_markup=help_kb(lang),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "help_main")
async def back_to_help(callback: CallbackQuery, t, lang):
    await callback.message.edit_text(
        t("help_text"),
        reply_markup=help_kb(lang),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "help_faq")
async def show_faq(callback: CallbackQuery, t, lang):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back"), callback_data="help_main")
    
    await callback.message.edit_text(
        t("faq_text"),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("help_guides"))
async def show_guides(callback: CallbackQuery, t, lang):
    # Если в data есть метка from_profile, то кнопка назад должна вести в профиль
    back_cb = "back_to_profile" if "from_profile" in callback.data else "help_main"
    
    await callback.message.edit_text(
        t("instructions_text"),
        reply_markup=guides_kb(lang, back_callback=back_cb),
        parse_mode="HTML"
    )