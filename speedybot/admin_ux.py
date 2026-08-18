"""Admin interaction safety and readable wizard prompts.

This module sits in front of the legacy/admin callback handlers. It fixes two
UX problems without rewriting the stable business handlers:

1. navigating/clicking another admin inline button cancels any stale
   register_next_step_handler state for that chat;
2. admin actions that expect typed input use clear Persian instructions with
   numbered fields, examples and an explicit cancel button.
"""

from html import escape

from telebot.handler_backends import ContinueHandling

from . import context as C
from . import ui


LEGACY_WIZARDS = {
    "plan_add", "plan_edit", "plan_toggle", "volume_add", "volume_toggle",
    "followup_delay", "cashback_percent", "discount_add", "gift_add",
    "discount_toggle", "gift_toggle", "channel_set", "admin_add",
    "admin_remove", "welcome_edit", "faq_edit", "affiliate_percent",
    "affiliate_wallet", "broadcast", "edit_card", "edit_holder", "edit_bank",
    "delete_user", "delete_sub", "guideadd", "guidedeleteask", "guideorderask",
}

PLUS_WIZARDS = {
    "blockadd", "blockremove", "catadd", "catrename", "catassign", "cattoggle",
    "trialset", "trialdel", "bcaud", "auditchat", "emojiset",
}

FIX_WIZARDS = {"trial_defaults", "plan_delete", "category_delete"}

# These legacy menu callbacks never answered their CallbackQuery, which leaves
# Telegram's spinner active and makes repeated clicks feel broken.
LEGACY_MENU_NEEDS_ACK = {
    "stats", "plans", "username_mode", "rewards", "security", "admins",
    "ops", "content", "affiliate", "affiliate_top", "notifications",
    "bank_config",
}


def _clear_step(chat_id):
    try:
        C.BOT.clear_step_handler_by_chat_id(chat_id)
    except Exception:
        pass


def _cancel_markup():
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    markup.add(C.inline("❌ لغو عملیات و بازگشت به پنل", callback_data="ux:cancel", style_name="danger"))
    return markup


def _send_wizard(chat, title, body, handler, *args):
    _clear_step(chat)
    text = (
        f"🧭 <b>{escape(title)}</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"{body}\n\n"
        "💡 <b>نکته:</b> فقط همان مقداری را که در مثال گفته شده ارسال کنید.\n"
        "اگر منصرف شدید، دکمه «لغو عملیات» را بزنید."
    )
    msg = C.BOT.send_message(chat, text, parse_mode="HTML", reply_markup=_cancel_markup())
    C.BOT.register_next_step_handler(msg, handler, *args)


def _plans_brief(limit=20):
    c = C.db()
    rows = c.execute(
        "SELECT id,name,price,volume_gb,days,ip_limit,active FROM plans ORDER BY sort_order,id LIMIT ?",
        (int(limit),),
    ).fetchall()
    c.close()
    if not rows:
        return "هنوز پلانی ساخته نشده است."
    lines = []
    for row in rows:
        vol = "نامحدود" if float(row["volume_gb"] or 0) <= 0 else f"{float(row['volume_gb']):g}GB"
        lines.append(
            f"• <code>#{row['id']}</code> {'🟢' if row['active'] else '🔴'} "
            f"{escape(str(row['name']))} — <b>{int(row['price']):,}</b> تومان — "
            f"{vol} / {int(row['days'])} روز / IP {int(row['ip_limit'])}"
        )
    return "\n".join(lines)


def _categories_brief(limit=20):
    c = C.db()
    rows = c.execute(
        "SELECT id,name,active FROM plan_categories ORDER BY sort_order,id LIMIT ?",
        (int(limit),),
    ).fetchall()
    c.close()
    if not rows:
        return "دسته‌بندی‌ای وجود ندارد."
    return "\n".join(
        f"• <code>#{r['id']}</code> {'🟢' if r['active'] else '🔴'} {escape(str(r['name']))}"
        for r in rows
    )


