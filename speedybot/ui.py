from . import context as C
from .storage import backfill_categories


def main_menu():
    t = C.CORE.types
    m = t.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(C.reply("🛍 مشاهده و خرید پلان‌ها", "buy"), C.reply("👤 حساب کاربری", "account"))
    if C.CORE.trial_enabled():
        m.row(C.reply("🎁 دریافت تست رایگان", "trial"), t.KeyboardButton("🤝 همکاری در فروش"))
    else:
        m.row(t.KeyboardButton("🤝 همکاری در فروش"))
    m.row(C.reply("📲 راهنمای اتصال", "guide"), t.KeyboardButton("📚 راهنما و سوالات"))
    if C.setting("feedback_enabled", "1") == "1":
        m.row(t.KeyboardButton("🎟 کد هدیه / تخفیف"), t.KeyboardButton("⭐ نظر و امتیاز"))
        m.row(C.reply("📞 پشتیبانی", "support"))
    else:
        m.row(t.KeyboardButton("🎟 کد هدیه / تخفیف"), C.reply("📞 پشتیبانی", "support"))
    return m


def admin_menu():
    t = C.CORE.types
    m = t.InlineKeyboardMarkup(row_width=2)
    rows = [
        (
            C.inline("📊 گزارش فروش", callback_data="admin:stats", style_name="primary"),
            C.inline("📦 پلان‌ها", callback_data="admin:plans", style_name="primary"),
        ),
        (
            C.inline("🗂 دسته‌بندی پلان‌ها", callback_data="plus:categories", style_name="primary"),
            C.inline("🗑 حذف پلان/دسته", callback_data="fix:delete", style_name="danger"),
        ),
        (
            C.inline("🧪 تست و Inboundها", callback_data="fix:inbounds", style_name="primary"),
            C.inline("🎯 تست اختصاصی", callback_data="plus:trialoverrides", style_name="primary"),
        ),
        (
            C.inline("👥 Groups", callback_data="admin:groups"),
            C.inline("📈 CRM", callback_data="admin:crm", style_name="primary"),
        ),
        (
            C.inline("⭐ بازخورد مشتری", callback_data="plus:feedback", style_name="primary"),
            C.inline("📣 پیام هدفمند", callback_data="plus:broadcast", style_name="primary"),
        ),
        (
            C.inline("🎟 کد و پاداش", callback_data="admin:rewards"),
            C.inline("🤝 همکاری در فروش", callback_data="admin:affiliate"),
        ),
        (
            C.inline("📲 راهنمای اتصال", callback_data="admin:guides"),
            C.inline("🟢 وضعیت فروش", callback_data="plus:mode", style_name="success"),
        ),
        (
            C.inline("🚫 لیست سیاه", callback_data="plus:blacklist", style_name="danger"),
            C.inline("🔐 احراز و عضویت", callback_data="admin:security"),
        ),
        (
            C.inline("👑 مدیران", callback_data="admin:admins"),
            C.inline("🔔 اعلان سرویس", callback_data="admin:notifications"),
        ),
        (
            C.inline("🖥 وضعیت سرور", callback_data="admin:server_status"),
            C.inline("💾 بکاپ", callback_data="admin:ops"),
        ),
        (
            C.inline("🛟 Snapshot پنل", callback_data="plus:snapshot", style_name="danger"),
            C.inline("🧾 Audit Log", callback_data="plus:audit"),
        ),
        (
            C.inline("🎨 ظاهر و دکمه‌ها", callback_data="plus:ui", style_name="primary", emoji_key="admin"),
            C.inline("💳 حساب واریز", callback_data="admin:bank_config"),
        ),
        (
            C.inline("📝 متن‌ها و FAQ", callback_data="admin:content"),
            C.inline("👤 غیرفعال‌کردن کاربر", callback_data="admin:delete_user", style_name="danger"),
        ),
        (
            C.inline("🔌 حذف از پنل", callback_data="admin:delete_sub", style_name="danger"),
            C.inline("↩️ بروزرسانی منو", callback_data="plus:home"),
        ),
    ]
    for a, b in rows:
        m.row(a, b)
    return m


