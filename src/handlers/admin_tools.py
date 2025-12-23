from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from contextlib import suppress
from loguru import logger

from src.config import settings
from src.database.requests import (
    get_stats, get_user, get_user_by_username, get_all_users_ids,
    update_user_balance, create_promo_code, get_user_subscriptions,
    get_all_promos, delete_promo, get_promo_by_id
)
from src.keyboards.builders import (
    admin_main_kb, admin_back_kb, admin_user_action_kb, admin_promo_type_kb,
    admin_promos_main_kb, admin_promos_list_kb, admin_promo_view_kb
)

router = Router()

# --- FSM States ---
class AdminStates(StatesGroup):
    find_user = State()
    add_balance = State()
    broadcast_text = State()
    create_promo_code = State()
    create_promo_value = State()
    create_promo_uses = State()

# --- Main Menu ---

@router.message(Command("admin"), F.from_user.id.in_(settings.ADMIN_IDS))
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    total_users, active_subs = await get_stats()
    
    text = (
        f"👮‍♂️ <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"💎 Активных подписок: <b>{active_subs}</b>\n\n"
        f"Выберите действие:"
    )
    await message.answer(text, reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_home")
async def admin_home_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    total_users, active_subs = await get_stats()
    text = (
        f"👮‍♂️ <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <b>{total_users}</b>\n"
        f"💎 Активных подписок: <b>{active_subs}</b>"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()

# --- User Management ---

@router.callback_query(F.data == "admin_users")
async def admin_users_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Отправьте <b>ID</b> пользователя или его <b>@username</b> ответным сообщением.",
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.find_user)

@router.message(AdminStates.find_user)
async def find_user_handler(message: Message, state: FSMContext):
    query = message.text.strip()
    user = None
    
    if query.isdigit():
        user = await get_user(int(query))
    else:
        user = await get_user_by_username(query)
    
    if not user:
        await message.answer("❌ Пользователь не найден. Попробуйте еще раз или нажмите Назад.", reply_markup=admin_back_kb("admin_users"))
        return

    # Показываем профиль найденного юзера
    subs = await get_user_subscriptions(user.id)
    subs_count = len(subs)
    
    text = (
        f"👤 <b>Пользователь найден!</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: @{user.username or 'Нет'}\n"
        f"💰 Баланс: <b>{user.balance}₽</b>\n"
        f"💎 Подписок: <b>{subs_count}</b>\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}"
    )
    
    await message.answer(text, reply_markup=admin_user_action_kb(user.id), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("admin_user_profile_"))
async def show_user_profile_cb(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[3])
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    subs = await get_user_subscriptions(user.id)
    subs_count = len(subs)
    
    text = (
        f"👤 <b>Пользователь найден!</b>\n\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"👤 Username: @{user.username or 'Нет'}\n"
        f"💰 Баланс: <b>{user.balance}₽</b>\n"
        f"💎 Подписок: <b>{subs_count}</b>\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y')}"
    )
    
    await callback.message.edit_text(text, reply_markup=admin_user_action_kb(user.id), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("admin_add_balance_"))
async def ask_balance_amount(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[3])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        f"💰 Введите сумму для пополнения баланса пользователя <code>{user_id}</code>:\n"
        "(Можно ввести отрицательное число для списания)",
        reply_markup=admin_back_kb(f"admin_user_profile_{user_id}"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_balance)

@router.message(AdminStates.add_balance)
async def process_add_balance(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data['target_user_id']
        
        await update_user_balance(user_id, amount)
        
        await message.answer(f"✅ Баланс пользователя {user_id} успешно изменен на {amount}₽.", reply_markup=admin_back_kb(f"admin_user_profile_{user_id}"))
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректное число.")

# --- Broadcast ---

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✉️ <b>Рассылка сообщений</b>\n\n"
        "Отправьте текст сообщения (можно с фото/видео), которое нужно разослать всем пользователям.",
        reply_markup=admin_back_kb(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.broadcast_text)

@router.message(AdminStates.broadcast_text)
async def broadcast_process(message: Message, state: FSMContext):
    users = await get_all_users_ids()
    count = 0
    
    status_msg = await message.answer(f"⏳ Начинаю рассылку на {len(users)} пользователей...")
    
    for user_id in users:
        try:
            # Метод copy_message позволяет отправить копию любого сообщения (текст, фото, стикер)
            await message.copy_to(chat_id=user_id)
            count += 1
        except Exception:
            pass # Игнорируем ошибки (блок бота и т.д.)
            
    await status_msg.edit_text(f"✅ Рассылка завершена!\nУспешно отправлено: {count} из {len(users)}")
    await state.clear()

# --- Promo Codes ---

@router.callback_query(F.data == "admin_promos")
async def promo_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎟 <b>Управление промокодами</b>\n\nВыберите действие:",
        reply_markup=admin_promos_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_promo_create_start")
async def promo_create_type(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎟 <b>Создание промокода</b>\n\nВыберите тип награды:",
        reply_markup=admin_promo_type_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("create_promo_"))
async def promo_ask_code(callback: CallbackQuery, state: FSMContext):
    p_type = callback.data.split("_")[2] # balance or days
    await state.update_data(promo_type="balance" if p_type == "balance" else "days")
    
    await callback.message.edit_text(
        "✍️ <b>Введите название промокода</b> (например, <code>SALE2024</code>):",
        reply_markup=admin_back_kb("admin_promo_create_start"),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.create_promo_code)

@router.message(AdminStates.create_promo_code)
async def promo_ask_value(message: Message, state: FSMContext):
    await state.update_data(promo_code=message.text.strip())
    data = await state.get_data()
    p_type_text = "сумму пополнения (₽)" if data['promo_type'] == 'balance' else "количество дней"
    
    await message.answer(
        f"🔢 Введите {p_type_text} (число):",
        reply_markup=admin_back_kb("admin_promo_create_start")
    )
    await state.set_state(AdminStates.create_promo_value)

@router.message(AdminStates.create_promo_value)
async def promo_ask_uses(message: Message, state: FSMContext):
    try:
        value = int(message.text)
        await state.update_data(promo_value=value)
        
        await message.answer(
            "🔢 <b>Введите количество активаций</b> (число):\n"
            "0 — для безлимитного использования.",
            reply_markup=admin_back_kb("admin_promos"),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.create_promo_uses)
    except ValueError:
        await message.answer("❌ Введите число.")

@router.message(AdminStates.create_promo_uses)
async def promo_finish(message: Message, state: FSMContext):
    try:
        max_uses = int(message.text)
        if max_uses < 0: raise ValueError
        
        data = await state.get_data()
        
        success = await create_promo_code(data['promo_code'], data['promo_type'], data['promo_value'], max_uses=max_uses)
        
        if success:
            uses_text = "Безлимит" if max_uses == 0 else str(max_uses)
            
            type_map = {
                "balance": "💰 Баланс",
                "days": "🗓 Дни подписки",
                "subscription": "🎁 Подписка"
            }
            type_display = type_map.get(data['promo_type'], data['promo_type'])
            
            await message.answer(
                f"✅ Промокод <code>{data['promo_code']}</code> создан!\n"
                f"Тип: {type_display}\n"
                f"Значение: {data['promo_value']}\n"
                f"Активаций: {uses_text}",
                reply_markup=admin_promos_main_kb(),
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Такой промокод уже существует!", reply_markup=admin_back_kb("admin_promos"))
            
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите неотрицательное число.")

# --- Promo List & Management ---

@router.callback_query(F.data == "admin_promo_list")
async def promo_list(callback: CallbackQuery):
    promos = await get_all_promos()
    
    if not promos:
        await callback.message.edit_text(
            "📜 <b>Список активных промокодов</b>\n\n"
            "Список пуст.",
            reply_markup=admin_back_kb("admin_promos"),
            parse_mode="HTML"
        )
        return

    await callback.message.edit_text(
        "📜 <b>Список активных промокодов</b>\n"
        "Нажмите на код для управления:",
        reply_markup=admin_promos_list_kb(promos),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_promo_view_"))
async def promo_view(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[3])
    promo = await get_promo_by_id(promo_id)
    
    if not promo:
        await callback.answer("Промокод не найден", show_alert=True)
        await promo_list(callback)
        return

    uses_str = f"{promo.current_uses} / {promo.max_uses if promo.max_uses > 0 else '∞'}"
    
    type_map = {
        "balance": "💰 Баланс",
        "days": "🗓 Дни подписки",
        "subscription": "🎁 Подписка"
    }
    type_display = type_map.get(promo.type, promo.type)

    text = (
        f"🎟 <b>Промокод:</b> <code>{promo.code}</code>\n\n"
        f"Тип: <b>{type_display}</b>\n"
        f"Значение: <b>{promo.value}</b>\n"
        f"Использований: <b>{uses_str}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_promo_view_kb(promo.id), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_promo_delete_"))
async def promo_delete_handler(callback: CallbackQuery):
    promo_id = int(callback.data.split("_")[3])
    try:
        await delete_promo(promo_id)
        await callback.answer("✅ Промокод удален")
        await promo_list(callback)
    except Exception as e:
        logger.exception(f"Ошибка при удалении промокода {promo_id}")
        await callback.answer("❌ Ошибка при удалении. Проверьте логи.", show_alert=True)

# --- Stats Shortcut ---
@router.callback_query(F.data == "admin_stats_full")
async def admin_stats_shortcut(callback: CallbackQuery, state: FSMContext):
    # Просто обновляем главное меню, так как там уже есть статистика
    await admin_home_cb(callback, state)

# --- Emoji Capture Tool (Legacy) ---
@router.message(F.entities, F.from_user.id.in_(settings.ADMIN_IDS))
async def capture_emoji_id(message: Message):
    for entity in message.entities:
        if entity.type == "custom_emoji":
            # Telegram API использует смещение в UTF-16, поэтому кодируем/декодируем для точности
            text_utf16 = message.text.encode('utf-16-le')
            start = entity.offset * 2
            end = (entity.offset + entity.length) * 2
            emoji_char = text_utf16[start:end].decode('utf-16-le')
            
            await message.reply(
                f"🆔 ID эмодзи: <code>{entity.custom_emoji_id}</code>\n"
                f"Эмодзи: <tg-emoji emoji-id='{entity.custom_emoji_id}'>{emoji_char}</tg-emoji>",
                parse_mode="HTML"
            )

            # Пытаемся получить и отправить эмодзи как стикер (обход ограничений отображения в тексте)
            try:
                stickers = await message.bot.get_custom_emoji_stickers(custom_emoji_ids=[entity.custom_emoji_id])
                if stickers:
                    await message.answer_sticker(stickers[0].file_id)
            except Exception:
                pass