def _legacy_spec(call):
    action = (call.data or "").split(":")[1]
    core = C.CORE

    if action == "plan_add":
        return (
            "افزودن پلان جدید",
            "یک خط با <b>۵ بخش</b> بفرستید:\n\n"
            "1️⃣ <b>نام پلان</b> — چیزی که مشتری می‌بیند\n"
            "2️⃣ <b>قیمت</b> — به تومان\n"
            "3️⃣ <b>حجم</b> — به GB؛ عدد <code>0</code> یعنی نامحدود\n"
            "4️⃣ <b>مدت</b> — تعداد روز\n"
            "5️⃣ <b>IP Limit</b> — تعداد دستگاه/IP؛ <code>0</code> یعنی بدون محدودیت\n\n"
            "<b>مثال آماده:</b>\n"
            "<code>نامحدود یک‌ماهه ۲ کاربر | 350000 | 0 | 30 | 2</code>",
            core.process_admin_plan_add,
            (),
        )

    if action == "plan_edit":
        return (
            "ویرایش کامل یک پلان",
            "ابتدا ID پلان را از لیست زیر پیدا کنید:\n"
            f"{_plans_brief()}\n\n"
            "سپس یک خط با <b>۶ بخش</b> بفرستید:\n"
            "1️⃣ ID پلان\n2️⃣ نام جدید\n3️⃣ قیمت جدید (تومان)\n"
            "4️⃣ حجم GB — <code>0</code> یعنی نامحدود\n5️⃣ تعداد روز\n6️⃣ IP Limit\n\n"
            "<b>مثال:</b>\n"
            "<code>2 | نامحدود یک‌ماهه ۲ کاربر | 350000 | 0 | 30 | 2</code>\n\n"
            "⚠️ این بخش همه مشخصات پلان را با مقادیر جدید ذخیره می‌کند؛ پس هیچ فیلدی را حذف نکنید.",
            core.process_admin_plan_edit,
            (),
        )

    if action == "plan_toggle":
        return (
            "فعال / غیرفعال کردن پلان",
            "ID پلان موردنظر را بفرستید.\n\n"
            f"{_plans_brief()}\n\n"
            "<b>مثال:</b> اگر می‌خواهید پلان #2 تغییر وضعیت دهد فقط بفرستید:\n<code>2</code>\n\n"
            "غیرفعال کردن پلان آن را از فروشگاه مخفی می‌کند ولی سوابق خرید را حذف نمی‌کند.",
            core.process_admin_plan_toggle,
            (),
        )

    if action == "volume_add":
        return (
            "افزودن بسته حجم اضافه",
            "یک خط با <b>۳ بخش</b> بفرستید:\n"
            "1️⃣ نام بسته\n2️⃣ حجم به GB\n3️⃣ قیمت به تومان\n\n"
            "<b>مثال:</b>\n<code>20 گیگ اضافه | 20 | 90000</code>",
            core.process_admin_volume_add,
            (),
        )

    if action == "volume_toggle":
        return (
            "فعال / غیرفعال کردن بسته حجم",
            "فقط ID عددی بسته حجم را بفرستید. در پنل پلان‌ها بسته‌ها با پیشوند <b>V#</b> دیده می‌شوند.\n\n"
            "<b>مثال:</b> برای <code>V#3</code> فقط بفرستید:\n<code>3</code>",
            core.process_admin_volume_toggle,
            (),
        )

    if action == "followup_delay":
        return (
            "زمان پیگیری بعد از تست",
            "تعداد ساعت بعد از پایان تست را وارد کنید. مقدار مجاز <b>۱ تا ۱۶۸ ساعت</b> است.\n\n"
            "<b>مثال:</b> برای ارسال پیام ۶ ساعت بعد:\n<code>6</code>",
            core.process_followup_delay,
            (),
        )

    if action == "cashback_percent":
        return (
            "تغییر درصد کش‌بک",
            "درصد کش‌بک خرید نقدی را وارد کنید. مقدار باید بین <b>0 تا 100</b> باشد.\n\n"
            "• <code>0</code> = کش‌بک خاموش\n• <code>5</code> = پنج درصد\n• <code>7.5</code> = هفت و نیم درصد",
            core.process_admin_cashback_percent,
            (),
        )

    if action == "discount_add":
        return (
            "ساخت کد تخفیف",
            "یک خط با <b>۶ بخش</b> بفرستید:\n"
            "1️⃣ کد — فقط انگلیسی/عدد/_/-\n"
            "2️⃣ نوع — <code>percent</code> درصدی یا <code>fixed</code> مبلغ ثابت\n"
            "3️⃣ مقدار تخفیف\n4️⃣ حداقل مبلغ خرید\n5️⃣ حداکثر تعداد استفاده\n6️⃣ تعداد روز اعتبار؛ <code>0</code> بدون انقضا\n\n"
            "<b>مثال ۲۰٪:</b>\n<code>WELCOME20 | percent | 20 | 200000 | 100 | 30</code>\n\n"
            "<b>مثال ۵۰ هزار تومان:</b>\n<code>OFF50 | fixed | 50000 | 300000 | 50 | 14</code>",
            core.process_admin_discount_add,
            (),
        )

    if action == "gift_add":
        return (
            "ساخت کد هدیه کیف پول",
            "یک خط با <b>۴ بخش</b> بفرستید:\n"
            "1️⃣ کد هدیه\n2️⃣ مبلغی که به کیف پول اضافه می‌شود\n"
            "3️⃣ حداکثر تعداد استفاده\n4️⃣ روز اعتبار؛ <code>0</code> بدون انقضا\n\n"
            "<b>مثال:</b>\n<code>GIFT50 | 50000 | 20 | 30</code>",
            core.process_admin_gift_add,
            (),
        )

    if action == "discount_toggle":
        return (
            "فعال / غیرفعال کردن کد تخفیف",
            "فقط خود کد تخفیف را بفرستید.\n\n<b>مثال:</b>\n<code>WELCOME20</code>",
            core.process_admin_discount_toggle,
            (),
        )

    if action == "gift_toggle":
        return (
            "فعال / غیرفعال کردن کد هدیه",
            "فقط خود کد هدیه را بفرستید.\n\n<b>مثال:</b>\n<code>GIFT50</code>",
            core.process_admin_gift_toggle,
            (),
        )

    if action == "channel_set":
        return (
            "تنظیم کانال عضویت اجباری",
            "برای کانال عمومی فقط Username را بفرستید:\n<code>@SpeedPing</code>\n\n"
            "برای کانال خصوصی، Chat ID و لینک دعوت را با <code>|</code> جدا کنید:\n"
            "<code>-1001234567890 | https://t.me/+InviteLink</code>\n\n"
            "ربات باید بتواند وضعیت عضویت کاربر را در آن کانال بررسی کند.",
            core.process_admin_channel_set,
            (),
        )

    if action in ("admin_add", "admin_remove"):
        if int(call.from_user.id) != int(core.ADMIN_ID):
            return ("__DENY__", "", None, ())
        return (
            "افزودن مدیر" if action == "admin_add" else "حذف مدیر",
            "فقط <b>Telegram ID عددی</b> مدیر را بفرستید.\n\n"
            "<b>مثال:</b>\n<code>123456789</code>\n\n"
            + ("مدیر جدید به پنل /sudoadmin دسترسی خواهد داشت." if action == "admin_add" else "Owner اصلی قابل حذف نیست."),
            core.process_admin_add if action == "admin_add" else core.process_admin_remove,
            (),
        )

    if action in ("welcome_edit", "faq_edit"):
        key = "welcome_text" if action == "welcome_edit" else "faq_text"
        title = "ویرایش متن خوش‌آمدگویی" if action == "welcome_edit" else "ویرایش متن راهنما و FAQ"
        return (
            title,
            "متن جدید را کامل در <b>یک پیام</b> ارسال کنید. متن قبلی به‌طور کامل جایگزین می‌شود.\n\n"
            "می‌توانید از Markdown ساده مثل <code>**پررنگ**</code> و خط جدید استفاده کنید.\n"
            "قبل از ارسال، متن نهایی را کامل آماده کنید.",
            core.process_admin_content,
            (key,),
        )

    if action == "affiliate_percent":
        return (
            "تغییر درصد همکاری در فروش",
            "درصد پورسانت معرف را بین <b>0 تا 100</b> بفرستید.\n\n"
            "<b>مثال:</b> <code>10</code> یعنی ۱۰٪ از مبلغ نقدی خرید موفق.",
            core.process_affiliate_percent,
            (),
        )

    if action == "affiliate_wallet":
        return (
            "شارژ یا کسر کیف پول کاربر",
            "در یک خط <b>Telegram ID</b> و <b>مبلغ</b> را با فاصله بفرستید.\n\n"
            "➕ شارژ ۵۰ هزار تومان:\n<code>123456789 50000</code>\n\n"
            "➖ کسر ۲۰ هزار تومان:\n<code>123456789 -20000</code>\n\n"
            "مبلغ به تومان است.",
            core.process_admin_wallet_adjustment,
            (),
        )

    if action == "broadcast":
        return (
            "ارسال پیام همگانی",
            "پیامی که در مرحله بعد می‌فرستید برای <b>همه کاربران فعال</b> کپی می‌شود.\n\n"
            "متن، عکس، ویدئو یا فایل قابل ارسال است.\n"
            "⚠️ قبل از ارسال، محتوا را دقیق بررسی کنید؛ این عملیات برای کاربران واقعی اجرا می‌شود.",
            core.process_admin_broadcast,
            (),
        )

    if action in ("edit_card", "edit_holder", "edit_bank"):
        labels = {
            "edit_card": ("تغییر شماره کارت", "شماره کارت جدید را بفرستید. مثال: <code>6219-xxxx-xxxx-xxxx</code>"),
            "edit_holder": ("تغییر نام صاحب حساب", "نامی که باید در صفحه پرداخت به مشتری نمایش داده شود را بفرستید."),
            "edit_bank": ("تغییر نام بانک", "نام بانک را همان‌طور که باید به مشتری نمایش داده شود بفرستید. مثال: <code>بلو بانک</code>"),
        }
        title, body = labels[action]
        return (title, body, core.process_edit_bank, (action,))

    if action == "delete_user":
        return (
            "غیرفعال کردن کاربر ربات",
            "Telegram ID عددی کاربر را بفرستید.\n\n<b>مثال:</b> <code>123456789</code>\n\n"
            "⚠️ این عملیات کاربر را از Broadcastهای فعال خارج می‌کند، اما سوابق مالی، تست، معرف و کیف پول برای امنیت حذف نمی‌شوند.",
            core.process_delete_bot_user,
            (),
        )

    if action == "delete_sub":
        return (
            "حذف Client از 3x-ui",
            "نام/Email دقیق Client در پنل 3x-ui را بفرستید.\n\n<b>مثال:</b> <code>speedping_123456789_42</code>\n\n"
            "⚠️ این عملیات Client را از پنل حذف می‌کند؛ قبل از ارسال نام را دوباره بررسی کنید.",
            core.process_delete_panel_sub,
            (),
        )

    parts = (call.data or "").split(":")
    if action == "guideadd" and len(parts) >= 4:
        platform, media_type = parts[2], parts[3]
        platform_name = core.GUIDE_PLATFORMS.get(platform, platform)
        if media_type == "TEXT":
            body = f"متن آموزشی جدید برای <b>{escape(platform_name)}</b> را در یک پیام ارسال کنید."
        elif media_type == "PHOTO":
            body = f"یک <b>عکس</b> برای راهنمای {escape(platform_name)} بفرستید. Caption اختیاری است."
        else:
            body = f"یک <b>ویدئو</b> برای راهنمای {escape(platform_name)} بفرستید. Caption اختیاری است."
        return ("افزودن آیتم راهنما", body, core.process_admin_guide_item, (platform, media_type))

    if action == "guidedeleteask" and len(parts) >= 3:
        platform = parts[2]
        return (
            "حذف آیتم راهنما",
            "ID آیتم راهنما را بفرستید. ID کنار هر آیتم به شکل <code>#12</code> نمایش داده می‌شود.\n\n"
            "<b>مثال:</b> برای حذف #12 فقط بفرستید: <code>12</code>",
            core.process_admin_guide_delete,
            (platform,),
        )

    if action == "guideorderask" and len(parts) >= 3:
        platform = parts[2]
        return (
            "تغییر ترتیب آیتم راهنما",
            "ID آیتم و عدد ترتیب جدید را با <code>|</code> جدا کنید. عدد کمتر زودتر نمایش داده می‌شود.\n\n"
            "<b>مثال:</b>\n<code>12 | 10</code>",
            core.process_admin_guide_order,
            (platform,),
        )

    return None


