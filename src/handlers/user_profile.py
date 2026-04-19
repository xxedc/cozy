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

            text += (
                "━━━━━━━━━━━━\n"
                "🚀 " + node_name + "\n"
                "📊 状态：🟢 正常\n"
                "📱 设备：" + str(online_count) + " / " + limit_str + "\n\n"
            )

            if best_time:
                days_left = (best_time.expires_at - now).days
                if days_left >= 3640:
                    text += "⏳ 到期：永久有效\n⏱ 剩余：永久\n"
                else:
                    text += "⏳ 到期：" + best_time.expires_at.strftime("%Y-%m-%d") + "\n"
                    text += "⏱ 剩余：" + str(days_left) + " 天\n"
            else:
                text += "⏳ 到期：无时间套餐\n"

            text += "\n━━━━━━━━━━━━\n"
            if best_time:
                text += "📡 流量：200 GB / 月\n"
            text += "📉 已用：0.0 GB\n"

            if best_traffic:
                tgb = getattr(best_traffic, 'traffic_gb', 0) or 0
                text += "🎁 流量包：" + str(tgb) + " GB\n"
            else:
                text += "🎁 流量包：无\n"

            if sub_url:
                text += "\n━━━━━━━━━━━━\n"
                text += "🔗 订阅：\n"
                text += "<code>" + sub_url + "</code>\n"

            text += "\n━━━━━━━━━━━━\n"

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