def admin_home():
    c = C.db()
    users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM transactions WHERE status IN ('PENDING','ISSUE')").fetchone()[0]
    blocks = c.execute("SELECT COUNT(*) FROM user_blocks WHERE active=1").fetchone()[0]
    fb = c.execute("SELECT COUNT(*),COALESCE(AVG(rating),0) FROM customer_feedback").fetchone()
    c.close()
    mt = {"NORMAL": "🟢 عادی", "SALES_PAUSED": "🟠 فروش متوقف", "MAINTENANCE": "🔴 تعمیرات"}[C.mode()]
    return "\n".join(
        [
            "🛠 <b>SpeedyBot Control Center</b>",
            "━━━━━━━━━━━━━━━━",
            f"⚙️ حالت سیستم: <b>{mt}</b>",
            f"🎁 تست رایگان: <b>{'🟢 فعال' if C.CORE.trial_enabled() else '🔴 غیرفعال'}</b>",
            f"👥 کاربران: <b>{int(users):,}</b>",
            f"⏳ نیازمند بررسی: <b>{int(pending)}</b>",
            f"🚫 مسدود: <b>{int(blocks)}</b>",
            f"⭐ رضایت: <b>{float(fb[1]):.1f}/5 ({int(fb[0])})</b>",
            "━━━━━━━━━━━━━━━━",
            "یکی از بخش‌های زیر را انتخاب کنید.",
        ]
    )


def categories_markup():
    backfill_categories()
    c = C.db()
    rows = c.execute(
        "SELECT c.*,COUNT(p.id) n FROM plan_categories c "
        "LEFT JOIN plans p ON p.category_id=c.id AND p.active=1 "
        "WHERE c.active=1 GROUP BY c.id HAVING n>0 ORDER BY c.sort_order,c.id"
    ).fetchall()
    c.close()
    m = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        m.add(
            C.inline(
                f"🗂 {r['name']}  •  {r['n']} پلان",
                callback_data=f"plus:shopcat:{r['id']}",
                style_name="primary",
            )
        )
    return m, rows


def send_category(chat_id, uid, cid):
    backfill_categories()
    c = C.db()
    cat = c.execute("SELECT name FROM plan_categories WHERE id=? AND active=1", (int(cid),)).fetchone()
    plans = c.execute(
        "SELECT * FROM plans WHERE active=1 AND category_id=? ORDER BY sort_order,id", (int(cid),)
    ).fetchall()
    bal = c.execute("SELECT COALESCE(balance,0) FROM users WHERE id=?", (int(uid),)).fetchone()
    c.close()
    if not cat or not plans:
        C.BOT.send_message(chat_id, "⛔️ در این دسته پلان فعالی نیست.", reply_markup=main_menu())
        return
    balance = int(bal[0] or 0) if bal else 0
    out = [f"🗂 <b>{cat['name']}</b>", "━━━━━━━━━━━━━━━━"]
    m = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for p in plans:
        vol = "نامحدود" if float(p["volume_gb"] or 0) <= 0 else f"{float(p['volume_gb']):g} GB"
        ip = "بدون محدودیت" if int(p["ip_limit"] or 0) <= 0 else f"{int(p['ip_limit'])} IP"
        out.append(
            f"\n📦 <b>{p['name']}</b>\n├ 💵 {int(p['price']):,} تومان\n├ 📅 {int(p['days'])} روز\n├ 📊 {vol}\n└ 👥 {ip}"
        )
        m.add(
            C.inline(
                f"🛒 خرید {p['name'][:30]} • {int(p['price']):,}",
                callback_data=f"buy:{p['id']}",
                style_name="success",
                emoji_key="buy",
            )
        )
        if balance >= int(p["price"]):
            m.add(
                C.inline(
                    f"👛 کیف پول • {p['name'][:28]}",
                    callback_data=f"walletbuy:{p['id']}",
                    style_name="primary",
                )
            )
    m.add(C.inline("↩️ دسته‌بندی‌ها", callback_data="plus:shop", style_name="primary"))
    out.append(f"\n━━━━━━━━━━━━━━━━\n👛 موجودی: <b>{balance:,} تومان</b>")
    C.BOT.send_message(chat_id, "\n".join(out), parse_mode="HTML", reply_markup=m)