def _plus_spec(call):
    from . import admin_handlers as A

    parts = (call.data or "").split(":")
    action = parts[1]
    actor = int(call.from_user.id)

    if action == "blockadd":
        return (
            "محدود کردن کاربر",
            "Telegram ID و دلیل را با <code>|</code> جدا کنید.\n\n"
            "<b>مثال:</b>\n<code>123456789 | سوءاستفاده از تست رایگان</code>\n\n"
            "کاربر محدودشده امکان خرید/تست ندارد ولی همچنان می‌تواند با پشتیبانی ارتباط داشته باشد.",
            A._block_add,
            (actor,),
        )
    if action == "blockremove":
        return ("رفع محدودیت کاربر", "فقط Telegram ID را بفرستید. مثال: <code>123456789</code>", A._block_remove, (actor,))
    if action == "catadd":
        return ("ساخت دسته‌بندی پلان", "نام دسته را همان‌طور که مشتری باید ببیند بفرستید. مثال: <code>🎮 Gaming</code>", A._cat_add, (actor,))
    if action == "catrename":
        return (
            "تغییر نام دسته‌بندی",
            f"دسته‌های فعلی:\n{_categories_brief()}\n\nفرمت: <code>CategoryID | نام جدید</code>\nمثال: <code>2 | 🎮 Gaming VIP</code>",
            A._cat_rename,
            (actor,),
        )
    if action == "catassign":
        return (
            "انتقال پلان به دسته‌بندی",
            f"<b>پلان‌ها:</b>\n{_plans_brief()}\n\n<b>دسته‌ها:</b>\n{_categories_brief()}\n\n"
            "فرمت: <code>PlanID | CategoryID</code>\nمثال: <code>3 | 2</code>",
            A._cat_assign,
            (actor,),
        )
    if action == "cattoggle":
        return ("فعال / غیرفعال کردن دسته", f"{_categories_brief()}\n\nفقط ID دسته را بفرستید. مثال: <code>2</code>", A._cat_toggle, (actor,))
    if action == "trialset":
        return (
            "تنظیم تست اختصاصی یک کاربر",
            "این تنظیم فقط برای یک Telegram ID اعمال می‌شود و از تنظیم عمومی Trial مهم‌تر است.\n\n"
            "فرمت: <code>TelegramID | حجمGB | روز | IP | یادداشت اختیاری</code>\n\n"
            "<b>مثال:</b>\n<code>123456789 | 5 | 3 | 2 | مشتری VIP</code>",
            A._trial_set,
            (actor,),
        )
    if action == "trialdel":
        return ("حذف تنظیم تست اختصاصی", "Telegram ID کاربر را بفرستید. بعد از حذف، تنظیم عمومی Trial استفاده می‌شود.\nمثال: <code>123456789</code>", A._trial_del, (actor,))
    if action == "bcaud" and len(parts) >= 3:
        audience = parts[2]
        from . import storage
        count = len(storage.audiences(audience))
        return (
            "ارسال پیام هدفمند",
            f"این پیام برای <b>{count:,}</b> کاربر در سگمنت انتخاب‌شده ارسال می‌شود.\n\n"
            "پیام بعدی شما عیناً با Copy Message ارسال می‌شود؛ متن، عکس، ویدئو یا فایل مجاز است.\n"
            "⚠️ قبل از ارسال، متن و رسانه را کامل بررسی کنید.",
            A._broadcast_message,
            (actor, audience),
        )
    if action == "auditchat":
        return (
            "تنظیم مقصد Audit Log",
            "Chat ID عددی کانال یا گروه لاگ را بفرستید. ربات باید اجازه ارسال پیام داشته باشد.\n\n"
            "<b>مثال:</b> <code>-1001234567890</code>\nبرای غیرفعال کردن ارسال تلگرامی: <code>0</code>",
            A._audit_chat,
            (actor,),
        )
    if action == "emojiset" and len(parts) >= 3:
        key = parts[2]
        label = C.EMOJI_KEYS.get(key, key)
        return (
            f"Custom Emoji برای {label}",
            "یک <b>Custom Emoji واقعی تلگرام</b> را در پیام بعدی ارسال کنید.\n"
            "اگر فقط Emoji معمولی بفرستید ID قابل استخراج نیست.\n"
            "برای پاک کردن تنظیم فعلی فقط <code>0</code> بفرستید.",
            A._emoji_set,
            (key, actor),
        )
    return None


