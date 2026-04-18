from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.services.stats import collect_daily_stats

scheduler = AsyncIOScheduler()

async def check_expiring_subscriptions():
    """每天检查即将到期的订阅，发送提醒"""
    from src.database.core import async_session
    from src.database.models import Subscription, User
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from datetime import datetime, timedelta
    from src.bot import bot
    from loguru import logger

    now = datetime.now()
    remind_days = [3, 1, 0]  # 提前3天、1天、当天提醒

    async with async_session() as session:
        result = await session.scalars(
            select(Subscription)
            .options(joinedload(Subscription.user))
            .where(Subscription.expires_at > now)
        )
        subs = result.all()

    for sub in subs:
        days_left = (sub.expires_at - now).days
        if days_left not in remind_days:
            continue

        user = sub.user
        if not user:
            continue

        # 跳过永久套餐
        if days_left >= 3640:
            continue

        # 根据剩余天数选择消息
        if days_left == 0:
            emoji = "🚨"
            title = "订阅今天到期！"
            urgency = "您的订阅<b>今天到期</b>，到期后将无法使用，请立即续费！"
        elif days_left == 1:
            emoji = "⚠️"
            title = "订阅明天到期"
            urgency = "您的订阅<b>明天到期</b>，请及时续费以避免中断。"
        else:
            emoji = "🔔"
            title = "订阅即将到期"
            urgency = "您的订阅还有 <b>" + str(days_left) + " 天</b>到期，记得提前续费哦！"

        expire_str = sub.expires_at.strftime("%Y-%m-%d %H:%M")
        sub_url = sub.subscription_url if hasattr(sub, 'subscription_url') and sub.subscription_url else ""

        msg = (
            emoji + " <b>" + title + "</b>\n\n"
            + urgency + "\n\n"
            "⏳ 到期时间：" + expire_str + "\n\n"
            "💡 续费方式：点击下方 ⚡ 购买VPN 按钮选择套餐续费\n"
        )
        if sub_url:
            msg += "\n📋 您的订阅链接：\n<code>" + sub_url + "</code>"

        try:
            await bot.send_message(
                chat_id=user.id,
                text=msg,
                parse_mode="HTML"
            )
            logger.info("🔔 已发送到期提醒给用户 " + str(user.id) + "，剩余 " + str(days_left) + " 天")
        except Exception as e:
            logger.warning("发送提醒失败 用户" + str(user.id) + ": " + str(e))



async def sync_subscription_urls():
    """每天同步 Marzban 最新订阅链接到数据库"""
    from src.database.core import async_session
    from src.database.models import Subscription
    from src.services.marzban_api import api
    from sqlalchemy import select
    import aiohttp
    from loguru import logger

    async with async_session() as session:
        subs = (await session.scalars(select(Subscription))).all()
        for sub in subs:
            if not sub.marzban_username:
                continue
            try:
                headers = await api._headers()
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(
                        api.host + "/api/user/" + sub.marzban_username,
                        headers=headers
                    ) as r:
                        if r.status == 200:
                            data = await r.json()
                            new_url = data.get("subscription_url", "")
                            if new_url and not new_url.startswith("http"):
                                new_url = api.host + new_url
                            if new_url:
                                sub.subscription_url = new_url
            except Exception as e:
                logger.warning("同步订阅链接失败: " + str(e))
        await session.commit()
        logger.info("✅ 订阅链接同步完成")


async def sync_marzban_settings():
    """根据用户当前有效套餐，同步正确的设置到 Marzban"""
    from src.database.core import async_session
    from src.database.models import Subscription, User
    from src.services.marzban_api import api
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from datetime import datetime
    from loguru import logger
    import aiohttp

    now = datetime.now()

    async with async_session() as session:
        # 获取所有用户
        users = (await session.scalars(select(User))).all()

    for user in users:
        async with async_session() as session:
            subs = (await session.scalars(
                select(Subscription).where(Subscription.user_id == user.id)
            )).all()

        active_time = None
        active_traffic = None
        marzban_username = None

        for s in subs:
            if not marzban_username and s.marzban_username:
                marzban_username = s.marzban_username
            pt = getattr(s, 'plan_type', 'time')
            if pt == 'time' and s.expires_at > now:
                if active_time is None or s.expires_at > active_time.expires_at:
                    active_time = s
            elif pt == 'traffic':
                active_traffic = s

        if not marzban_username:
            continue

        try:
            headers = await api._headers()

            if active_time and active_traffic:
                # 同时有时间套餐和流量包
                # 时间套餐优先：200GB/月重置，有到期时间
                # 流量包保存在数据库，等时间套餐到期后自动激活
                expire_ts = int(active_time.expires_at.timestamp())
                payload = {
                    "expire": expire_ts,
                    "data_limit": int(200 * 1024**3),
                    "data_limit_reset_strategy": "month",
                    "status": "active"
                }

            elif active_time:
                # 只有时间套餐：200GB每月重置
                expire_ts = int(active_time.expires_at.timestamp())
                payload = {
                    "expire": expire_ts,
                    "data_limit": 200 * 1024**3,
                    "data_limit_reset_strategy": "month",
                    "status": "active"
                }

            elif active_traffic:
                # 只有流量包：不限时间，总GB用完即止，不重置
                traffic_gb = getattr(active_traffic, 'traffic_gb', 0) or 500
                payload = {
                    "expire": 0,
                    "data_limit": int(traffic_gb * 1024**3),
                    "data_limit_reset_strategy": "no_reset",
                    "status": "active"
                }

            else:
                # 没有有效套餐：禁用
                payload = {"status": "disabled"}

            async with aiohttp.ClientSession() as sess:
                async with sess.put(
                    api.host + "/api/user/" + marzban_username,
                    json=payload,
                    headers=headers
                ) as r:
                    result = await r.json()
                    logger.info("同步 " + marzban_username + " -> " + str(payload.get("status", "active")))

        except Exception as e:
            logger.warning("同步 Marzban 设置失败 " + marzban_username + ": " + str(e))

def start_scheduler():
    # 每天 10:00 执行统计
    scheduler.add_job(collect_daily_stats, 'cron', hour=10, minute=0)

    # 每天 09:00 检查到期提醒（北京时间需+8，服务器UTC时间01:00）
    scheduler.add_job(
        check_expiring_subscriptions,
        'cron',
        hour=1,   # UTC 01:00 = 北京时间 09:00
        minute=0
    )

    scheduler.start()
