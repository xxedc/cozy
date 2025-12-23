from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.utils.translations import get_text

def buy_type_kb(lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    # Сначала "Мульти" - психологически более дорогой и желаемый продукт ставим первым
    builder.button(text=get_text(lang, "btn_multi"), callback_data="buy_multi")
    builder.button(text=get_text(lang, "btn_single"), callback_data="type_single")
    builder.adjust(1)
    return builder.as_markup()

def location_kb(lang: str = "ru", prefix: str = "buy"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "swe"), callback_data=f"{prefix}_swe")
    builder.button(text=get_text(lang, "ger"), callback_data=f"{prefix}_ger")
    
    # Кнопку "Назад" показываем только при покупке, так как там есть меню типов
    if prefix == "buy":
        builder.button(text=get_text(lang, "btn_back"), callback_data="back_to_types")
        
    builder.adjust(1)
    return builder.as_markup()

def duration_kb(lang: str, location_code: str):
    builder = InlineKeyboardBuilder()
    
    # Базовая цена зависит от типа (Мульти чуть дороже)
    base_price = 199 if location_code == "multi" else 169
    
    # Сетка тарифов (дни, множитель цены)
    plans = [
        (30, 1, "duration_1m"),
        (90, 2.5, "duration_3m"),   # 3 месяца по цене 2.5
        (180, 4.5, "duration_6m"),  # 6 месяцев по цене 4.5
        (365, 8, "duration_1y")     # 12 месяцев по цене 8
    ]

    for days, multiplier, text_key in plans:
        price = int(base_price * multiplier)
        # callback: pay_локация_дни_цена
        builder.button(
            text=get_text(lang, text_key, price=price), 
            callback_data=f"prepay_{location_code}_{days}_{price}"
        )
    
    # Если это мульти-доступ, назад ведет к выбору типа.
    # Если это конкретная страна, назад ведет к списку стран.
    back_callback = "back_to_types" if location_code == "multi" else "type_single"
    
    builder.button(text=get_text(lang, "btn_back"), callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()

def payment_method_kb(lang: str, balance: int, price: int, location_code: str, days: int):
    builder = InlineKeyboardBuilder()
    
    # 1. Оплата с баланса
    if balance >= price:
        # Хватает денег -> Кнопка активна
        builder.button(
            text=get_text(lang, "pay_balance_btn", price=price),
            callback_data=f"confirm_balance_{location_code}_{days}_{price}"
        )
    else:
        # Не хватает -> Кнопка ведет на пополнение (или просто неактивна визуально)
        diff = price - balance
        builder.button(
            text=get_text(lang, "pay_balance_disabled", diff=diff),
            callback_data=f"top_up_buy_{location_code}_{days}_{price}" # Ведем на пополнение с контекстом покупки
        )

    # 2. Оплата картой (всегда доступна)
    builder.button(
        text=get_text(lang, "pay_online_btn", price=price),
        callback_data=f"confirm_online_{location_code}_{days}_{price}"
    )
    
    builder.button(text=get_text(lang, "btn_back"), callback_data=f"buy_{location_code}")
    builder.adjust(1)
    return builder.as_markup()

def top_up_kb(lang: str, back_callback: str = "back_to_profile", context_suffix: str = ""):
    builder = InlineKeyboardBuilder()
    amounts = [100, 200, 300, 500, 1000]
    for amount in amounts:
        # Если есть контекст (например _buy_multi_30_199), добавляем его к callback
        builder.button(text=f"{amount}₽", callback_data=f"add_funds_{amount}{context_suffix}")
    builder.button(text=get_text(lang, "btn_back"), callback_data=back_callback)
    builder.adjust(2)
    return builder.as_markup()

def language_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    builder.adjust(2)
    return builder.as_markup()

def profile_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "promo_btn"), callback_data="activate_promo")
    builder.button(text=get_text(lang, "top_up_btn"), callback_data="top_up_menu")
    # Добавляем метку _from_profile, чтобы знать, откуда пришел юзер
    builder.button(text=get_text(lang, "btn_instruction"), callback_data="help_guides_from_profile")
    builder.adjust(1)
    return builder.as_markup()

