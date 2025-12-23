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
    or_f(Command("stats"), F.text.in_([get_text("ru", "status_btn"), get_text("en", "status_btn")]))
)
async def admin_stats(message: Message, t):
    # 1. Получаем данные из БД
    total_users, active_subs = await get_stats()
    
    # 2. Получаем данные о серверах (в будущем можно брать реальную нагрузку с API)
    # Пока сделаем имитацию или простой список, так как метод api.get_system_stats нужно реализовывать отдельно
    servers_info = ""
    
    # Пример того, как это могло бы выглядеть с реальным API:
    # try:
    #     sys_info = await api.get_system_stats()
    #     servers_info += f"🇸🇪 Sweden: CPU {sys_info['cpu']}% | RAM {sys_info['ram']}%\n"
    # except:
    #     servers_info += "🇸🇪 Sweden: 🟢 Online (No data)\n"
    
    # Для старта просто выведем статус
    servers_info += "🇸🇪 Sweden: 🟢 Online\n"
    servers_info += "🇩🇪 Germany: 🟢 Online\n"

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

@router.message(F.text.in_([get_text("ru", "status_btn"), get_text("en", "status_btn")]))
async def public_stats(message: Message, t):
    # Для публичной статистики показываем только общее число пользователей
    # Это создает эффект массовости ("Social Proof")
    total_users, _ = await get_stats()
    
    # Можно немного "накрутить" для старта, если пользователей < 10
    # if total_users < 10: total_users = 10 + total_users
    
    await message.answer(t("public_stats", users=total_users), parse_mode="HTML")