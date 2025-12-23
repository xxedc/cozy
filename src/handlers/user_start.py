from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from src.keyboards.reply import get_main_kb
from src.database.requests import add_user, get_user, get_user_subscriptions

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, t, lang):
    await add_user(message.from_user.id, message.from_user.username, lang)
    
    user = await get_user(message.from_user.id)
    
    subs = await get_user_subscriptions(message.from_user.id)
    has_active_sub = any(sub.status == 'active' and sub.expires_at > datetime.now() for sub in subs)
    
    is_trial_used = (user.is_trial_used if user else False) or has_active_sub
    
    await message.answer(
        t("start_msg"),
        reply_markup=get_main_kb(lang, is_trial_used),
        parse_mode="HTML"
    )