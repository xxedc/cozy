from datetime import datetime as dt
from itertools import islice
from typing import Dict, List, Literal

from telebot import types  # noqa

from app import xray
from app.utils.system import readable_size


def chunk_dict(data: dict, size: int = 2):
    it = iter(data)
    for i in range(0, len(data), size):
        yield {k: data[k] for k in islice(it, size)}


class BotKeyboard:

    @staticmethod
    def main_menu():
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text='🔁 系统信息', callback_data='system'),
            types.InlineKeyboardButton(text='♻️ 重启 Xray', callback_data='restart'))
        keyboard.add(
            types.InlineKeyboardButton(text='👥 用户列表', callback_data='users:1'),
            types.InlineKeyboardButton(text='✏️ 批量编辑用户', callback_data='edit_all'))
        keyboard.add(
            types.InlineKeyboardButton(text='➕ 从模板创建用户', callback_data='template_add_user'))
        keyboard.add(
            types.InlineKeyboardButton(text='➕ 从模板批量创建', callback_data='template_add_bulk_user'))
        keyboard.add(
            types.InlineKeyboardButton(text='➕ 创建用户', callback_data='add_user'))
        keyboard.add(
            types.InlineKeyboardButton(text='➕ 批量创建用户', callback_data='add_bulk_user'))
        return keyboard

    @staticmethod
    def edit_all_menu():
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text='🗑 删除已过期', callback_data='delete_expired'),
            types.InlineKeyboardButton(text='🗑 删除已超限', callback_data='delete_limited'))
        keyboard.add(
            types.InlineKeyboardButton(text='🔋 流量 (➕|➖)', callback_data='add_data'),
            types.InlineKeyboardButton(text='📅 时间 (➕|➖)', callback_data='add_time'))
        keyboard.add(
            types.InlineKeyboardButton(text='➕ 添加入站', callback_data='inbound_add'),
            types.InlineKeyboardButton(text='➖ 移除入站', callback_data='inbound_remove'))
        keyboard.add(types.InlineKeyboardButton(text='🔙 返回', callback_data='cancel'))
        return keyboard

    @staticmethod
    def inbounds_menu(action, inbounds):
        keyboard = types.InlineKeyboardMarkup()
        for inbound in inbounds:
            keyboard.add(types.InlineKeyboardButton(text=inbound, callback_data=f'confirm_{action}:{inbound}'))
        keyboard.add(types.InlineKeyboardButton(text='🔙 返回', callback_data='cancel'))
        return keyboard

    @staticmethod
    def templates_menu(templates: Dict[str, int], username: str = None):
        keyboard = types.InlineKeyboardMarkup()
        for chunk in chunk_dict(templates):
            row = []
            for name, _id in chunk.items():
                row.append(
                    types.InlineKeyboardButton(
                        text=name,
                        callback_data=f'template_charge:{_id}:{username}' if username else f"template_add_user:{_id}"))
            keyboard.add(*row)
        keyboard.add(
            types.InlineKeyboardButton(
                text='🔙 返回',
                callback_data=f'user:{username}' if username else 'cancel'))
        return keyboard

    @staticmethod
    def random_username(template_id: str = ''):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text='🔡 随机用户名',
            callback_data=f'random:{template_id}'))
        keyboard.add(types.InlineKeyboardButton(
            text='🔙 取消',
            callback_data='cancel'))
        return keyboard

    @staticmethod
    def user_menu(user_info, with_back: bool = True, page: int = 1):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                text='❌ 禁用' if user_info['status'] == 'active' else '✅ 启用',
                callback_data=f"{'suspend' if user_info['status'] == 'active' else 'activate'}:{user_info['username']}"
            ),
            types.InlineKeyboardButton(
                text='🗑 删除',
                callback_data=f"delete:{user_info['username']}"
            ),
        )
        keyboard.add(
            types.InlineKeyboardButton(
                text='🚫 重置订阅',
                callback_data=f"revoke_sub:{user_info['username']}"),
            types.InlineKeyboardButton(
                text='✏️ 编辑',
                callback_data=f"edit:{user_info['username']}"))
        keyboard.add(
            types.InlineKeyboardButton(
                text='📝 编辑备注',
                callback_data=f"edit_note:{user_info['username']}"),
            types.InlineKeyboardButton(
                text='📡 节点链接',
                callback_data=f"links:{user_info['username']}"))
        keyboard.add(
            types.InlineKeyboardButton(
                text='🔁 重置流量',
                callback_data=f"reset_usage:{user_info['username']}"
            ),
            types.InlineKeyboardButton(
                text='🔋 充值',
                callback_data=f"charge:{user_info['username']}"
            )
        )
        if with_back:
            keyboard.add(
                types.InlineKeyboardButton(
                    text='🔙 返回',
                    callback_data=f'users:{page}'
                )
            )
        return keyboard

    @staticmethod
    def user_status_select():
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text="🟢 立即激活", callback_data='status:active'),
            types.InlineKeyboardButton(text="🟣 暂停等待", callback_data='status:onhold')
        )
        keyboard.add(types.InlineKeyboardButton(text='🔙 返回', callback_data='cancel'))
        return keyboard

    @staticmethod
    def show_links(username: str):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text="🖼 节点二维码", callback_data=f'genqr:configs:{username}'),
            types.InlineKeyboardButton(text="🚀 订阅二维码", callback_data=f'genqr:sub:{username}')
        )
        keyboard.add(types.InlineKeyboardButton(text='🔙 返回', callback_data=f'user:{username}'))
        return keyboard

    @staticmethod
    def subscription_page(sub_url: str):
        keyboard = types.InlineKeyboardMarkup()
        if sub_url[:4] == 'http':
            keyboard.add(types.InlineKeyboardButton(text='🚀 订阅页面', url=sub_url))
        return keyboard

    @staticmethod
    def confirm_action(action: str, username: str = None):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text='✅ 确认', callback_data=f"confirm:{action}:{username}"),
            types.InlineKeyboardButton(text='❌ 取消', callback_data=f"cancel")
        )
        return keyboard

    @staticmethod
    def charge_add_or_reset(username: str, template_id: int):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text='🔰 叠加到当前', callback_data=f"confirm:charge_add:{username}:{template_id}"),
            types.InlineKeyboardButton(text='♻️ 重置', callback_data=f"confirm:charge_reset:{username}:{template_id}"))
        keyboard.add(types.InlineKeyboardButton(text="取消", callback_data=f'user:{username}'))
        return keyboard

    @staticmethod
    def inline_cancel_action(callback_data: str = "cancel"):
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="🔙 取消", callback_data=callback_data))
        return keyboard

    @staticmethod
    def user_list(users: list, page: int, total_pages: int):
        keyboard = types.InlineKeyboardMarkup()
        if len(users) >= 2:
            users = [p for p in users]
            users = [users[i:i + 2] for i in range(0, len(users), 2)]
        else:
            users = [users]
        for user in users:
            row = []
            for p in user:
                status = {'active': '✅', 'expired': '🕰', 'limited': '📵', 'disabled': '❌', 'on_hold': '🔌'}
                row.append(types.InlineKeyboardButton(
                    text=f"{p.username} ({status[p.status]})",
                    callback_data=f'user:{p.username}:{page}'
                ))
            keyboard.row(*row)
        if total_pages > 1:
            if page > 1:
                keyboard.add(types.InlineKeyboardButton(text="⬅️ 上一页", callback_data=f'users:{page - 1}'))
            if page < total_pages:
                keyboard.add(types.InlineKeyboardButton(text="➡️ 下一页", callback_data=f'users:{page + 1}'))
        keyboard.add(types.InlineKeyboardButton(text='🔙 返回', callback_data='cancel'))
        return keyboard

    @staticmethod
    def select_protocols(
            selected_protocols: Dict[str, List[str]],
            action: Literal["edit", "create", "create_from_template"],
            username: str = None,
            data_limit: float = None,
            expire_date: dt = None,
            expire_on_hold_duration: int = None,
            expire_on_hold_timeout: dt = None
    ):
        keyboard = types.InlineKeyboardMarkup()
        if action == "edit":
            keyboard.add(types.InlineKeyboardButton(text="⚠️ 流量限额：", callback_data=f"help_edit"))
            keyboard.add(
                types.InlineKeyboardButton(
                    text=f"{readable_size(data_limit) if data_limit else '无限制'}",
                    callback_data=f"help_edit"
                ),
                types.InlineKeyboardButton(text="✏️ 修改", callback_data=f"edit_user:{username}:data"))
            if expire_on_hold_duration:
                keyboard.add(types.InlineKeyboardButton(text="⏳ 有效时长：", callback_data=f"edit_user:{username}:expire"))
                keyboard.add(
                    types.InlineKeyboardButton(
                        text=f"{int(expire_on_hold_duration / 24 / 60 / 60)} 天",
                        callback_data=f"edit_user:{username}:expire"
                    ),
                    types.InlineKeyboardButton(text="✏️ 修改", callback_data=f"edit_user:{username}:expire"))
                keyboard.add(types.InlineKeyboardButton(text="🌀 自动启用时间：", callback_data=f"edit_user:{username}:expire_on_hold_timeout"))
                keyboard.add(
                    types.InlineKeyboardButton(
                        text=f"{expire_on_hold_timeout.strftime('%Y-%m-%d') if expire_on_hold_timeout else '永不'}",
                        callback_data=f"edit_user:{username}:expire_on_hold_timeout"),
                    types.InlineKeyboardButton(text="✏️ 修改", callback_data=f"edit_user:{username}:expire_on_hold_timeout")
                )
            else:
                keyboard.add(types.InlineKeyboardButton(text="📅 到期日期：", callback_data=f"help_edit"))
                keyboard.add(
                    types.InlineKeyboardButton(
                        text=f"{expire_date.strftime('%Y-%m-%d') if expire_date else '永不'}",
                        callback_data=f"help_edit"
                    ),
                    types.InlineKeyboardButton(text="✏️ 修改", callback_data=f"edit_user:{username}:expire"))
        if action != 'create_from_template':
            for protocol, inbounds in xray.config.inbounds_by_protocol.items():
                keyboard.add(
                    types.InlineKeyboardButton(
                        text=f"🌐 {protocol.upper()} {'✅' if protocol in selected_protocols else '❌'}",
                        callback_data=f'select_protocol:{protocol}:{action}'
                    )
                )
                if protocol in selected_protocols:
                    for inbound in inbounds:
                        keyboard.add(
                            types.InlineKeyboardButton(
                                text=f"«{inbound['tag']}» {'✅' if inbound['tag'] in selected_protocols[protocol] else '❌'}",
                                callback_data=f'select_inbound:{inbound["tag"]}:{action}'
                            )
                        )
        keyboard.add(types.InlineKeyboardButton(
            text='✅ 完成',
            callback_data='confirm:edit_user' if action == "edit" else 'confirm:add_user'
        ))
        keyboard.add(types.InlineKeyboardButton(
            text='❌ 取消',
            callback_data=f'user:{username}' if action == "edit" else 'cancel'
        ))
        return keyboard
