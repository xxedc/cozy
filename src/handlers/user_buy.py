from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta
from loguru import logger

from src.keyboards.builders import location_kb, buy_type_kb, duration_kb, instruction_links_kb, payment_method_kb
from src.keyboards.reply import get_main_kb
from src.utils.translations import get_text
from src.services.marzban_api import api
from src.database.requests import add_subscription, get_user, set_trial_used, async_session
from sqlalchemy import select

router = Router()

@router.message(F.text.in_([get_text("ru", "buy_btn"), get_text("en", "buy_btn")]))
async def start_buy(message: Message, t, lang):
    # Шаг 1: Предлагаем выбрать тип (Мульти или Соло)
    user = await get_user(message.from_user.id)
    balance = user.balance if user else 0
    await message.answer(t("buy_menu_text", balance=balance), reply_markup=buy_type_kb(lang), parse_mode="HTML")

@router.message(F.text.in_([get_text("ru", "trial_btn"), get_text("en", "trial_btn")]))
async def get_trial(message: Message, t, lang):
    user_id = message.from_user.id
    
    # 1. Проверяем, брал ли уже
    user = await get_user(user_id)
    if user and user.is_trial_used:
        await message.answer(t("trial_used"), parse_mode="HTML")
        return

    # Вместо генерации сразу показываем выбор локации с префиксом 'trial'
    await message.answer(t("choose_location"), reply_markup=location_kb(lang, prefix="trial"))