def help_kb(lang: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text(lang, "btn_instruction"), callback_data="help_guides")
    builder.button(text=get_text(lang, "btn_faq"), callback_data="help_faq")
    # Ссылка на поддержку (замените username на свой)
    builder.button(text=get_text(lang, "btn_support"), url="https://t.me/muroshark") 
    builder.adjust(1)
    return builder.as_markup()

def instruction_links_kb():
    """Клавиатура только со ссылками на инструкции (без кнопки Назад)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🍏 iOS / macOS", url="https://telegra.ph/iOS-Guide-Placeholder")
    builder.button(text="🤖 Android", url="https://telegra.ph/Android-Guide-Placeholder")
    builder.button(text="💻 Windows", url="https://telegra.ph/Windows-Guide-Placeholder")
    builder.adjust(1)
    return builder

def guides_kb(lang: str, back_callback: str = "help_main"):
    builder = instruction_links_kb()
    builder.button(text=get_text(lang, "btn_back"), callback_data=back_callback)
    builder.adjust(1)
    return builder.as_markup()

def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="✉️ Рассылка", callback_data="admin_broadcast")
    builder.button(text="🎟 Промокоды", callback_data="admin_promos")
    builder.button(text="📊 Статистика", callback_data="admin_stats_full")
    builder.adjust(2)
    return builder.as_markup()

def admin_back_kb(callback_data: str = "admin_home"):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=callback_data)
    return builder.as_markup()

def admin_user_action_kb(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 +Баланс", callback_data=f"admin_add_balance_{user_id}")
    builder.button(text="🎁 Выдать подписку", callback_data=f"admin_give_sub_{user_id}")
    builder.button(text="🔙 Назад", callback_data="admin_users")
    builder.adjust(2)
    return builder.as_markup()

def admin_promo_type_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Деньги на баланс", callback_data="create_promo_balance")
    builder.button(text="🗓 Дни подписки", callback_data="create_promo_days")
    builder.button(text="🔙 Назад", callback_data="admin_promos")
    builder.adjust(1)
    return builder.as_markup()

def admin_promos_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать новый", callback_data="admin_promo_create_start")
    builder.button(text="📜 Список активных", callback_data="admin_promo_list")
    builder.button(text="🔙 Назад", callback_data="admin_home")
    builder.adjust(1)
    return builder.as_markup()

def admin_promos_list_kb(promos):
    builder = InlineKeyboardBuilder()
    for promo in promos:
        # Показываем Код | Использовано/Лимит
        uses = f"{promo.current_uses}/{promo.max_uses if promo.max_uses > 0 else '∞'}"
        builder.button(text=f"🎟 {promo.code} ({uses})", callback_data=f"admin_promo_view_{promo.id}")
    builder.button(text="🔙 Назад", callback_data="admin_promos")
    builder.adjust(1)
    return builder.as_markup()

def admin_promo_view_kb(promo_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🗑 Удалить", callback_data=f"admin_promo_delete_{promo_id}")
    builder.button(text="🔙 Назад", callback_data="admin_promo_list")
    builder.adjust(1)
    return builder.as_markup()

def promo_sub_select_kb(subs, lang: str = "ru"):
    builder = InlineKeyboardBuilder()
    for sub in subs:
        # Маппинг кода локации (SWE, GER, MULTI) в красивое название
        loc_code = sub.server.location.lower()
        if loc_code == "multi":
            # Берем название из перевода, убираем лишнее в скобках для краткости
            loc_name = get_text(lang, "btn_multi").split("(")[0].strip()
        else:
            loc_name = get_text(lang, loc_code)
            
        label = f"{loc_name} | ⏳ {sub.expires_at.strftime('%d.%m')}"
        builder.button(text=label, callback_data=f"select_promo_sub_{sub.id}")
    builder.adjust(1)
    return builder.as_markup()