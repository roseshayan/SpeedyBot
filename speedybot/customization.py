from html import escape

from . import context as C
from . import ui


def _send(chat_id, text, markup=None):
    C.BOT.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)


def _guard(call):
    if C.is_admin(call.from_user.id):
        return True
    C.BOT.answer_callback_query(call.id, "دسترسی ندارید.", show_alert=True)
    return False


def _panel(chat_id):
    lines = [
        "🏷 <b>برند و منوی مشتری</b>",
        "━━━━━━━━━━━━━━━━",
        f"نام فعلی برند: <b>{escape(C.brand_name())}</b>",
        "",
        "دکمه‌های فعال در پنل مشتری:",
    ]
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for key, label in C.CUSTOMER_MENU_KEYS.items():
        enabled = C.menu_visible(key)
        lines.append(f"{'🟢' if enabled else '🔴'} {escape(label)}")
        markup.add(
            C.inline(
                f"{'🟢' if enabled else '🔴'} {label}",
                callback_data=f"custom:toggle:{key}",
                style_name="success" if enabled else "danger",
            )
        )
    markup.row(
        C.inline("🏷 تغییر نام برند", callback_data="custom:brand", style_name="primary"),
        C.inline("♻️ نمایش همه دکمه‌ها", callback_data="custom:reset", style_name="success"),
    )
    markup.add(C.inline("↩️ پنل مدیریت", callback_data="custom:home", style_name="primary"))
    lines += [
        "",
        "ℹ️ مخفی‌کردن دکمه، آن را از رابط مشتری حذف می‌کند. برای «نظر و امتیاز»، کلید فعال/غیرفعال‌سازی کامل قابلیت همچنان در بخش بازخورد مشتری وجود دارد.",
    ]
    _send(chat_id, "\n".join(lines), markup)


def _save_brand(message, actor):
    raw = (message.text or "").strip()
    if raw == "🔙 بازگشت به منوی اصلی":
        _send(message.chat.id, ui.admin_home(), ui.admin_menu())
        return
    name = " ".join(raw.split())
    if name == "0":
        name = "فروشگاه"
    if not name or len(name) > 64:
        C.BOT.send_message(
            message.chat.id,
            "❌ نام برند باید بین ۱ تا ۶۴ کاراکتر باشد.",
            reply_markup=ui.admin_menu(),
        )
        return

    old = C.brand_name()
    C.set_setting("brand_name", name)
    _sync_default_content(old, name)
    C.audit("BRAND_CHANGED", actor, name, send=False)
    C.BOT.send_message(
        message.chat.id,
        f"✅ نام برند روی «{name}» تنظیم شد.",
        reply_markup=ui.admin_menu(),
    )


def _sync_default_content(old_brand, new_brand):
    defaults = {
        "welcome_text": (
            "سلام به **فروشگاه** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.",
            f"سلام به **{new_brand}** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.",
        ),
        "faq_text": (
            "📚 **راهنمای فروشگاه**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید.",
            f"📚 **راهنمای {new_brand}**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید.",
        ),
    }
    for key, (neutral_default, branded_default) in defaults.items():
        value = C.setting(key, "")
        if value == neutral_default:
            C.set_setting(key, branded_default)
            continue
        updated = value.replace("SpeedyBot", new_brand).replace("SpeedPing", new_brand)
        if old_brand and old_brand != "فروشگاه" and old_brand != new_brand:
            updated = updated.replace(old_brand, new_brand)
        if updated != value:
            C.set_setting(key, updated)


def callback(call):
    if not _guard(call):
        return
    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    chat_id = call.message.chat.id
    actor = int(call.from_user.id)

    if action == "panel":
        C.BOT.answer_callback_query(call.id)
        _panel(chat_id)
        return
    if action == "home":
        C.BOT.answer_callback_query(call.id)
        _send(chat_id, ui.admin_home(), ui.admin_menu())
        return
    if action == "brand":
        C.BOT.answer_callback_query(call.id)
        msg = C.BOT.send_message(
            chat_id,
            "🏷 نام برند جدید را بفرستید.\nحداکثر ۶۴ کاراکتر. برای بازگشت به نام عمومی «فروشگاه»، عدد <code>0</code> را بفرستید.",
            parse_mode="HTML",
            reply_markup=C.CORE.back_menu(),
        )
        C.BOT.register_next_step_handler(msg, _save_brand, actor)
        return
    if action == "toggle" and len(parts) > 2:
        key = parts[2]
        if key not in C.CUSTOMER_MENU_KEYS:
            C.BOT.answer_callback_query(call.id, "دکمه نامعتبر است.", show_alert=True)
            return
        new_value = "0" if C.menu_visible(key) else "1"
        C.set_setting(f"menu_{key}_visible", new_value)
        C.audit("CUSTOMER_MENU_TOGGLED", actor, key, new_value, send=False)
        C.BOT.answer_callback_query(
            call.id,
            "نمایش داده می‌شود ✅" if new_value == "1" else "از منوی مشتری مخفی شد ✅",
        )
        _panel(chat_id)
        return
    if action == "reset":
        for key in C.CUSTOMER_MENU_KEYS:
            C.set_setting(f"menu_{key}_visible", "1")
        C.audit("CUSTOMER_MENU_RESET", actor, "all", send=False)
        C.BOT.answer_callback_query(call.id, "همه دکمه‌ها فعال شدند ✅")
        _panel(chat_id)
        return


def register():
    C.BOT.callback_query_handler(func=lambda call: (call.data or "").startswith("custom:"))(callback)
    C.promote_callback()
