import re
from datetime import datetime as dt

from dateutil.relativedelta import relativedelta

from app.models.user import User, UserResponse, UserStatus
from app.models.user_template import UserTemplate
from app.utils.system import readable_size

statuses = {
    UserStatus.active: "✅",
    UserStatus.expired: "🕰",
    UserStatus.limited: "🪫",
    UserStatus.disabled: "❌",
    UserStatus.on_hold: "🔌",
}


def time_to_string(time: dt):
    now = dt.now()
    if time < now:
        delta = now - time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if days > 0:
            return f"约 <code>{days}</code> 天前"
        elif hours > 0:
            return f"约 <code>{hours}</code> 小时前"
        elif minutes > 0:
            return f"约 <code>{minutes}</code> 分钟前"
        else:
            return "刚刚"
    else:
        delta = time - now
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        if days > 0:
            return f"还有约 <code>{days}</code> 天"
        elif hours > 0:
            return f"还有约 <code>{hours}</code> 小时"
        elif minutes > 0:
            return f"还有约 <code>{minutes}</code> 分钟"
        else:
            return "即将到期"


def get_user_info_text(db_user: User) -> str:
    user: UserResponse = UserResponse.model_validate(db_user)
    data_limit = readable_size(user.data_limit) if user.data_limit else "无限制"
    used_traffic = readable_size(user.used_traffic) if user.used_traffic else "-"
    data_left = readable_size(user.data_limit - user.used_traffic) if user.data_limit else "-"
    on_hold_timeout = user.on_hold_timeout.strftime("%Y-%m-%d") if user.on_hold_timeout else "-"
    on_hold_duration = user.on_hold_expire_duration // (24*60*60) if user.on_hold_expire_duration else None
    expiry_date = dt.fromtimestamp(user.expire).date() if user.expire else "永不"
    time_left = time_to_string(dt.fromtimestamp(user.expire)) if user.expire else "-"
    online_at = time_to_string(user.online_at) if user.online_at else "-"
    sub_updated_at = time_to_string(user.sub_updated_at) if user.sub_updated_at else "-"
    if user.status == UserStatus.on_hold:
        expiry_text = f"⏰ <b>暂停时长：</b> <code>{on_hold_duration} 天</code>（自动启用时间：<code>{on_hold_timeout}</code>）"
    else:
        expiry_text = f"📅 <b>到期日期：</b> <code>{expiry_date}</code>（{time_left}）"
    return f"""\
{statuses[user.status]} <b>状态：</b> <code>{user.status.title()}</code>

🔤 <b>用户名：</b> <code>{user.username}</code>

🔋 <b>流量限额：</b> <code>{data_limit}</code>
📶 <b>已用流量：</b> <code>{used_traffic}</code>（剩余 <code>{data_left}</code>）
{expiry_text}

🔌 <b>最后在线：</b> {online_at}
🔄 <b>订阅更新时间：</b> {sub_updated_at}
📱 <b>上次订阅客户端：</b> <blockquote>{user.sub_last_user_agent or "-"}</blockquote>

📝 <b>备注：</b> <blockquote expandable>{user.note or "空"}</blockquote>
👨‍💻 <b>管理员：</b> <code>{db_user.admin.username if db_user.admin else "-"}</code>
🚀 <b><a href="{user.subscription_url}">订阅链接</a>：</b> <code>{user.subscription_url}</code>"""


def get_template_info_text(template: UserTemplate):
    protocols = ""
    for p, inbounds in template.inbounds.items():
        protocols += f"\n├─ <b>{p.upper()}</b>\n"
        protocols += "├───" + ", ".join([f"<code>{i}</code>" for i in inbounds])
    data_limit = readable_size(template.data_limit) if template.data_limit else "无限制"
    expire = ((dt.now() + relativedelta(seconds=template.expire_duration))
              .strftime("%Y-%m-%d")) if template.expire_duration else "永不"
    text = f"""
📊 模板信息：
ID：<b>{template.id}</b>
流量限额：<b>{data_limit}</b>
到期日期：<b>{expire}</b>
用户名前缀：<b>{template.username_prefix if template.username_prefix else "-"}</b>
用户名后缀：<b>{template.username_suffix if template.username_suffix else "-"}</b>
协议：{protocols}"""
    return text


def get_number_at_end(username: str):
    n = re.search(r'(\d+)$', username)
    if n:
        return n.group(1)