def _fix_spec(call):
    from . import admin_tools as T
    from . import trial

    action = (call.data or "").split(":")[1]
    actor = int(call.from_user.id)
    if action == "trial_defaults":
        gb, days, ip = trial.default_values()
        return (
            "تنظیم عمومی تست رایگان",
            f"تنظیم فعلی: <b>{gb:g} GB / {days} روز / IP {ip}</b>\n\n"
            "فرمت: <code>حجمGB | تعداد روز | IP Limit</code>\n"
            "• حجم می‌تواند اعشاری باشد؛ مثلاً <code>0.5</code>\n"
            "• IP برابر <code>0</code> یعنی بدون محدودیت IP\n\n"
            "<b>مثال:</b>\n<code>2 | 2 | 1</code>",
            T._trial_defaults_save,
            (actor,),
        )
    if action == "plan_delete":
        return (
            "حذف امن پلان",
            f"{_plans_brief()}\n\nفقط ID پلان را بفرستید. مثال: <code>3</code>\n\n"
            "⚠️ پلان دارای سابقه تراکنش حذف فیزیکی نمی‌شود تا تاریخچه مالی خراب نشود؛ چنین پلانی را غیرفعال کنید.",
            T._plan_delete,
            (actor,),
        )
    if action == "category_delete":
        return (
            "حذف امن دسته‌بندی",
            f"{_categories_brief()}\n\nفقط ID دسته را بفرستید. مثال: <code>3</code>\n\n"
            "پلان‌های آن دسته حذف نمی‌شوند و قبل از حذف به یک دسته دیگر منتقل می‌شوند.",
            T._category_delete,
            (actor,),
        )
    return None


