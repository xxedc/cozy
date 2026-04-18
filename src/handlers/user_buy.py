from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime, timedelta
from loguru import logger

from src.keyboards.builders import location_kb, buy_type_kb, duration_kb, instruction_links_kb, payment_method_kb
from src.keyboards.reply import get_main_kb
from src.utils.translations import get_text
from src.services.marzban_api import api
from src.database.requests import add_subscription, get_user, set_trial_used, async_session, get_user_subscriptions
from sqlalchemy import select

router = Router()

@router.message(F.text.in_(["🚀 开通订阅"]))
async def start_buy(message: Message, t, lang):
    # Шаг 1: Предлагаем выбрать тип (Мульти или Соло)
    user = await get_user(message.from_user.id)
    balance = user.balance if user else 0
    await message.answer(t("buy_menu_text", balance=balance), reply_markup=buy_type_kb(lang), parse_mode="HTML")

@router.message(F.text.in_(["🎁 免费试用"]))
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
        expire_date = datetime.now() + timedelta(days=7)  # 7天试用
        expire_ts = int(expire_date.timestamp())

        # 同步到 Marzban：7天有效期，30GB流量不重置
        key, sub_url = await api.create_key(
            username=username,
            expire_timestamp=expire_ts,
            data_limit_gb=30
        )

        await add_subscription(
            tg_id=user_id,
            key_data=key,
            server_code=location_code,
            expires_at=expire_date,
            device_limit=1,
            marzban_username=username,
            subscription_url=sub_url,
            plan_type="time",
            traffic_gb=30
        )
        
        # Отмечаем, что триал использован
        await set_trial_used(user_id)
        
        # Форматируем время для ответа
        date_str = expire_date.strftime('%Y-%m-%d %H:%M')
        # Для триала всегда < 1 дня, поэтому показываем часы и минуты
        if lang == "ru":
            remaining = "6天 23小时"  # 7天试用
        else:
            remaining = "6天 23小时"  # 7天试用
            
        location_name = t("swe") if location_code == "swe" else t("ger")
        
        logger.success(f"🎁 Выдан Trial юзеру {user_id} ({location_code})")
        
        # Удаляем сообщение с кнопками и отправляем новое с обновленной клавиатурой (без кнопки теста)
        await callback.message.delete()
        days_left_trial = (expire_date - datetime.now()).days
        hours_left_trial = ((expire_date - datetime.now()).seconds) // 3600
        remaining_trial = str(days_left_trial) + "天 " + str(hours_left_trial) + "小时"

        if sub_url:
            trial_msg = (
                "<b>🎁 试用已激活！</b>\n\n"
                "📡 节点：" + location_name + "\n"
                "⏳ 有效期：7天 / 30GB\n"
                "⏳ 到期时间：" + date_str + "\n"
                "⏱ 剩余时间：" + remaining_trial + "\n\n"
                "📋 <b>订阅链接（复制到客户端导入）：</b>\n"
                "<code>" + sub_url + "</code>"
            )
        else:
            trial_msg = (
                "<b>🎁 试用已激活！</b>\n\n"
                "📡 节点：" + location_name + "\n"
                "⏳ 有效期：7天 / 30GB\n"
                "⏳ 到期时间：" + date_str + "\n"
                "<code>" + key + "</code>"
            )
        await callback.message.answer(trial_msg, parse_mode="HTML", reply_markup=instruction_links_kb().as_markup())

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

