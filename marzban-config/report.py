import datetime

from app import logger
from app.db.models import User
from app.telegram import bot
from telebot.apihelper import ApiTelegramException
from datetime import datetime
from app.telegram.utils.keyboard import BotKeyboard
from app.utils.system import readable_size
from config import TELEGRAM_ADMIN_ID, TELEGRAM_LOGGER_CHANNEL_ID
from telebot.formatting import escape_html
from app.models.admin import Admin
from app.models.user import UserDataLimitResetStrategy


def report(text: str, chat_id: int = None, parse_mode="html", keyboard=None):
    if bot and (TELEGRAM_ADMIN_ID or TELEGRAM_LOGGER_CHANNEL_ID):
        try:
            if TELEGRAM_LOGGER_CHANNEL_ID:
                bot.send_message(TELEGRAM_LOGGER_CHANNEL_ID, text, parse_mode=parse_mode)
            else:
                for admin in TELEGRAM_ADMIN_ID:
                    bot.send_message(admin, text, parse_mode=parse_mode, reply_markup=keyboard)
            if chat_id:
                bot.send_message(chat_id, text, parse_mode=parse_mode)
        except ApiTelegramException as e:
            logger.error(e)


def report_new_user(
        user_id: int,
        username: str,
        by: str,
        expire_date: int,
        data_limit: int,
        proxies: list,
        has_next_plan: bool,
        data_limit_reset_strategy: UserDataLimitResetStrategy,
        admin: Admin = None
):
    text = ''\'\
🆕 <b>#新建用户</b>
➖➖➖➖➖➖➖➖➖
<b>用户名：</b> <code>{username}</code>
<b>流量限额：</b> <code>{data_limit}</code>
<b>到期日期：</b> <code>{expire_date}</code>
<b>协议：</b> <code>{proxies}</code>
<b>流量重置策略：</b> <code>{data_limit_reset_strategy}</code>
<b>有续费套餐：</b> <code>{next_plan}</code>
➖➖➖➖➖➖➖➖➖
<b>所属管理员：</b> <code>{belong_to}</code>
<b>操作人：</b> <b>#{by}</b>\'\'\'\'.format(
        belong_to=escape_html(admin.username) if admin else None,
        by=escape_html(by),
        username=escape_html(username),
        data_limit=readable_size(data_limit) if data_limit else "无限制",
        expire_date=datetime.fromtimestamp(expire_date).strftime("%H:%M:%S %Y-%m-%d") if expire_date else "永不",
        proxies="" if not proxies else ", ".join([escape_html(proxy) for proxy in proxies]),
        data_limit_reset_strategy=escape_html(data_limit_reset_strategy),
        next_plan="是" if has_next_plan else "否",
    )

    return report(
        chat_id=admin.telegram_id if admin and admin.telegram_id else None,
        text=text,
        keyboard=BotKeyboard.user_menu({
            'username': username,
            'id': user_id,
            'status': 'active'
        }, with_back=False)
    )


def report_user_modification(
        username: str,
        expire_date: int,
        data_limit: int,
        proxies: list,
        has_next_plan: bool,
        by: str,
        data_limit_reset_strategy: UserDataLimitResetStrategy,
        admin: Admin = None
):
    text = ''\'\
✏️ <b>#修改用户</b>
➖➖➖➖➖➖➖➖➖
<b>用户名：</b> <code>{username}</code>
<b>流量限额：</b> <code>{data_limit}</code>
<b>到期日期：</b> <code>{expire_date}</code>
<b>协议：</b> <code>{protocols}</code>
<b>流量重置策略：</b> <code>{data_limit_reset_strategy}</code>
<b>有续费套餐：</b> <code>{next_plan}</code>
➖➖➖➖➖➖➖➖➖
<b>所属管理员：</b> <code>{belong_to}</code>
<b>操作人：</b> <b>#{by}</b>\
    \'\'\'\'.format(
        belong_to=escape_html(admin.username) if admin else None,
        by=escape_html(by),
        username=escape_html(username),
        data_limit=readable_size(data_limit) if data_limit else "无限制",
        expire_date=datetime.fromtimestamp(expire_date).strftime("%H:%M:%S %Y-%m-%d") if expire_date else "永不",
        protocols=', '.join([p for p in proxies]),
        data_limit_reset_strategy=escape_html(data_limit_reset_strategy),
        next_plan="是" if has_next_plan else "否",
    )

    return report(
        chat_id=admin.telegram_id if admin and admin.telegram_id else None,
        text=text,
        keyboard=BotKeyboard.user_menu({'username': username, 'status': 'active'}, with_back=False))