def _wizard_spec(call):
    data = call.data or ""
    if data.startswith("admin:"):
        return _legacy_spec(call)
    if data.startswith("plus:"):
        return _plus_spec(call)
    if data.startswith("fix:"):
        return _fix_spec(call)
    return None


def _is_wizard(call):
    if not C.is_admin(call.from_user.id):
        return False
    data = call.data or ""
    parts = data.split(":")
    if len(parts) < 2:
        return data == "ux:cancel"
    if data == "ux:cancel":
        return True
    action = parts[1]
    return (
        (data.startswith("admin:") and action in LEGACY_WIZARDS)
        or (data.startswith("plus:") and action in PLUS_WIZARDS)
        or (data.startswith("fix:") and action in FIX_WIZARDS)
    )


def wizard_callback(call):
    if (call.data or "") == "ux:cancel":
        _clear_step(call.message.chat.id)
        C.BOT.answer_callback_query(call.id, "عملیات لغو شد ✅")
        C.BOT.send_message(call.message.chat.id, ui.admin_home(), parse_mode="HTML", reply_markup=ui.admin_menu())
        return

    spec = _wizard_spec(call)
    if not spec:
        return ContinueHandling()
    title, body, handler, args = spec
    if title == "__DENY__":
        C.BOT.answer_callback_query(call.id, "فقط Owner اصلی اجازه این عملیات را دارد.", show_alert=True)
        return
    C.BOT.answer_callback_query(call.id)
    _send_wizard(call.message.chat.id, title, body, handler, *args)


def _is_admin_navigation(call):
    if not C.is_admin(call.from_user.id):
        return False
    return (call.data or "").startswith(("admin:", "plus:", "fix:", "ux:"))


def state_guard(call):
    """Cancel stale input state whenever the admin starts another inline action."""
    _clear_step(call.message.chat.id)
    data = call.data or ""
    if data.startswith("admin:"):
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else ""
        if action in LEGACY_MENU_NEEDS_ACK:
            try:
                C.BOT.answer_callback_query(call.id)
            except Exception:
                pass
    return ContinueHandling()


def register():
    # Wizard must run after the state guard, while both must be before the old
    # handlers. Register wizard first, then promote guard so guard becomes #1.
    C.BOT.callback_query_handler(func=_is_wizard)(wizard_callback)
    C.promote_callback()
    C.BOT.callback_query_handler(func=_is_admin_navigation)(state_guard)
    C.promote_callback()