async def issue_key(user_id: int, username: str, location_code: str, days: int, t, lang, message: Message, price: int = 0):
    """Вспомогательная функция для выдачи ключа после успешной оплаты"""
    
    # Логируем действие!
    logger.info(f"💰 Юзер {user_id} получает ключ: {location_code} на {days} дней")

    if location_code == "multi":
        location_name = "🌍 全球通（所有节点）"
        device_limit = 5 # Премиум лимит
    elif location_code == "swe":
        location_name = "🇯🇵 日本"
        device_limit = 3 # Стандартный лимит
    else:
        location_name = "🇯🇵 日本（备用）"
        device_limit = 3 # Стандартный лимит
    
    await message.edit_text(t("gen_key"))
    
    try:
        # Генерируем ключ с учетом лимита устройств
        # Временно убираем limit из вызова API
        username = f"user_{user_id}"

        # 获取已有订阅，时间套餐叠加到期时间
        existing_subs = await get_user_subscriptions(user_id)
        now_dt = datetime.now()

        if days == 0:
            # 流量包：设置一个很远的日期，实际靠流量控制
            expire_date = datetime.now() + timedelta(days=3650)
            new_traffic = 500
        else:
            # 时间套餐：在已有时间套餐到期时间基础上叠加（不叠加流量包时间）
            existing_time = None
            for s in existing_subs:
                pt = getattr(s, 'plan_type', 'time')
                if pt == 'time' and s.expires_at > now_dt:
                    existing_time = s
                    break
            if existing_time:
                expire_date = existing_time.expires_at + timedelta(days=days)
            else:
                expire_date = now_dt + timedelta(days=days)
            new_traffic = 0

        # 同步到期时间和流量到 Marzban 面板
        import time as _time
        if days == 0:
            _expire_ts = 0        # 流量包不限时间
            _data_gb = 500        # 500GB每月重置
        else:
            _expire_ts = int(expire_date.timestamp())
            _data_gb = 200        # 时间套餐200GB每月重置

        key, sub_url = await api.create_key(
            username=username,
            expire_timestamp=_expire_ts,
            data_limit_gb=_data_gb
        )

        # 用 Marzban 返回的最新订阅链接（确保和面板一致）
        if sub_url:
            import aiohttp as _aio_sync
            try:
                _h_sync = await api._headers()
                async with _aio_sync.ClientSession() as _s_sync:
                    async with _s_sync.get(
                        api.host + "/api/user/" + username,
                        headers=_h_sync
                    ) as _r_sync:
                        if _r_sync.status == 200:
                            _d_sync = await _r_sync.json()
                            _latest = _d_sync.get("subscription_url", "")
                            if _latest:
                                if not _latest.startswith("http"):
                                    _latest = api.host + _latest
                                sub_url = _latest
            except Exception:
                pass

        await add_subscription(
            tg_id=user_id,
            key_data=key,
            server_code=location_code,
            expires_at=expire_date,
            device_limit=device_limit,
            marzban_username=username,
            subscription_url=sub_url,
            plan_type="traffic" if days == 0 else "time",
            traffic_gb=new_traffic
        )
        
        # 触发邀请返佣
        try:
            from src.database.requests import process_referral_reward
            reward = await process_referral_reward(user_id, price if "price" in dir() else 0)
            if reward:
                logger.info("💰 邀请返佣已发放")
        except Exception:
            pass

        # 记录消费账单
        try:
            from src.database.requests import add_billing_record
            plan_label = "流量包 500GB" if days == 0 else (str(days) + "天订阅")
            await add_billing_record(
                user_id,
                -price,
                "purchase",
                "购买" + plan_label + " - " + location_name
            )
        except Exception:
            pass

        # Логируем успех!
        logger.success(f"✅ Ключ выдан юзеру {user_id}")

        # 计算显示时间
        if days == 0:
            time_line = "⏳ 有效期：永久（无到期时间）"
        else:
            date_str = expire_date.strftime("%Y-%m-%d %H:%M")
            days_left = (expire_date - datetime.now()).days
            remaining = str(days_left) + "天"
            time_line = "⏳ 到期时间：" + date_str + "\n⏱ 剩余时间：" + remaining

        if sub_url:
            msg = (
                "✅ <b>购买成功！</b>\n\n"
                "📡 节点：" + location_name + "\n"
                + time_line + "\n\n"
                "📋 <b>订阅链接（支持全部协议，复制到客户端导入）：</b>\n"
                "<code>" + sub_url + "</code>"
            )
        else:
            msg = (
                "✅ <b>购买成功！</b>\n\n"
                "📡 节点：" + location_name + "\n"
                + time_line + "\n\n"
                "<code>" + key + "</code>"
            )
        await message.answer(msg, parse_mode="HTML", reply_markup=instruction_links_kb().as_markup())
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
    await issue_key(user_id, callback.from_user.username, location_code, days, t, lang, callback.message, price=price)

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
    await issue_key(callback.from_user.id, callback.from_user.username, location_code, days, t, lang, callback.message, price=price)