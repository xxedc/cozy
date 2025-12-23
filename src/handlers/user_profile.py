from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from src.utils.translations import get_text
from src.database.requests import get_user_subscriptions, get_user, async_session
from src.keyboards.builders import profile_kb, top_up_kb, payment_method_kb
from src.services.marzban_api import api
from sqlalchemy import select

router = Router()

async def get_profile_text(user_id: int, t, lang: str):
    user = await get_user(user_id)
    subs = await get_user_subscriptions(user_id)
    
    balance = user.balance if user else 0
    text = t("profile_header", id=user_id, balance=balance) + "\n\n"
    
    if not subs:
        text += t("no_subs")
    else:
        text += t("your_subs")
        now = datetime.now()
        for sub in subs:
            # Пытаемся перевести название страны, если оно сохранено кодом (например "swe")
            # Если нет, выводим как есть
            server_name = sub.server.name if sub.server else "unknown"
            if "swe" in server_name.lower():
                country_name = t("swe")
            elif "ger" in server_name.lower():
                country_name = t("ger")
            elif "multi" in server_name.lower():
                country_name = t("btn_multi")
            else:
                country_name = server_name
            
            # Расчет оставшегося времени
            delta = sub.expires_at - now
            if delta.total_seconds() <= 0:
                remaining = "0m"
            else:
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                
                if lang == "ru":
                    remaining = f"{days}д {hours}ч" if days > 0 else f"{hours}ч {minutes}м"
                else:
                    remaining = f"{days}d {hours}h" if days > 0 else f"{hours}h {minutes}m"
            
            # Получаем статус устройств
            status = await api.get_user_status(sub.marzban_username)
            online_count = status.get('online', 0)
            limit_count = sub.device_limit
            limit_str = str(limit_count) if limit_count > 0 else "∞"

            text += t("sub_item", country=country_name, key=sub.vless_key, date=sub.expires_at.strftime('%d.%m.%Y %H:%M'), remaining=remaining, online=online_count, limit=limit_str)
    
    return text, profile_kb(lang)

@router.message(F.text.in_([get_text("ru", "profile_btn"), get_text("en", "profile_btn")]))
async def profile(message: Message, t, lang):
    text, kb = await get_profile_text(message.from_user.id, t, lang)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, t, lang):
    text, kb = await get_profile_text(callback.from_user.id, t, lang)
    # Если подписок нет, kb будет None, но edit_text требует валидную разметку или None
    # Если kb=None, просто убираем кнопки
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("top_up_"))
async def top_up_menu(callback: CallbackQuery, t, lang):
    back_cb = "back_to_profile"
    context_suffix = ""
    
    # Если пришли из меню покупки (top_up_buy_LOC_DAYS_PRICE)
    if callback.data.startswith("top_up_buy_"):
        try:
            parts = callback.data.split("_")
            # parts: ['top', 'up', 'buy', 'loc', 'days', 'price']
            location, days, price = parts[3], parts[4], parts[5]
            back_cb = f"prepay_{location}_{days}_{price}"
            # Формируем суффикс для кнопок пополнения: _buy_loc_days_price
            context_suffix = f"_buy_{location}_{days}_{price}"
        except IndexError:
            pass

    await callback.message.edit_text(
        t("top_up_choose"),
        reply_markup=top_up_kb(lang, back_callback=back_cb, context_suffix=context_suffix),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("add_funds_"))
async def add_funds_mock(callback: CallbackQuery, t, lang):
    amount = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # MOCK: В реальности здесь отправка Invoice на оплату
    # Сейчас просто начисляем баланс
    
    async with async_session() as session:
        from src.database.models import User
        user = await session.scalar(select(User).where(User.id == user_id))
        user.balance += amount
        await session.commit()
        new_balance = user.balance

    # Проверяем, есть ли контекст покупки в callback_data
    # Формат: add_funds_AMOUNT_buy_LOC_DAYS_PRICE
    if "_buy_" in callback.data:
        try:
            # parts: ['add', 'funds', 'AMOUNT', 'buy', 'LOC', 'DAYS', 'PRICE']
            parts = callback.data.split("_")
            location = parts[4]
            days = int(parts[5])
            price = int(parts[6])
            
            # Показываем всплывающее уведомление об успехе
            await callback.answer(t("top_up_success_alert", balance=new_balance), show_alert=True)
            
            # Формируем название тарифа для отображения
            if location == "multi":
                plan_name = "Universal (Multi)"
            else:
                plan_name = f"Single ({location.upper()})"
            plan_name += f" - {days} " + (t("days_short") if lang == "ru" else "days")
            
            # Возвращаем пользователя к экрану выбора оплаты (где кнопка "С баланса" теперь активна)
            await callback.message.edit_text(
                t("choose_payment", plan_name=plan_name, price=price, balance=new_balance),
                reply_markup=payment_method_kb(lang, new_balance, price, location, days),
                parse_mode="HTML"
            )
            return
        except (IndexError, ValueError):
            pass # Если ошибка парсинга, идем по стандартному пути

    await callback.message.answer(
        t("top_up_success", balance=new_balance),
        parse_mode="HTML"
    )
    # Возвращаем в профиль
    text, kb = await get_profile_text(user_id, t, lang)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)