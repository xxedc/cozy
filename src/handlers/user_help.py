from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from src.utils.translations import get_text
from src.keyboards.builders import help_kb, guides_kb

router = Router()

@router.message(F.text.in_(["🆘 帮助中心", "🆘 帮助", get_text("ru", "help_btn")]))
async def help_menu(message: Message, t, lang):
    text = (
        "🆘 <b>帮助中心</b>\n\n"
        "请选择以下分类获取帮助：\n\n"
        "📚 <b>配置教程</b> — 客户端下载和配置\n"
        "❓ <b>常见问题</b> — 速度/设备/续期问题\n"
        "👨‍💻 <b>联系客服</b> — 人工在线支持"
    )
    await message.answer(text, reply_markup=help_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "help_main")
async def back_to_help(callback: CallbackQuery, t, lang):
    await callback.message.edit_text(
        t("help_text"),
        reply_markup=help_kb(lang),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "help_faq")
async def show_faq(callback: CallbackQuery, t, lang):
    builder = InlineKeyboardBuilder()
    builder.button(text=t("btn_back"), callback_data="help_main")
    
    await callback.message.edit_text(
        t("faq_text"),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("help_guides"))
async def show_guides(callback: CallbackQuery, t, lang):
    # Если в data есть метка from_profile, то кнопка назад должна вести в профиль
    back_cb = "back_to_profile" if "from_profile" in callback.data else "help_main"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🍏 iOS / macOS", url="https://apps.apple.com/app/shadowrocket/id932747118")
    builder.button(text="🤖 Android", url="https://github.com/2dust/v2rayNG/releases/latest")
    builder.button(text="💻 Windows", url="https://github.com/2dust/v2rayN/releases/latest")
    builder.button(text="👨‍💻 联系客服", url="https://t.me/xxedce")
    builder.button(text="🔙 返回", callback_data=back_cb)
    builder.adjust(1)

    text = (
        "<b>📚 配置教程</b>\n\n"
        "选择您的设备下载客户端：\n\n"
        "🍏 <b>iOS / macOS</b>：Shadowrocket / V2Box\n"
        "🤖 <b>Android</b>：v2rayNG / Clash\n"
        "💻 <b>Windows</b>：v2rayN / Clash\n\n"
        "下载后在客户端中选择<b>添加订阅</b>，\n"
        "粘贴您的订阅链接即可使用。\n\n"
        "💡 订阅链接在 <b>📦 我的订阅</b> 中获取"
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")