@router.callback_query(F.data.startswith("trial_"))
async def process_trial_selection(callback: CallbackQuery, t, lang):
    user_id = callback.from_user.id
    location_code = callback.data.split("_")[1]
    
    # Повторная проверка (на случай если кликнул дважды)
    user = await get_user(user_id)
    if user and user.is_trial_used:
        await callback.message.edit_text(t("trial_used"), parse_mode="HTML")
        return

    await callback.message.edit_text(t("gen_key"))

    try:
        # Генерируем ключ для ТЕСТА (Лимит 1 устройство)
        # Временно убираем limit=1 из вызова API, так как метод его не поддерживает
        username = f"trial_{user_id}"
        key = await api.create_key(username=username)
        expire_date = datetime.now() + timedelta(days=1) # 24 часа
        
        # Сохраняем подписку
        await add_subscription(
            tg_id=user_id,
            key_data=key,
            server_code=location_code,
            expires_at=expire_date,
            device_limit=1,
            marzban_username=username
        )
        
        # Отмечаем, что триал использован
        await set_trial_used(user_id)
        
        # Форматируем время для ответа
        date_str = expire_date.strftime('%d.%m.%Y %H:%M')
        # Для триала всегда < 1 дня, поэтому показываем часы и минуты
        if lang == "ru":
            remaining = "23ч 59м" # Примерно
        else:
            remaining = "23h 59m"
            
        location_name = t("swe") if location_code == "swe" else t("ger")
        
        logger.success(f"🎁 Выдан Trial юзеру {user_id} ({location_code})")
        
        # Удаляем сообщение с кнопками и отправляем новое с обновленной клавиатурой (без кнопки теста)
        await callback.message.delete()
        await callback.message.answer(
            t("trial_success", location=location_name, date=date_str, remaining=remaining) + f"\n<code>{key}</code>",
            parse_mode="HTML",
            reply_markup=instruction_links_kb().as_markup()
        )

        # Обновляем главное меню (убираем кнопку теста)
        await callback.message.answer(
            t("choose_action"),
            reply_markup=get_main_kb(lang, is_trial_used=True)
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка выдачи Trial {user_id}: {e}")
        await callback.message.edit_text(t("error"), parse_mode="HTML")

@router.callback_query(F.data == "type_single")
async def select_single_location(callback: CallbackQuery, t, lang):
    # Шаг 2 (ветка Соло): Показываем список стран
    await callback.message.edit_text(t("choose_location"), reply_markup=location_kb(lang))

@router.callback_query(F.data == "back_to_types")
async def back_to_main_buy_menu(callback: CallbackQuery, t, lang):
    # Возврат назад к выбору типа
    user = await get_user(callback.from_user.id)
    balance = user.balance if user else 0
    await callback.message.edit_text(t("buy_menu_text", balance=balance), reply_markup=buy_type_kb(lang), parse_mode="HTML")
    
@router.callback_query(F.data.startswith("buy_"))
async def select_duration(callback: CallbackQuery, t, lang):
    # Получаем код локации (swe, ger, multi)
    location_code = callback.data.split("_")[1]
    
    # Показываем меню выбора срока
    await callback.message.edit_text(
        t("choose_duration"), 
        reply_markup=duration_kb(lang, location_code),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("prepay_"))
async def show_payment_methods(callback: CallbackQuery, t, lang):
    # Формат data: prepay_{location}_{days}_{price}
    _, location_code, days_str, price_str = callback.data.split("_")
    days = int(days_str)
    price = int(price_str)
    
    user_id = callback.from_user.id
    user = await get_user(user_id)
    balance = user.balance if user else 0
    
    # Красивое название тарифа
    if location_code == "multi":
        plan_name = "Universal (Multi)"
    else:
        plan_name = f"Single ({location_code.upper()})"
        
    plan_name += f" - {days} " + (t("days_short") if lang == "ru" else "days")

    await callback.message.edit_text(
        t("choose_payment", plan_name=plan_name, price=price, balance=balance),
        reply_markup=payment_method_kb(lang, balance, price, location_code, days),
        parse_mode="HTML"
    )

async def issue_key(user_id: int, username: str, location_code: str, days: int, t, lang, message: Message):
    """Вспомогательная функция для выдачи ключа после успешной оплаты"""
    
    # Логируем действие!
    logger.info(f"💰 Юзер {user_id} получает ключ: {location_code} на {days} дней")

    if location_code == "multi":
        location_name = "Universal (Multi-Access)"
        device_limit = 5 # Премиум лимит
    elif location_code == "swe":
        location_name = t("swe")
        device_limit = 3 # Стандартный лимит
    else:
        location_name = t("ger")
        device_limit = 3 # Стандартный лимит
    
    await message.edit_text(t("gen_key"))
    
    try:
        # Генерируем ключ с учетом лимита устройств
        # Временно убираем limit из вызова API
        username = f"user_{user_id}"
        key = await api.create_key(username=username)
        expire_date = datetime.now() + timedelta(days=days)
        
        await add_subscription(
            tg_id=user_id,
            key_data=key,
            server_code=location_code,
            expires_at=expire_date,
            device_limit=device_limit,
            marzban_username=username
        )
        
        # Логируем успех!
        logger.success(f"✅ Ключ выдан юзеру {user_id}")
        
        # Форматируем время
        date_str = expire_date.strftime('%d.%m.%Y %H:%M')
        days_left = (expire_date - datetime.now()).days
        if lang == "ru":
            remaining = f"{days_left}д"
        else:
            remaining = f"{days_left}d"

        await message.answer(
            t("key_ready", location=location_name, key=key, date=date_str, remaining=remaining),
            parse_mode="HTML",
            reply_markup=instruction_links_kb().as_markup()
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при выдаче ключа юзеру {user_id}: {e}")
        await message.edit_text(t("error"), parse_mode="HTML")

@router.callback_query(F.data.startswith("confirm_balance_"))
async def process_balance_pay(callback: CallbackQuery, t, lang):
    # confirm_balance_{location}_{days}_{price}
    _, _, location_code, days_str, price_str = callback.data.split("_")
    days = int(days_str)
    price = int(price_str)
    user_id = callback.from_user.id

    # Транзакция списания
    async with async_session() as session:
        from src.database.models import User
        user = await session.scalar(select(User).where(User.id == user_id))
        
        if user.balance < price:
            await callback.answer(t("insufficient_funds"), show_alert=True)
            return
        
        user.balance -= price
        await session.commit()
        logger.info(f"💸 Списано {price}р с баланса юзера {user_id}")

    # Выдаем ключ
    await issue_key(user_id, callback.from_user.username, location_code, days, t, lang, callback.message)

@router.callback_query(F.data.startswith("confirm_online_"))
async def process_online_pay(callback: CallbackQuery, t, lang):
    # confirm_online_{location}_{days}_{price}
    # Здесь должна быть интеграция с ЮКассой / CryptoBot
    # Пока делаем MOCK (сразу успех)
    
    _, _, location_code, days_str, price_str = callback.data.split("_")
    days = int(days_str)
    price = int(price_str)
    
    # В реальном проекте здесь мы отправляем Invoice
    # await bot.send_invoice(...)
    # А выдачу ключа делаем в pre_checkout_query / successful_payment
    
    # Для теста сразу выдаем:
    await issue_key(callback.from_user.id, callback.from_user.username, location_code, days, t, lang, callback.message)