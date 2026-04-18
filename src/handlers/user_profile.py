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
        now = datetime.now()
        active = [s for s in subs if s.expires_at > now]
        time_subs = sorted([s for s in active if getattr(s, 'plan_type', 'time') != 'traffic'], key=lambda s: s.expires_at, reverse=True)
        traffic_subs = sorted([s for s in active if getattr(s, 'plan_type', 'time') == 'traffic'], key=lambda s: s.expires_at, reverse=True)

        best_time = time_subs[0] if time_subs else None
        best_traffic = traffic_subs[0] if traffic_subs else None
        best = best_time or best_traffic

        if not best:
            text += t("no_subs")
        else:
            # 节点名
            server_name = best.server.name if best.server else "unknown"
            if "multi" in server_name.lower():
                node_name = "🌍 全球通（所有节点）"
            elif "swe" in server_name.lower():
                node_name = "🇯🇵 日本"
            elif "ger" in server_name.lower():
                node_name = "🇯🇵 日本（备用）"
            else:
                node_name = server_name

            status = await api.get_user_status(best.marzban_username)
            online_count = status.get('online', 0)
            limit_str = str(best.device_limit) if best.device_limit else "∞"

            # 从数据库取固定订阅链接
            sub_url = ""
            for s in (time_subs + traffic_subs):
                if hasattr(s, "subscription_url") and s.subscription_url:
                    sub_url = s.subscription_url
                    break

            text += "━━━━━━━━━━━━━━━━━━\n"
            text += "📡 <b>节点：</b>" + node_name + "\n"
            text += "📱 <b>在线设备：</b>" + str(online_count) + " / " + limit_str + "\n"
            text += "\n"

            # 时间套餐信息
            if best_time:
                days_left = (best_time.expires_at - now).days
                if days_left >= 3640:
                    text += "🗓 <b>时间套餐：</b>永久有效\n"
                else:
                    text += "🗓 <b>时间套餐到期：</b>" + best_time.expires_at.strftime("%Y-%m-%d %H:%M:%S") + "\n"
                    text += "⏱ <b>剩余天数：</b>" + str(days_left) + " 天\n"
                text += "📶 <b>月度流量：</b>200 GB（每30天重置）\n"
            else:
                text += "🗓 <b>时间套餐：</b>未购买\n"

            text += "\n"

            # 流量包信息
            if best_traffic:
                tgb = getattr(best_traffic, 'traffic_gb', 0) or 0
                text += "📦 <b>流量包：</b>" + str(tgb) + " GB（永久有效）\n"
            else:
                text += "📦 <b>流量包：</b>未购买\n"

            text += "\n"

            # 订阅链接
            if sub_url:
                text += "━━━━━━━━━━━━━━━━━━\n"
                text += "📋 <b>订阅链接（支持全协议）：</b>\n"
                text += "<code>" + sub_url + "</code>\n"
            text += "\n"
    
    has_active = any(s.expires_at > now and getattr(s,'plan_type','time') != 'traffic' for s in subs)
    return text, profile_kb(lang, has_active_sub=has_active)

@router.message(F.text.in_(["📦 我的订阅", get_text("ru", "profile_btn")]))
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

    # 记录充值账单
    try:
        from src.database.requests import add_billing_record
        await add_billing_record(user_id, amount, "topup", "余额充值 +" + str(amount) + "¥")
    except Exception:
        pass

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
@router.callback_query(F.data.startswith("renew_"))
async def renew_subscription(callback: CallbackQuery, t, lang):
    from src.keyboards.builders import duration_kb, buy_type_kb
    from src.database.requests import get_user, get_user_subscriptions
    from datetime import datetime

    plan = callback.data.split("_")[1]
    days_map = {"1m": 30, "3m": 90, "1y": 365}
    price_map = {"1m": 15, "3m": 40, "1y": 140}

    days = days_map.get(plan, 30)
    price = price_map.get(plan, 15)
    label_map = {"1m": "1个月", "3m": "3个月", "1y": "12个月"}
    label = label_map.get(plan, "1个月")

    user_id = callback.from_user.id
    user = await get_user(user_id)
    balance = user.balance if user else 0

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()

    if balance >= price:
        builder.button(
            text="💰 余额支付（" + str(price) + "¥）",
            callback_data="confirm_balance_multi_" + str(days) + "_" + str(price)
        )
    else:
        diff = price - balance
        builder.button(
            text="💰 余额不足（还差" + str(diff) + "¥）",
            callback_data="top_up_menu"
        )
    builder.button(
        text="💳 在线支付（" + str(price) + "¥）",
        callback_data="confirm_online_multi_" + str(days) + "_" + str(price)
    )
    builder.button(text="🔙 返回", callback_data="back_to_profile")
    builder.adjust(1)

    await callback.message.edit_text(
        "🔄 <b>续期确认</b>\n\n"
        "套餐：<b>" + label + "</b>\n"
        "价格：<b>" + str(price) + "¥</b>\n"
        "当前余额：<b>" + str(balance) + "¥</b>\n\n"
        "续期后时间将在现有到期时间基础上延长。",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()