def report_user_deletion(username: str, by: str, admin: Admin = None):
    text = ''\'\
🗑 <b>#删除用户</b>
➖➖➖➖➖➖➖➖➖
<b>用户名</b>：<code>{username}</code>
➖➖➖➖➖➖➖➖➖
<b>所属管理员：</b> <code>{belong_to}</code>
<b>操作人</b>：<b>#{by}</b>\
    \'\'\'\'.format(
        belong_to=escape_html(admin.username) if admin else None,
        by=escape_html(by),
        username=escape_html(username)
    )
    return report(chat_id=admin.telegram_id if admin and admin.telegram_id else None, text=text)


def report_status_change(username: str, status: str, admin: Admin = None):
    _status = {
        'active': '✅ <b>#已激活</b>',
        'disabled': '❌ <b>#已禁用</b>',
        'limited': '🪫 <b>#已超限</b>',
        'expired': '🕔 <b>#已过期</b>'
    }
    text = ''\'\
{status}
➖➖➖➖➖➖➖➖➖
<b>用户名</b>：<code>{username}</code>
<b>所属管理员：</b> <code>{belong_to}</code>\
    \'\'\'\'.format(
        belong_to=escape_html(admin.username) if admin else None,
        username=escape_html(username),
        status=_status[status]
    )
    return report(chat_id=admin.telegram_id if admin and admin.telegram_id else None, text=text)


def report_user_usage_reset(username: str, by: str, admin: Admin = None):
    text = """  
🔁 <b>#重置流量</b>
➖➖➖➖➖➖➖➖➖
<b>用户名</b>：<code>{username}</code>
➖➖➖➖➖➖➖➖➖
<b>所属管理员：</b> <code>{belong_to}</code>
<b>操作人</b>：<b>#{by}</b>\
    """.format(
        belong_to=escape_html(admin.username) if admin else None,
        by=escape_html(by),
        username=escape_html(username)
    )
    return report(chat_id=admin.telegram_id if admin and admin.telegram_id else None, text=text)


def report_user_data_reset_by_next(user: User, admin: Admin = None):
    text = """  
🔁 <b>#自动重置</b>
➖➖➖➖➖➖➖➖➖
<b>用户名：</b> <code>{username}</code>
<b>流量限额：</b> <code>{data_limit}</code>
<b>到期日期：</b> <code>{expire_date}</code>
➖➖➖➖➖➖➖➖➖
    """.format(
        username=escape_html(user.username),
        data_limit=readable_size(user.data_limit) if user.data_limit else "无限制",
        expire_date=datetime.fromtimestamp(user.expire).strftime("%H:%M:%S %Y-%m-%d") if user.expire else "永不",
    )
    return report(chat_id=admin.telegram_id if admin and admin.telegram_id else None, text=text)


def report_user_subscription_revoked(username: str, by: str, admin: Admin = None):
    text = """  
🔁 <b>#重置订阅</b>
➖➖➖➖➖➖➖➖➖
<b>用户名</b>：<code>{username}</code>
➖➖➖➖➖➖➖➖➖
<b>所属管理员：</b> <code>{belong_to}</code>
<b>操作人</b>：<b>#{by}</b>\
    """.format(
        belong_to=escape_html(admin.username) if admin else None,
        by=escape_html(by),
        username=escape_html(username)
    )
    return report(chat_id=admin.telegram_id if admin and admin.telegram_id else None, text=text)


def report_login(username: str, password: str, client_ip: str, status: str):
    text = """  
🔐 <b>#登录通知</b>
➖➖➖➖➖➖➖➖➖
<b>用户名</b>：<code>{username}</code>
<b>密码</b>：<code>{password}</code>
<b>客户端IP</b>：<code>{client_ip}</code>
➖➖➖➖➖➖➖➖➖
<b>登录状态</b>：<code>{status}</code>  
    """.format(
        username=escape_html(username),
        password=escape_html(password),
        status=escape_html(status),
        client_ip=escape_html(client_ip)
    )
    return report(text=text)
