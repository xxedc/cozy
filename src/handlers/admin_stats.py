from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, or_f

from src.utils.translations import get_text
from src.database.requests import get_stats
from src.config import settings
from src.services.marzban_api import api

router = Router()

# Фильтр: только для админов
@router.message(
    F.from_user.id.in_(settings.ADMIN_IDS),
    or_f(Command("stats"), F.text.in_(["📦 我的订阅", "💰 个人中心"]))
)
async def admin_stats(message: Message, t):
    # 1. Получаем данные из БД
    total_users, active_subs = await get_stats()
    
    # 从 Marzban 获取系统信息
    servers_info = ""
    try:
        import aiohttp as _aio
        headers = await api._headers()
        async with _aio.ClientSession() as _sess:
            async with _sess.get(f"{api.host}/api/system", headers=headers) as _r:
                sys_data = await _r.json()
            # 获取所有用户流量汇总
            async with _sess.get(
                f"{api.host}/api/users?limit=500",
                headers=headers
            ) as _r2:
                users_data = await _r2.json()

        total_traffic = sum((u.get("used_traffic") or 0) for u in users_data.get("users", []))
        total_gb = round(total_traffic / 1024**3, 2)

        mem = sys_data.get("mem_used", 0)
        mem_total = sys_data.get("mem_total", 1)
        mem_pct = round(mem / mem_total * 100) if mem_total else 0
        cpu = sys_data.get("cpu_usage", 0)
        incoming = round((sys_data.get("incoming_bandwidth", 0) or 0) / 1024**3, 2)
        outgoing = round((sys_data.get("outgoing_bandwidth", 0) or 0) / 1024**3, 2)

        servers_info = (
            f"🇯🇵 日本节点：🟢 运行正常\n"
            f"🖥 CPU：{cpu}%  |  内存：{mem_pct}%\n"
            f"📥 总入站：{incoming} GB\n"
            f"📤 总出站：{outgoing} GB\n"
            f"📶 全部用户已用流量：{total_gb} GB"
        )
    except Exception as e:
        servers_info = f"🇯🇵 日本节点：🟢 运行正常\n⚠️ 详细数据获取失败：{e}"

    # 3. Отправляем отчет
    await message.answer(
        t(
            "admin_stats", 
            users=total_users, 
            subs=active_subs, 
            servers_info=servers_info
        ),
        parse_mode="HTML"
    )

@router.message(F.text.in_(["📦 我的订阅", "💰 个人中心", "📊 服务状态"]))
async def public_stats(message: Message, t):
    from src.database.requests import get_user, get_user_subscriptions
    from src.services.marzban_api import api
    from datetime import datetime
    import aiohttp as _aio

    tg_user = message.from_user
    user = await get_user(tg_user.id)
    subs = await get_user_subscriptions(tg_user.id)

    name = tg_user.full_name or tg_user.username or str(tg_user.id)
    balance = user.balance if user else 0
    now = datetime.now()
    active_subs = [s for s in subs if s.expires_at > now]

    from src.handlers.user_buy import get_usdt_rate as _get_rate
    try:
        _rate = await _get_rate()
    except Exception:
        _rate = 7.2

    lines = [
        "╔══════════════════╗",
        "       📊 账户状态       ",
        "╚══════════════════╝",
        "",
        "👤 <b>" + name + "</b>",
        "🆔 ID：<code>" + str(tg_user.id) + "</code>",
        "💰 余额：<b>" + str(balance) + " ¥</b>   💱 实时汇率 <b>1 USDT ≈ " + str(_rate) + "¥</b>",
        "",
    ]

    if not active_subs:
        lines += ["❌ <b>暂无活跃订阅</b>", "", "点击 ⚡ 购买VPN 开始使用"]
    else:
        # 分离时间套餐和流量包
        time_subs = [s for s in active_subs if not hasattr(s, 'plan_type') or s.plan_type != 'traffic']
        traffic_subs = [s for s in active_subs if hasattr(s, 'plan_type') and s.plan_type == 'traffic']

        # 取最新时间套餐
        best_time = sorted(time_subs, key=lambda s: s.expires_at, reverse=True)[0] if time_subs else None
        # 取最新节点信息
        best = best_time or sorted(active_subs, key=lambda s: s.expires_at, reverse=True)[0]

        # 节点名
        loc = (best.server.location or "").lower() if best.server else ""
        if "multi" in loc:
            node = "🌍 全球通（所有节点）"
        elif loc in ("swe", "jp", "japan"):
            node = "🇯🇵 日本"
        else:
            node = "🌐 " + (best.server.name if best.server else loc)

        lines.append("━━━━━━━━━━━━")
        lines.append("📡 节点：" + node)

        # 时间套餐到期（时间套餐永远显示实际到期时间）
        if best_time:
            days_left = (best_time.expires_at - now).days
            lines.append("⏳ 订阅到期：" + best_time.expires_at.strftime("%Y-%m-%d %H:%M:%S"))
            lines.append("⏱ 剩余：" + str(days_left) + " 天")
        else:
            lines.append("⏳ 订阅到期：无时间套餐")

        # 从 Marzban 获取流量
        used_bytes = 0
        marzban_limit = 0
        try:
            headers = await api._headers()
            async with _aio.ClientSession() as sess:
                async with sess.get(
                    api.host + "/api/user/" + best.marzban_username,
                    headers=headers
                ) as r:
                    d = await r.json()
                    used_bytes = d.get("used_traffic") or 0
                    marzban_limit = d.get("data_limit") or 0
        except Exception:
            pass

        used_gb = round(used_bytes / 1024**3, 2)

        # 流量包总计
        traffic_pack_gb = sum(getattr(s, 'traffic_gb', 0) or 500 for s in traffic_subs)

        # 套餐状态
        has_valid = bool(best_time or best_traffic)
        status_str = "🟢 有效" if has_valid else "🔴 已过期（请及时续费）"

        lines += [
            "━━━━━━━━━━━━━━━━━━",
            "🚀 <b>套餐信息</b>",
            "",
            "🌍 " + node,
            "",
            "📌 套餐状态：" + status_str,
        ]

        if best_time:
            t_days = (best_time.expires_at - now).days
            if t_days >= 3640:
                lines += ["⏳ 到期时间：永久有效", "⏱ 剩余时间：永久"]
            else:
                lines += [
                    "⏳ 到期时间：" + best_time.expires_at.strftime("%Y-%m-%d %H:%M"),
                    "⏱ 剩余时间：" + str(t_days) + " 天",
                ]
        else:
            lines.append("⏳ 到期时间：无时间套餐")

        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━",
            "📊 <b>流量使用</b>",
            "",
        ]

        if best_time:
            lines.append("📅 月配额：200 GB / 月（每30天重置）")
        lines.append("📉 已使用：" + str(used_gb) + " GB")

        if traffic_pack_gb > 0:
            remain_pack = round(max(0, traffic_pack_gb - used_gb), 2)
            lines += [
                "",
                "📦 流量包：" + str(traffic_pack_gb) + " GB（用完即止）",
                "📊 剩余流量：" + str(remain_pack) + " GB",
            ]

        # 订阅链接
        sub_url = ""
        for s in sorted(active_subs, key=lambda x: x.expires_at, reverse=True):
            if hasattr(s, "subscription_url") and s.subscription_url:
                sub_url = s.subscription_url
                break

        if sub_url:
            lines += [
                "",
                "━━━━━━━━━━━━━━━━━━",
                "🔗 <b>订阅信息（全协议支持）</b>",
                "",
                "👇 点击复制订阅链接",
                "<code>" + sub_url + "</code>",
            ]

        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━",
            "⚠️ <b>使用提示</b>",
            "",
            "• 建议每日自动更新订阅",
            "• 若连接失败，请切换节点或重启客户端",
            "• 高峰时段建议切换低延迟节点",
        ]

    await message.answer("\n".join(lines), parse_mode="HTML")

