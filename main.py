import os
import telebot
from telebot import apihelper
from telebot import types
import sqlite3
import requests
import time
import re
import secrets
import threading
from urllib.parse import quote
from datetime import datetime

# --- CONFIGURATIONS (READING FROM SYSTEM ENV) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# تنظیمات اتصال به پنل سنائی
XUI_API_URL = os.getenv("XUI_API_URL")          # مثلا http://127.0.0.1:2053
XUI_BASE_PATH = os.getenv("XUI_BASE_PATH")      # مثلا /your-secret-base-path
XUI_BEARER_TOKEN = os.getenv("XUI_BEARER_TOKEN")
XUI_SUB_SERVER_URL = os.getenv("XUI_SUB_SERVER_URL") # مثلا https://sub.example.com:2096
XUI_SUB_PATH = os.getenv("XUI_SUB_PATH", "/sub/")  # مسیر Subscription در Settings → Subscription

DEVELOPMENT_MODE = False
bot = telebot.TeleBot(BOT_TOKEN)
USER_STATES = {}
_BOT_USERNAME_CACHE = None
SERVICE_MONITOR_LOCK = threading.Lock()
SERVICE_MONITOR_THREAD = None

# --- PLANS DATA ---
PLANS = {
    1: {"name": "پلان نامحدود (یک‌ماهه)", "price": 300000, "volume": 0, "days": 30},
}

# --- DATABASE SETUP / MIGRATIONS ---
def _ensure_column(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init_db():
    conn = sqlite3.connect('speedping.db', timeout=15)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        balance INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER,
        last_seen_at INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        referred_by INTEGER,
        referral_bound_at INTEGER
    )''')
    # مهاجرت امن دیتابیس نسخه‌های قبلی
    _ensure_column(cursor, 'users', 'created_at', 'INTEGER')
    _ensure_column(cursor, 'users', 'last_seen_at', 'INTEGER')
    _ensure_column(cursor, 'users', 'is_active', 'INTEGER NOT NULL DEFAULT 1')
    _ensure_column(cursor, 'users', 'referred_by', 'INTEGER')
    _ensure_column(cursor, 'users', 'referral_bound_at', 'INTEGER')

    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        photo_id TEXT,
        plan_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING',
        price INTEGER NOT NULL DEFAULT 0,
        payment_method TEXT NOT NULL DEFAULT 'CARD',
        wallet_used INTEGER NOT NULL DEFAULT 0,
        cash_amount INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER,
        approved_at INTEGER,
        service_email TEXT,
        last_error TEXT
    )''')
    for col, definition in [
        ('price', 'INTEGER NOT NULL DEFAULT 0'),
        ('payment_method', "TEXT NOT NULL DEFAULT 'CARD'"),
        ('wallet_used', 'INTEGER NOT NULL DEFAULT 0'),
        ('cash_amount', 'INTEGER NOT NULL DEFAULT 0'),
        ('created_at', 'INTEGER'),
        ('approved_at', 'INTEGER'),
        ('service_email', 'TEXT'),
        ('last_error', 'TEXT'),
    ]:
        _ensure_column(cursor, 'transactions', col, definition)

    cursor.execute('''CREATE TABLE IF NOT EXISTS trial_services (
        user_id INTEGER PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'CREATING',
        created_at INTEGER NOT NULL,
        activated_at INTEGER,
        last_error TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_messages (admin_msg_id INTEGER PRIMARY KEY, user_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_codes (
        user_id INTEGER PRIMARY KEY,
        code TEXT NOT NULL UNIQUE,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_commissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        purchase_tx_id INTEGER NOT NULL UNIQUE,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER NOT NULL,
        purchase_amount INTEGER NOT NULL,
        commission_percent REAL NOT NULL,
        commission_amount INTEGER NOT NULL,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS wallet_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        balance_after INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        related_tx_id INTEGER,
        related_user_id INTEGER,
        unique_key TEXT UNIQUE,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS service_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_email TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        service_kind TEXT NOT NULL,
        event_type TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        UNIQUE(service_email, event_type)
    )''')

    # تنظیمات اولیه
    defaults = {
        'card_number': '6219-0000-0000-0000',
        'card_holder': 'تست تست',
        'bank_name': 'بلو بانک',
        'referral_enabled': '1',
        'referral_commission_percent': '10',
        'service_notifications_enabled': '1',
        'service_notification_interval_seconds': '300',
        'service_volume_warning_percent': '90',
        'service_expiry_warning_hours': '24',
        'trial_expiry_warning_hours': '3',
    }
    for key, value in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    now_ts = int(time.time())
    cursor.execute("UPDATE users SET created_at = COALESCE(created_at, ?), last_seen_at = COALESCE(last_seen_at, ?) WHERE created_at IS NULL OR last_seen_at IS NULL", (now_ts, now_ts))
    # بک‌فیل قیمت برای تراکنش‌های نسخه قبلی (در صورت وجود)
    for plan_id, plan in PLANS.items():
        cursor.execute("UPDATE transactions SET price = ? WHERE plan_id = ? AND (price IS NULL OR price = 0)", (plan['price'], plan_id))
        cursor.execute("UPDATE transactions SET cash_amount = price WHERE plan_id = ? AND payment_method = 'CARD' AND (cash_amount IS NULL OR cash_amount = 0)", (plan_id,))
    cursor.execute("UPDATE transactions SET created_at = COALESCE(created_at, ?) WHERE created_at IS NULL", (now_ts,))

    conn.commit()
    conn.close()

init_db()

# --- DATABASE HELPERS ---
def get_db_setting(key, default_value=""):
    try:
        conn = sqlite3.connect('speedping.db')
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default_value
    except:
        return default_value

def update_db_setting(key, value):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def _db_connect():
    conn = sqlite3.connect('speedping.db', timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_balance(user_id):
    conn = _db_connect()
    row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return int(row['balance']) if row else 0


def get_referral_percent():
    try:
        value = float(get_db_setting('referral_commission_percent', '10'))
        return max(0.0, min(value, 100.0))
    except Exception:
        return 10.0


def referral_enabled():
    return get_db_setting('referral_enabled', '1') == '1'


def get_or_create_referral_code(user_id):
    conn = _db_connect()
    try:
        now_ts = int(time.time())
        conn.execute(
            "INSERT OR IGNORE INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (?, 0, ?, ?, 1)",
            (user_id, now_ts, now_ts)
        )
        conn.commit()
        row = conn.execute("SELECT code FROM referral_codes WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return row['code']
        for _ in range(20):
            code = secrets.token_urlsafe(7).replace('-', '').replace('_', '')[:10]
            if len(code) < 8:
                continue
            try:
                conn.execute(
                    "INSERT INTO referral_codes (user_id, code, created_at) VALUES (?, ?, ?)",
                    (user_id, code, int(time.time()))
                )
                conn.commit()
                return code
            except sqlite3.IntegrityError:
                conn.rollback()
                continue
        raise RuntimeError("Could not generate unique referral code")
    finally:
        conn.close()


def get_bot_username():
    global _BOT_USERNAME_CACHE
    if _BOT_USERNAME_CACHE:
        return _BOT_USERNAME_CACHE
    try:
        me = bot.get_me()
        _BOT_USERNAME_CACHE = me.username
        return _BOT_USERNAME_CACHE
    except Exception:
        return None


def build_referral_link(user_id):
    code = get_or_create_referral_code(user_id)
    username = get_bot_username()
    if not username:
        return None, code
    return f"https://t.me/{username}?start=ref_{code}", code


def bind_referrer_for_new_user(new_user_id, referral_code):
    """Bind referral only for a truly new user. Binding is permanent and single-level."""
    if not referral_enabled() or not referral_code:
        return None
    if not re.fullmatch(r"[A-Za-z0-9]{6,32}", referral_code):
        return None

    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        code_row = conn.execute(
            "SELECT user_id FROM referral_codes WHERE code = ?",
            (referral_code,)
        ).fetchone()
        if not code_row:
            conn.rollback()
            return None
        referrer_id = int(code_row['user_id'])
        if referrer_id == int(new_user_id):
            conn.rollback()
            return None
        referrer = conn.execute(
            "SELECT id, is_active FROM users WHERE id = ?",
            (referrer_id,)
        ).fetchone()
        current = conn.execute(
            "SELECT referred_by FROM users WHERE id = ?",
            (new_user_id,)
        ).fetchone()
        if not referrer or int(referrer['is_active'] or 0) != 1 or not current or current['referred_by'] is not None:
            conn.rollback()
            return None
        conn.execute(
            "UPDATE users SET referred_by = ?, referral_bound_at = ? WHERE id = ? AND referred_by IS NULL",
            (referrer_id, int(time.time()), new_user_id)
        )
        conn.commit()
        return referrer_id
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()


def wallet_adjust(user_id, amount, tx_type, description, related_tx_id=None, related_user_id=None, unique_key=None, allow_negative=False):
    """Atomic wallet ledger. amount is signed: positive credit, negative debit."""
    amount = int(amount)
    if amount == 0:
        return True, get_user_balance(user_id)

    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if unique_key:
            existing = conn.execute("SELECT balance_after FROM wallet_transactions WHERE unique_key = ?", (unique_key,)).fetchone()
            if existing:
                conn.rollback()
                return True, int(existing['balance_after'])

        row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (?, 0, ?, ?, 1)",
                (user_id, int(time.time()), int(time.time()))
            )
            current_balance = 0
        else:
            current_balance = int(row['balance'] or 0)

        new_balance = current_balance + amount
        if new_balance < 0 and not allow_negative:
            conn.rollback()
            return False, current_balance

        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.execute(
            """INSERT INTO wallet_transactions
               (user_id, amount, balance_after, type, description, related_tx_id, related_user_id, unique_key, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, amount, new_balance, tx_type, description, related_tx_id, related_user_id, unique_key, int(time.time()))
        )
        conn.commit()
        return True, new_balance
    except sqlite3.IntegrityError:
        conn.rollback()
        if unique_key:
            row = conn.execute("SELECT balance_after FROM wallet_transactions WHERE unique_key = ?", (unique_key,)).fetchone()
            if row:
                return True, int(row['balance_after'])
        raise
    finally:
        conn.close()


def credit_referral_commission(purchase_tx_id):
    """Credit one-level commission exactly once after a successful cash-backed purchase."""
    if not referral_enabled():
        return None

    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM referral_commissions WHERE purchase_tx_id = ?", (purchase_tx_id,)).fetchone():
            conn.rollback()
            return None

        tx = conn.execute(
            "SELECT user_id, status, cash_amount FROM transactions WHERE id = ?",
            (purchase_tx_id,)
        ).fetchone()
        if not tx or tx['status'] != 'APPROVED':
            conn.rollback()
            return None
        referred_id = int(tx['user_id'])
        cash_amount = int(tx['cash_amount'] or 0)
        if cash_amount <= 0:
            conn.rollback()
            return None

        user = conn.execute("SELECT referred_by FROM users WHERE id = ?", (referred_id,)).fetchone()
        if not user or user['referred_by'] is None:
            conn.rollback()
            return None
        referrer_id = int(user['referred_by'])
        if referrer_id == referred_id:
            conn.rollback()
            return None

        percent = get_referral_percent()
        commission = int(cash_amount * percent / 100.0)
        if commission <= 0:
            conn.rollback()
            return None

        ref_row = conn.execute("SELECT balance FROM users WHERE id = ?", (referrer_id,)).fetchone()
        if not ref_row:
            conn.rollback()
            return None
        new_balance = int(ref_row['balance'] or 0) + commission
        now_ts = int(time.time())
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, referrer_id))
        conn.execute(
            """INSERT INTO referral_commissions
               (purchase_tx_id, referrer_id, referred_id, purchase_amount, commission_percent, commission_amount, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (purchase_tx_id, referrer_id, referred_id, cash_amount, percent, commission, now_ts)
        )
        conn.execute(
            """INSERT INTO wallet_transactions
               (user_id, amount, balance_after, type, description, related_tx_id, related_user_id, unique_key, created_at)
               VALUES (?, ?, ?, 'REFERRAL_COMMISSION', ?, ?, ?, ?, ?)""",
            (
                referrer_id, commission, new_balance,
                f"پورسانت خرید موفق کاربر دعوت‌شده #{referred_id}",
                purchase_tx_id, referred_id, f"referral_reward:{purchase_tx_id}", now_ts
            )
        )
        conn.commit()
        return {
            'referrer_id': referrer_id,
            'referred_id': referred_id,
            'amount': commission,
            'balance': new_balance,
            'percent': percent,
        }
    except sqlite3.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_referral_stats(user_id):
    conn = _db_connect()
    try:
        invited = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referred_by = ?", (user_id,)).fetchone()['c']
        buyers = conn.execute("SELECT COUNT(DISTINCT referred_id) AS c FROM referral_commissions WHERE referrer_id = ?", (user_id,)).fetchone()['c']
        total_commission = conn.execute("SELECT COALESCE(SUM(commission_amount), 0) AS s FROM referral_commissions WHERE referrer_id = ?", (user_id,)).fetchone()['s']
        balance = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
        return int(invited or 0), int(buyers or 0), int(total_commission or 0), int(balance['balance'] if balance else 0)
    finally:
        conn.close()


# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛍 مشاهده و خرید پلان‌ها", "👤 حساب کاربری")
    markup.row("🤝 همکاری در فروش", "🎁 دریافت تست رایگان")
    markup.row("📞 پشتیبانی")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔙 بازگشت به منوی اصلی")
    return markup

def admin_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار ربات و فروش", callback_data="admin:stats"),
        types.InlineKeyboardButton("🤝 همکاری در فروش", callback_data="admin:affiliate"),
        types.InlineKeyboardButton("🖥 وضعیت زنده سرور", callback_data="admin:server_status"),
        types.InlineKeyboardButton("🔔 اعلان سرویس‌ها", callback_data="admin:notifications"),
        types.InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin:broadcast"),
        types.InlineKeyboardButton("💳 تنظیمات حساب واریز", callback_data="admin:bank_config"),
        types.InlineKeyboardButton("👤 غیرفعال کردن کاربر", callback_data="admin:delete_user"),
        types.InlineKeyboardButton("🔌 حذف اشتراک از پنل", callback_data="admin:delete_sub")
    )
    return markup

# --- USER HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    USER_STATES[message.chat.id] = None
    user_id = message.from_user.id
    now_ts = int(time.time())

    # فقط کاربری که برای اولین بار وارد ربات می‌شود امکان اتصال به معرف را دارد.
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        is_new_user = existing is None
        if is_new_user:
            conn.execute(
                "INSERT INTO users (id, balance, created_at, last_seen_at, is_active) VALUES (?, 0, ?, ?, 1)",
                (user_id, now_ts, now_ts)
            )
        else:
            conn.execute("UPDATE users SET is_active = 1, last_seen_at = ? WHERE id = ?", (now_ts, user_id))
        conn.commit()
    finally:
        conn.close()

    referral_code = None
    parts = (message.text or '').strip().split(maxsplit=1)
    if len(parts) == 2 and parts[1].startswith('ref_'):
        referral_code = parts[1][4:]

    bound_referrer = None
    if is_new_user and referral_code:
        bound_referrer = bind_referrer_for_new_user(user_id, referral_code)

    welcome_text = "سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید."
    if bound_referrer:
        welcome_text += "\n\n🤝 لینک دعوت شما با موفقیت ثبت شد. اگر خرید موفق انجام دهید، پورسانت به کیف پول معرف شما اضافه می‌شود."
        try:
            bot.send_message(bound_referrer, "🎯 یک کاربر جدید با لینک دعوت شما وارد SpeedPing شد.\nپورسانت بعد از خرید موفق او به کیف پول شما اضافه می‌شود.")
        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def go_to_main_menu(message):
    USER_STATES[message.chat.id] = None
    bot.send_message(message.chat.id, "شما به منوی اصلی بازگشتید.", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "🛍 مشاهده و خرید پلان‌ها")
def show_plans(message):
    USER_STATES[message.chat.id] = None
    user_id = message.from_user.id
    balance = get_user_balance(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for plan_id, info in PLANS.items():
        markup.add(types.InlineKeyboardButton(
            text=f"💳 {info['name']} - {info['price']:,} تومان",
            callback_data=f"buy:{plan_id}"
        ))
        if balance >= info['price']:
            markup.add(types.InlineKeyboardButton(
                text=f"👛 پرداخت {info['price']:,} تومان از کیف پول",
                callback_data=f"walletbuy:{plan_id}"
            ))
    bot.send_message(
        message.chat.id,
        f"🛒 **لیست پلان‌های SpeedPing**\n\n👛 موجودی کیف پول شما: `{balance:,} تومان`\n\nپرداخت بانکی همیشه فعال است؛ اگر موجودی کیف پول به مبلغ پلن برسد، گزینه پرداخت مستقیم از کیف پول هم نمایش داده می‌شود.",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda message: message.text == "🤝 همکاری در فروش")
def show_affiliate_panel(message):
    USER_STATES[message.chat.id] = None
    user_id = message.from_user.id
    if not referral_enabled():
        bot.send_message(user_id, "⛔️ سیستم همکاری در فروش در حال حاضر غیرفعال است.", reply_markup=main_menu())
        return

    invited, buyers, earned, balance = get_referral_stats(user_id)
    link, code = build_referral_link(user_id)
    percent = get_referral_percent()

    text = (
        "🤝 **همکاری در فروش SpeedPing**\n\n"
        f"👛 موجودی کیف پول: **{balance:,} تومان**\n"
        f"👥 تعداد دعوت‌شده‌ها: **{invited} نفر**\n"
        f"✅ خریداران موفق: **{buyers} نفر**\n"
        f"💰 کل پورسانت دریافتی: **{earned:,} تومان**\n"
        f"📈 نرخ پورسانت فعلی: **{percent:g}٪ از مبلغ پرداخت نقدی هر خرید موفق**\n\n"
        "**قوانین:**\n"
        "• فقط کاربر جدیدی که اولین ورودش با لینک شما باشد به شما متصل می‌شود.\n"
        "• معرف بعد از ثبت قابل تغییر نیست و خودمعرفی پذیرفته نمی‌شود.\n"
        "• دریافت تست رایگان پورسانت ندارد.\n"
        "• پورسانت پس از تایید پرداخت و صدور موفق سرویس و فقط یک‌بار برای هر خرید واریز می‌شود.\n"
        "• خریدی که کاملاً با کیف پول انجام شود پورسانت جدید ایجاد نمی‌کند.\n"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    if link:
        text += f"\n🔗 **لینک اختصاصی دعوت شما:**\n`{link}`"
        share_url = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote('با لینک من وارد SpeedPing شو و سرویس‌ها را ببین ⚡️', safe='')}"
        markup.add(types.InlineKeyboardButton("📤 ارسال لینک دعوت", url=share_url))
    else:
        text += f"\n🔑 کد دعوت شما: `{code}`\n⚠️ در حال حاضر دریافت username ربات از تلگرام ممکن نشد؛ کمی بعد دوباره این بخش را باز کنید."
    markup.add(types.InlineKeyboardButton("📜 تاریخچه کیف پول", callback_data="ref:wallet_history"))
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)


@bot.callback_query_handler(func=lambda call: call.data == 'ref:wallet_history')
def show_wallet_history(call):
    user_id = call.from_user.id
    conn = _db_connect()
    rows = conn.execute(
        "SELECT amount, balance_after, type, description, created_at FROM wallet_transactions WHERE user_id = ? ORDER BY id DESC LIMIT 15",
        (user_id,)
    ).fetchall()
    conn.close()
    bot.answer_callback_query(call.id)
    if not rows:
        bot.send_message(user_id, "📜 هنوز تراکنشی در کیف پول شما ثبت نشده است.")
        return
    lines = ["📜 **۱۵ تراکنش آخر کیف پول**\n"]
    for row in rows:
        sign = "+" if int(row['amount']) > 0 else ""
        dt = datetime.fromtimestamp(int(row['created_at'])).strftime('%Y-%m-%d %H:%M')
        lines.append(f"• `{sign}{int(row['amount']):,}` تومان | موجودی: `{int(row['balance_after']):,}`\n  {row['description'] or row['type']} | {dt}")
    bot.send_message(user_id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == "🎁 دریافت تست رایگان")
def request_free_trial(message):
    USER_STATES[message.chat.id] = None
    user_id = message.from_user.id
    trial_email = f"speedping_trial_{user_id}"

    # رزرو اتمیک تست: با چند بار کلیک هم فقط یک درخواست برای هر کاربر ساخته می‌شود.
    conn = sqlite3.connect('speedping.db', timeout=15)
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "SELECT status FROM trial_services WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row and row[0] in ('CREATING', 'ACTIVE'):
            conn.rollback()
            if row[0] == 'CREATING':
                bot.send_message(
                    message.chat.id,
                    "⏳ درخواست تست شما قبلاً ثبت شده و در حال صدور است. لطفاً دوباره روی دکمه نزنید.",
                    reply_markup=main_menu()
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "🎁 شما قبلاً تست رایگان SpeedPing را دریافت کرده‌اید. هر کاربر فقط یک‌بار امکان دریافت تست دارد.",
                    reply_markup=main_menu()
                )
            return

        now_ts = int(time.time())
        if row and row[0] == 'FAILED':
            cursor.execute(
                "UPDATE trial_services SET status = 'CREATING', last_error = NULL, created_at = ? WHERE user_id = ?",
                (now_ts, user_id)
            )
        else:
            cursor.execute(
                "INSERT INTO trial_services (user_id, email, status, created_at) VALUES (?, ?, 'CREATING', ?)",
                (user_id, trial_email, now_ts)
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        bot.send_message(
            message.chat.id,
            "🎁 تست رایگان برای این حساب قبلاً ثبت شده است.",
            reply_markup=main_menu()
        )
        return
    finally:
        conn.close()

    bot.send_message(
        message.chat.id,
        "⚡️ در حال ساخت تست رایگان شما هستم...\n\n📦 حجم: ۱ گیگابایت\n⏱ اعتبار: ۱ روز",
        reply_markup=main_menu()
    )
    generate_trial_xui_config(user_id, trial_email)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy:'))
def handle_buy_plan(call):
    plan_id = int(call.data.split(':')[1])
    plan = PLANS.get(plan_id)
    if not plan:
        bot.answer_callback_query(call.id, "پلن نامعتبر است.", show_alert=True)
        return
    bot.answer_callback_query(call.id)

    card_num = get_db_setting('card_number')
    card_holder = get_db_setting('card_holder')
    bank_name = get_db_setting('bank_name')

    msg = bot.send_message(
        call.message.chat.id,
        f"💵 شما پلان را انتخاب کردید: **{plan['name']}**\n\n"
        f"💳 لطفاً مبلغ **{plan['price']:,} تومان** را به مشخصات زیر واریز کنید:\n\n"
        f"🏦 بانک: *{bank_name}*\n"
        f"💳 شماره کارت:\n`{card_num}`\n"
        f"👤 به نام: *{card_holder}*\n\n"
        f"📸 پس از واریز، **فقط اسکرین‌شات یا عکس فیش واریزی** خود را ارسال کنید.",
        parse_mode="Markdown",
        reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, process_receipt, plan_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('walletbuy:'))
def handle_wallet_buy(call):
    user_id = call.from_user.id
    plan_id = int(call.data.split(':')[1])
    plan = PLANS.get(plan_id)
    if not plan:
        bot.answer_callback_query(call.id, "پلن نامعتبر است.", show_alert=True)
        return

    price = int(plan['price'])
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
        balance = int(user['balance'] or 0) if user else 0
        if balance < price:
            conn.rollback()
            bot.answer_callback_query(call.id, f"موجودی کافی نیست. موجودی: {balance:,} تومان", show_alert=True)
            return

        now_ts = int(time.time())
        recent = conn.execute(
            "SELECT id FROM transactions WHERE user_id = ? AND plan_id = ? AND payment_method = 'WALLET' AND created_at >= ? AND status IN ('PROCESSING','APPROVED') ORDER BY id DESC LIMIT 1",
            (user_id, plan_id, now_ts - 15)
        ).fetchone()
        if recent:
            conn.rollback()
            bot.answer_callback_query(call.id, "یک خرید کیف پول برای همین پلن همین الان ثبت شده؛ چند ثانیه بعد دوباره تلاش کنید.", show_alert=True)
            return
        cursor = conn.execute(
            """INSERT INTO transactions
               (user_id, photo_id, plan_id, status, price, payment_method, wallet_used, cash_amount, created_at)
               VALUES (?, NULL, ?, 'PROCESSING', ?, 'WALLET', ?, 0, ?)""",
            (user_id, plan_id, price, price, now_ts)
        )
        tx_id = cursor.lastrowid
        service_email = f"speedping_{user_id}_{tx_id}"
        new_balance = balance - price
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))
        conn.execute("UPDATE transactions SET service_email = ? WHERE id = ?", (service_email, tx_id))
        conn.execute(
            """INSERT INTO wallet_transactions
               (user_id, amount, balance_after, type, description, related_tx_id, unique_key, created_at)
               VALUES (?, ?, ?, 'PURCHASE', ?, ?, ?, ?)""",
            (user_id, -price, new_balance, f"خرید {plan['name']} از کیف پول", tx_id, f"wallet_purchase:{tx_id}", now_ts)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        bot.answer_callback_query(call.id, "خطا در ثبت خرید کیف پول.", show_alert=True)
        try:
            bot.send_message(ADMIN_ID, f"🚨 خطای خرید کیف پول کاربر {user_id}: {str(e)[:500]}")
        except Exception:
            pass
        return
    finally:
        conn.close()

    bot.answer_callback_query(call.id, "پرداخت از کیف پول ثبت شد ✅")
    bot.send_message(
        user_id,
        f"👛 مبلغ **{price:,} تومان** از کیف پول شما کسر شد.\n⚡️ سرویس در حال صدور است...\n🆔 تراکنش: `{tx_id}`",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    finalize_service_transaction(tx_id)


def process_receipt(message, plan_id):
    if message.text == "🔙 بازگشت به منوی اصلی":
        go_to_main_menu(message)
        return

    if not message.photo:
        bot.send_message(message.chat.id, "❌ خطا! شما فیش واریزی را ارسال نکردید. لطفاً مجدداً مراحل خرید را طی کنید.", reply_markup=main_menu())
        return

    plan = PLANS.get(plan_id)
    if not plan:
        bot.send_message(message.chat.id, "❌ پلن انتخاب‌شده دیگر معتبر نیست.", reply_markup=main_menu())
        return

    photo_id = message.photo[-1].file_id
    price = int(plan['price'])
    now_ts = int(time.time())

    conn = _db_connect()
    cursor = conn.execute(
        """INSERT INTO transactions
           (user_id, photo_id, plan_id, status, price, payment_method, wallet_used, cash_amount, created_at)
           VALUES (?, ?, ?, 'PENDING', ?, 'CARD', 0, ?, ?)""",
        (message.from_user.id, photo_id, plan_id, price, price, now_ts)
    )
    tx_id = cursor.lastrowid
    service_email = f"speedping_{message.from_user.id}_{tx_id}"
    conn.execute("UPDATE transactions SET service_email = ? WHERE id = ?", (service_email, tx_id))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "✅ فیش شما دریافت شد و در حال بررسی توسط مدیریت است. به محض تایید و صدور سرویس به شما اطلاع داده می‌شود.", reply_markup=main_menu())

    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"admin:approve:{tx_id}"),
        types.InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:reject:{tx_id}")
    )

    plan_name = plan['name']
    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=(
            f"🔔 **تراکنش جدید خرید کانفیگ!**\n\n"
            f"👤 کاربر: `{message.from_user.id}`\n"
            f"📦 پلان: {plan_name}\n"
            f"💵 مبلغ: **{price:,} تومان**\n"
            f"🆔 کد تراکنش: `{tx_id}`"
        ),
        reply_markup=admin_markup,
        parse_mode="Markdown"
    )

# --- ACCOUNT SECTION ---
@bot.message_handler(func=lambda message: message.text == "👤 حساب کاربری")
def show_account(message):
    USER_STATES[message.chat.id] = None
    user_id = message.chat.id

    conn = _db_connect()
    approved_txs = conn.execute(
        "SELECT id, service_email, payment_method FROM transactions WHERE user_id = ? AND status = 'APPROVED' ORDER BY id DESC",
        (user_id,)
    ).fetchall()
    active_trial = conn.execute(
        "SELECT email FROM trial_services WHERE user_id = ? AND status = 'ACTIVE'",
        (user_id,)
    ).fetchone()
    balance_row = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    balance = int(balance_row['balance'] if balance_row else 0)

    msg_text = (
        f"👤 **حساب کاربری شما در SpeedPing**\n\n"
        f"🆔 آیدی تلگرام: `{user_id}`\n"
        f"👛 موجودی کیف پول: **{balance:,} تومان**\n"
    )

    markup = types.InlineKeyboardMarkup()
    if approved_txs or active_trial:
        msg_text += "\n👇 برای مشاهده وضعیت زنده هر سرویس روی دکمه آن بزنید:"
        if active_trial:
            markup.add(types.InlineKeyboardButton(text="🎁 تست رایگان 1GB / 1 روز", callback_data="view:trial"))
        for tx in approved_txs:
            tx_id = int(tx['id'])
            markup.add(types.InlineKeyboardButton(text=f"📦 اکانت اختصاصی (تراکنش {tx_id})", callback_data=f"view:status:{tx_id}"))
    else:
        msg_text += "\n❌ در حال حاضر سرویس فعالی ندارید."

    markup.add(types.InlineKeyboardButton("📜 تاریخچه کیف پول", callback_data="ref:wallet_history"))
    bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('view:status:'))
def handle_view_status(call):
    tx_id = int(call.data.split(':')[2])
    user_id = call.message.chat.id
    conn = _db_connect()
    row = conn.execute("SELECT service_email FROM transactions WHERE id = ? AND user_id = ? AND status = 'APPROVED'", (tx_id, user_id)).fetchone()
    conn.close()
    if not row:
        bot.answer_callback_query(call.id, "این سرویس برای حساب شما پیدا نشد.", show_alert=True)
        return
    user_email = row['service_email'] or f"speedping_{user_id}_{tx_id}"
    bot.answer_callback_query(call.id, "در حال استعلام وضعیت زنده...")
    send_xui_status(user_id, user_email)


@bot.callback_query_handler(func=lambda call: call.data == 'view:trial')
def handle_view_trial_status(call):
    user_id = call.message.chat.id
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM trial_services WHERE user_id = ? AND status = 'ACTIVE'", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        bot.answer_callback_query(call.id, "تست فعالی برای شما ثبت نشده است.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "در حال استعلام وضعیت زنده...")
    send_xui_status(user_id, row[0])


def send_xui_status(user_id, user_email):
    
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    try:
        client_url = _xui_url(f"panel/api/clients/get/{quote(str(user_email), safe='')}")
        response = requests.get(client_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        client_data = response.json().get("obj", {}) if response.status_code == 200 and response.json().get("success") else {}
        
        traffic_url = _xui_url(f"panel/api/clients/traffic/{quote(str(user_email), safe='')}")
        traffic_res = requests.get(traffic_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        traffic_data = traffic_res.json().get("obj", {}) if traffic_res.status_code == 200 and traffic_res.json().get("success") else {}
        
        data = {**client_data, **traffic_data}
        
        if data:
            enable_status = "🟢 فعال" if data.get("enable", True) else "🔴 غیرفعال"
            bytes_up = data.get("up", 0)
            bytes_down = data.get("down", 0)
            used_gb = (bytes_up + bytes_down) / (1024 * 1024 * 1024)
            
            total_bytes = data.get("total", 0) or data.get("totalGB", 0)
            total_str = "نامحدود" if total_bytes == 0 else f"{total_bytes / (1024*1024*1024):.2f} گیگابایت"
            
            expiry_time_ms = data.get("expiryTime", 0)
            current_time_ms = int(time.time() * 1000)
            
            if expiry_time_ms == 0:
                time_left_str = "بدون محدودیت زمانی"
            elif expiry_time_ms < current_time_ms:
                time_left_str = "❌ منقضی شده"
            else:
                diff_seconds = (expiry_time_ms - current_time_ms) / 1000
                days = int(diff_seconds // 86400)
                hours = int((diff_seconds % 86400) // 3600)
                time_left_str = f"⏳ {days} روز و {hours} ساعت باقی‌مانده"
                
            sub_id = data.get("subId") or data.get("uuid")
            if not sub_id:
                sub_id = "error_id"
                
            status_text = f"📊 **گزارش وضعیت زنده سرویس SpeedPing**\n\n" \
                          f"✉️ نام کاربری: `{user_email}`\n" \
                          f"⚡️ وضعیت سرویس: {enable_status}\n" \
                          f"📥 حجم مصرف شده: `{used_gb:.2f} GB`\n" \
                          f"📤 سقف حجم اکانت: `{total_str}`\n" \
                          f"📅 مهلت اعتبار: **{time_left_str}**\n"
                          
            markup = types.InlineKeyboardMarkup()
            # ⚠️ فیکس شد: استفاده از کاراکتر | برای حل تداخل دکمه با خط تیره ایمیل‌ها
            if sub_id != "error_id":
                markup.row(types.InlineKeyboardButton(text="🌐 دریافت لینک سابسکریپشن", callback_data=f"getlinks:sub:{sub_id}"))
            markup.row(types.InlineKeyboardButton(text="🔑 دریافت کانفیگ‌های مستقیم", callback_data=f"getlinks:dir:{user_email}"))
            
            bot.send_message(user_id, status_text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ مشخصات این اکانت روی پنل سرور یافت نشد.")
    except Exception as e:
        bot.send_message(user_id, f"🚨 خطا در خواندن اطلاعات فنی سرور.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('getlinks:'))
def handle_account_get_links(call):
    mode = call.data.split(':')[1]
    param = call.data.split(':')[2]
    user_id = call.message.chat.id
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    if mode == "sub":
        subscription_url = _subscription_url(param)
        bot.send_message(user_id, f"🌐 **لینک سابسکریپشن اختصاصی شما (پورت 2096):**\n\n```\n{subscription_url}\n```", parse_mode="Markdown")
    elif mode == "dir":
        bot.answer_callback_query(call.id, "در حال استخراج...")
        get_links_url = _xui_url(f"panel/api/clients/links/{quote(str(param), safe='')}")
        res = requests.get(get_links_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        config_links = res.json().get("obj", []) if res.status_code == 200 and res.json().get("success") else []
        
        if config_links:
            msg_text = "🔑 **کانفیگ‌های اتصال مستقیم شما:**\n\n"
            for link in config_links:
                msg_text += f"```\n{link}\n```\n"
            bot.send_message(user_id, msg_text, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ کانفیگ مستقیمی یافت نشد.")

# --- SUPPORT SYSTEM ---
@bot.message_handler(func=lambda message: message.text == "📞 پشتیبانی")
def support_mode(message):
    USER_STATES[message.chat.id] = 'SUPPORT'
    bot.send_message(message.chat.id, "📞 **بخش پشتیبانی SpeedPing**\n\nپیام خود را ارسال کنید. مدیریت به زودی پاسخ خواهد داد.", reply_markup=back_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.from_user.id == ADMIN_ID)
def handle_admin_reply(message):
    admin_reply_id = message.reply_to_message.message_id
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM support_messages WHERE admin_msg_id = ?", (admin_reply_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        target_user_id = row[0]
        try:
            bot.copy_message(chat_id=target_user_id, from_chat_id=ADMIN_ID, message_id=message.message_id)
            bot.send_message(ADMIN_ID, "✅ پاسخ ارسال شد.")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ خطا: {str(e)}")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'SUPPORT', content_types=['text', 'photo', 'voice', 'video', 'document'])
def forward_to_admin(message):
    bot.send_message(ADMIN_ID, f"👤 **پیام جدید پشتیبانی از کاربر:** `{message.chat.id}`\nReply کنید:")
    admin_msg = bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO support_messages (admin_msg_id, user_id) VALUES (?, ?)", (admin_msg.message_id, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "⏳ پیام شما به پشتیبانی ارسال شد.")

# --- 👑 POWERFUL ADMIN PANEL (/sudoadmin) ---
def _run_xui_diagnostic():
    """Read-only checks for API path/auth; does not create, edit or delete anything."""
    headers = _xui_headers()
    proxies = _xui_proxies()
    checks = [
        ("Inbounds", _xui_url("panel/api/inbounds/list")),
        ("Clients", _xui_url("panel/api/clients/list")),
    ]
    results = []
    for name, url in checks:
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=15, verify=not DEVELOPMENT_MODE)
            data = _safe_json(r)
            if r.status_code == 200 and data.get("success"):
                obj = data.get("obj")
                count = len(obj) if isinstance(obj, list) else "OK"
                results.append(f"✅ {name}: HTTP 200 / success=true / count={count}")
            else:
                results.append("❌ " + _xui_response_error(r, name))
        except requests.exceptions.SSLError as e:
            results.append(f"❌ {name}: خطای TLS/SSL: {str(e)[:300]}")
        except requests.exceptions.RequestException as e:
            results.append(f"❌ {name}: خطای شبکه: {str(e)[:300]}")
        except Exception as e:
            results.append(f"❌ {name}: {str(e)[:400]}")
    return "\n\n".join(results)


@bot.message_handler(commands=['xuidiag'])
def xui_diag_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "🔎 در حال تست Read-only اتصال 3x-ui...")
    bot.send_message(
        message.chat.id,
        "🧪 نتیجه تست 3x-ui:\n\n" + _run_xui_diagnostic() +
        "\n\nاین تست هیچ کاربر یا Inboundی را تغییر نمی‌دهد."
    )


@bot.message_handler(commands=['sudoadmin'])
def super_admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ شما به این منو دسترسی ندارید.")
        return
    bot.send_message(message.chat.id, "🚀 **به پنل مدیریت ارشد SpeedPing خوش آمدید**\nتنظیمات مورد نظر را انتخاب کنید:", reply_markup=admin_main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def handle_admin_panel_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    action = call.data.split(':')[1]
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None

    if action == "approve" or action == "reject":
        tx_id = int(call.data.split(':')[2])
        handle_invoice_decision(call, action, tx_id)
        return

    if action == "stats":
        conn = _db_connect()
        total_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()['c']
        active_users = conn.execute("SELECT COUNT(*) AS c FROM users WHERE is_active = 1").fetchone()['c']
        total_sales_count = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status = 'APPROVED'").fetchone()['c']
        total_trials_count = conn.execute("SELECT COUNT(*) AS c FROM trial_services WHERE status = 'ACTIVE'").fetchone()['c']
        gross_sales = conn.execute("SELECT COALESCE(SUM(price), 0) AS s FROM transactions WHERE status = 'APPROVED'").fetchone()['s']
        cash_revenue = conn.execute("SELECT COALESCE(SUM(cash_amount), 0) AS s FROM transactions WHERE status = 'APPROVED'").fetchone()['s']
        wallet_sales = conn.execute("SELECT COALESCE(SUM(wallet_used), 0) AS s FROM transactions WHERE status = 'APPROVED'").fetchone()['s']
        commissions = conn.execute("SELECT COALESCE(SUM(commission_amount), 0) AS s FROM referral_commissions").fetchone()['s']
        referrals = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referred_by IS NOT NULL").fetchone()['c']
        issues = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status = 'ISSUE'").fetchone()['c']
        conn.close()

        stats_text = (
            f"📊 **آمار سیستم فروش SpeedPing:**\n\n"
            f"👤 کل کاربران ثبت‌شده: `{int(total_users)} نفر`\n"
            f"🟢 کاربران فعال در ربات: `{int(active_users)} نفر`\n"
            f"📦 فروش موفق: `{int(total_sales_count)} عدد`\n"
            f"🎁 تست صادرشده: `{int(total_trials_count)} عدد`\n"
            f"🤝 کاربران ورودی از معرفی: `{int(referrals)} نفر`\n"
            f"💰 پورسانت پرداخت‌شده: `{int(commissions):,} تومان`\n"
            f"💵 ارزش کل فروش: `{int(gross_sales):,} تومان`\n"
            f"🏦 دریافت نقدی/کارت: `{int(cash_revenue):,} تومان`\n"
            f"👛 فروش از کیف پول: `{int(wallet_sales):,} تومان`\n"
            f"⚠️ تراکنش نیازمند بررسی: `{int(issues)} عدد`"
        )
        bot.send_message(ADMIN_ID, stats_text, parse_mode="Markdown")

    elif action == "affiliate":
        conn = _db_connect()
        referrals_count = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referred_by IS NOT NULL").fetchone()['c']
        commissions_count = conn.execute("SELECT COUNT(*) AS c FROM referral_commissions").fetchone()['c']
        commissions_sum = conn.execute("SELECT COALESCE(SUM(commission_amount),0) AS s FROM referral_commissions").fetchone()['s']
        wallet_total = conn.execute("SELECT COALESCE(SUM(balance),0) AS s FROM users").fetchone()['s']
        conn.close()
        enabled = referral_enabled()
        percent = get_referral_percent()
        text = (
            "🤝 **مدیریت همکاری در فروش**\n\n"
            f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n"
            f"نرخ پورسانت: **{percent:g}٪**\n"
            f"دعوت‌های ثبت‌شده: **{int(referrals_count)}**\n"
            f"پورسانت‌های ثبت‌شده: **{int(commissions_count)}**\n"
            f"مجموع پورسانت: **{int(commissions_sum):,} تومان**\n"
            f"مجموع مانده کیف پول کاربران: **{int(wallet_total):,} تومان**"
        )
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("⏯ روشن/خاموش", callback_data="admin:affiliate_toggle"),
            types.InlineKeyboardButton("📈 تغییر درصد", callback_data="admin:affiliate_percent"),
            types.InlineKeyboardButton("👛 شارژ/کسر کیف پول", callback_data="admin:affiliate_wallet"),
            types.InlineKeyboardButton("🏆 برترین معرف‌ها", callback_data="admin:affiliate_top")
        )
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=m)

    elif action == "affiliate_toggle":
        new_value = '0' if referral_enabled() else '1'
        update_db_setting('referral_enabled', new_value)
        bot.answer_callback_query(call.id, "وضعیت تغییر کرد ✅")
        bot.send_message(ADMIN_ID, f"🤝 همکاری در فروش {'فعال شد 🟢' if new_value == '1' else 'غیرفعال شد 🔴'}")

    elif action == "affiliate_percent":
        msg = bot.send_message(ADMIN_ID, "📈 درصد پورسانت جدید را از 0 تا 100 وارد کنید. مثال: `10` یا `7.5`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_affiliate_percent)

    elif action == "affiliate_wallet":
        msg = bot.send_message(ADMIN_ID, "👛 آیدی کاربر و مبلغ را در یک خط بفرستید.\nمثال شارژ: `123456789 50000`\nمثال کسر: `123456789 -20000`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_wallet_adjustment)

    elif action == "affiliate_top":
        conn = _db_connect()
        rows = conn.execute(
            """SELECT referrer_id, COUNT(DISTINCT referred_id) AS buyers, SUM(commission_amount) AS earned
               FROM referral_commissions GROUP BY referrer_id ORDER BY earned DESC LIMIT 10"""
        ).fetchall()
        conn.close()
        if not rows:
            bot.send_message(ADMIN_ID, "🏆 هنوز پورسانتی ثبت نشده است.")
        else:
            lines = ["🏆 **۱۰ معرف برتر**\n"]
            for i, row in enumerate(rows, 1):
                lines.append(f"{i}. `{row['referrer_id']}` — خریدار: {int(row['buyers'])} — پورسانت: **{int(row['earned'] or 0):,} تومان**")
            bot.send_message(ADMIN_ID, "\n".join(lines), parse_mode="Markdown")

    elif action == "retry":
        tx_id = int(call.data.split(':')[2])
        retry_issue_transaction(call, tx_id)
        return

    elif action == "refund_wallet":
        tx_id = int(call.data.split(':')[2])
        refund_issue_wallet_transaction(call, tx_id)
        return

    elif action == "notifications":
        enabled = service_notifications_enabled()
        interval = get_service_notification_interval()
        volume_warn = get_service_volume_warning_percent()
        expiry_warn = get_service_expiry_warning_hours(False)
        trial_warn = get_service_expiry_warning_hours(True)
        conn = _db_connect()
        sent_total = conn.execute("SELECT COUNT(*) AS c FROM service_notifications").fetchone()['c']
        expired_count = conn.execute("SELECT COUNT(*) AS c FROM service_notifications WHERE event_type IN ('VOLUME_EXHAUSTED','TIME_EXPIRED')").fetchone()['c']
        conn.close()
        text = (
            "🔔 **مدیریت اعلان سرویس‌ها**\n\n"
            f"وضعیت: {'🟢 فعال' if enabled else '🔴 غیرفعال'}\n"
            f"فاصله بررسی پنل: **{interval // 60 if interval >= 60 else interval} {'دقیقه' if interval >= 60 else 'ثانیه'}**\n"
            f"هشدار حجم: **{volume_warn:g}٪ مصرف**\n"
            f"هشدار زمان سرویس پولی: **{expiry_warn:g} ساعت مانده**\n"
            f"هشدار زمان تست: **{trial_warn:g} ساعت مانده**\n"
            f"رویدادهای ثبت‌شده: **{int(sent_total)}**\n"
            f"اعلان‌های اتمام ثبت‌شده: **{int(expired_count)}**\n\n"
            "اعلان اتمام حجم/زمان برای هر سرویس فقط یک‌بار ثبت و ارسال می‌شود."
        )
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("⏯ روشن/خاموش", callback_data="admin:notifications_toggle"),
            types.InlineKeyboardButton("🔄 بررسی همین الان", callback_data="admin:notifications_check")
        )
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=m)

    elif action == "notifications_toggle":
        new_value = '0' if service_notifications_enabled() else '1'
        update_db_setting('service_notifications_enabled', new_value)
        bot.answer_callback_query(call.id, "وضعیت تغییر کرد ✅")
        bot.send_message(ADMIN_ID, f"🔔 اعلان سرویس‌ها {'فعال شد 🟢' if new_value == '1' else 'غیرفعال شد 🔴'}")

    elif action == "notifications_check":
        bot.answer_callback_query(call.id, "در حال بررسی پنل...")
        result = check_service_notifications(force=True)
        bot.send_message(ADMIN_ID, _format_monitor_result(result), parse_mode="Markdown")

    elif action == "server_status":
        bot.answer_callback_query(call.id, "در حال استعلام وضعیت زنده...")
        try:
            status_url = _xui_url("panel/api/server/status")
            res = requests.get(status_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
            if res.status_code == 200 and res.json().get("success"):
                obj = res.json().get("obj", {})
                cpu = obj.get("cpu", 0)
                mem_curr = obj.get("mem", {}).get("current", 0) / (1024**3)
                mem_total = obj.get("mem", {}).get("total", 0) / (1024**3)
                disk_curr = obj.get("disk", {}).get("current", 0) / (1024**3)
                disk_total = obj.get("disk", {}).get("total", 0) / (1024**3)
                xray_state = obj.get("xray", {}).get("state", "unknown")
                xray_ver = obj.get("xray", {}).get("version", "unknown")
                
                srv_txt = f"🖥 **وضعیت فعلی سرور آلمان SpeedPing:**\n\n" \
                          f"🔥 مصرف پردازنده: `{cpu}%`\n" \
                          f"🧠 حافظه رم: `{mem_curr:.2f} GB / {mem_total:.2f} GB`\n" \
                          f"💾 دیسک سرور: `{disk_curr:.2f} GB / {disk_total:.2f} GB`\n" \
                          f"⚙️ وضعیت هسته Xray: *{xray_state} ({xray_ver})*"
                bot.send_message(ADMIN_ID, srv_txt, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"🚨 خطا در ارتباط با وب‌سرویس سرور")
            
    elif action == "broadcast":
        msg = bot.send_message(ADMIN_ID, "📣 پیام همگانی خود را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_broadcast)
        
    elif action == "bank_config":
        card_num = get_db_setting('card_number')
        card_holder = get_db_setting('card_holder')
        bank_name = get_db_setting('bank_name')
        
        bank_txt = f"💳 **مشخصات فعلی واریز ربات:**\n\n🏦 بانک: {bank_name}\n💳 شماره کارت: `{card_num}`\n👤 به نام: {card_holder}"
        b_markup = types.InlineKeyboardMarkup()
        b_markup.add(
            types.InlineKeyboardButton("✏️ تغییر شماره کارت", callback_data="admin:edit_card"),
            types.InlineKeyboardButton("✏️ تغییر نام صاحب حساب", callback_data="admin:edit_holder"),
            types.InlineKeyboardButton("✏️ تغییر نام بانک", callback_data="admin:edit_bank")
        )
        bot.send_message(ADMIN_ID, bank_txt, parse_mode="Markdown", reply_markup=b_markup)
        
    elif action in ["edit_card", "edit_holder", "edit_bank"]:
        msg = bot.send_message(ADMIN_ID, f"✍️ مقدار جدید را وارد کنید:")
        bot.register_next_step_handler(msg, process_edit_bank, action)
        
    elif action == "delete_user":
        msg = bot.send_message(ADMIN_ID, "👤 آیدی عددی کاربر را برای غیرفعال‌سازی وارد کنید. سوابق مالی، تست و معرف حذف نمی‌شوند:")
        bot.register_next_step_handler(msg, process_delete_bot_user)
        
    elif action == "delete_sub":
        msg = bot.send_message(ADMIN_ID, "🔌 نام اشتراک (Email) مورد نظر در پنل را جهت حذف وارد کنید:")
        bot.register_next_step_handler(msg, process_delete_panel_sub)

def handle_invoice_decision(call, action, tx_id):
    conn = _db_connect()
    tx = conn.execute(
        "SELECT user_id, plan_id, status, payment_method FROM transactions WHERE id = ?",
        (tx_id,)
    ).fetchone()

    if not tx or tx['status'] != 'PENDING':
        bot.answer_callback_query(call.id, "این تراکنش قبلاً تعیین تکلیف شده است.")
        conn.close()
        return

    user_id = int(tx['user_id'])

    if action == "approve":
        conn.execute("UPDATE transactions SET status = 'PROCESSING', last_error = NULL WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "پرداخت تایید شد؛ در حال صدور سرویس...")
        try:
            bot.edit_message_caption(
                chat_id=ADMIN_ID,
                message_id=call.message.message_id,
                caption=f"⏳ فیش {tx_id} تایید شد و سرویس در حال صدور است..."
            )
        except Exception:
            pass
        finalize_service_transaction(tx_id, admin_message_id=call.message.message_id)
    elif action == "reject":
        conn.execute("UPDATE transactions SET status = 'REJECTED', last_error = NULL WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "فیش رد شد.")
        try:
            bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption=f"❌ فیش {tx_id} رد شد.")
        except Exception:
            pass
        bot.send_message(user_id, "❌ فیش واریزی شما توسط پشتیبانی رد شد.", reply_markup=main_menu())


def process_affiliate_percent(message):
    try:
        value = float((message.text or '').strip().replace('٪', '').replace('%', ''))
        if value < 0 or value > 100:
            raise ValueError
        update_db_setting('referral_commission_percent', f"{value:g}")
        bot.send_message(ADMIN_ID, f"✅ نرخ پورسانت همکاری در فروش روی **{value:g}٪** تنظیم شد.", parse_mode="Markdown")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ درصد نامعتبر است. عددی بین 0 و 100 وارد کنید.")


def process_admin_wallet_adjustment(message):
    try:
        parts = (message.text or '').replace(',', '').split()
        if len(parts) != 2:
            raise ValueError
        user_id = int(parts[0])
        amount = int(parts[1])
        if amount == 0:
            raise ValueError
        ok, new_balance = wallet_adjust(
            user_id,
            amount,
            'ADMIN_ADJUSTMENT',
            f"اصلاح دستی کیف پول توسط ادمین ({amount:+,} تومان)",
            unique_key=f"admin_adjust:{user_id}:{int(time.time()*1000)}"
        )
        if not ok:
            bot.send_message(ADMIN_ID, f"❌ موجودی کاربر برای کسر این مبلغ کافی نیست. موجودی فعلی: {new_balance:,} تومان")
            return
        bot.send_message(ADMIN_ID, f"✅ کیف پول `{user_id}` اصلاح شد. موجودی جدید: **{new_balance:,} تومان**", parse_mode="Markdown")
        try:
            bot.send_message(user_id, f"👛 کیف پول شما توسط مدیریت **{amount:+,} تومان** تغییر کرد.\nموجودی جدید: **{new_balance:,} تومان**", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.send_message(ADMIN_ID, "❌ فرمت نامعتبر است. مثال: `123456789 50000` یا `123456789 -20000`", parse_mode="Markdown")


def retry_issue_transaction(call, tx_id):
    conn = _db_connect()
    tx = conn.execute("SELECT status FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if not tx or tx['status'] != 'ISSUE':
        conn.close()
        bot.answer_callback_query(call.id, "این تراکنش در وضعیت ISSUE نیست.", show_alert=True)
        return
    conn.execute("UPDATE transactions SET status = 'PROCESSING', last_error = NULL WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "Retry شروع شد...")
    finalize_service_transaction(tx_id)


def refund_issue_wallet_transaction(call, tx_id):
    conn = _db_connect()
    tx = conn.execute(
        "SELECT user_id, price, payment_method, wallet_used, status, service_email FROM transactions WHERE id = ?",
        (tx_id,)
    ).fetchone()
    conn.close()
    if not tx or tx['status'] != 'ISSUE' or tx['payment_method'] != 'WALLET':
        bot.answer_callback_query(call.id, "این تراکنش قابل بازپرداخت کیف پول نیست.", show_alert=True)
        return

    # برای جلوگیری از سرویس رایگان، تا وقتی مطمئن نشویم کلاینت روی پنل وجود ندارد بازپرداخت نمی‌کنیم.
    try:
        client = _get_client_data(tx['service_email'], _xui_headers(), _xui_proxies())
    except Exception:
        bot.answer_callback_query(call.id, "پنل قابل استعلام نیست؛ بازپرداخت انجام نشد.", show_alert=True)
        return
    if client:
        bot.answer_callback_query(call.id, "کلاینت روی پنل وجود دارد؛ ابتدا سرویس را Retry/بررسی کنید.", show_alert=True)
        return

    amount = int(tx['wallet_used'] or tx['price'] or 0)
    ok, balance = wallet_adjust(
        int(tx['user_id']),
        amount,
        'REFUND',
        f"بازپرداخت خرید ناموفق تراکنش #{tx_id}",
        related_tx_id=tx_id,
        unique_key=f"wallet_refund:{tx_id}"
    )
    if not ok:
        bot.answer_callback_query(call.id, "بازپرداخت انجام نشد.", show_alert=True)
        return
    conn = _db_connect()
    conn.execute("UPDATE transactions SET status = 'REFUNDED', last_error = NULL WHERE id = ? AND status = 'ISSUE'", (tx_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "مبلغ به کیف پول برگشت ✅")
    bot.send_message(ADMIN_ID, f"✅ تراکنش کیف پول `{tx_id}` بازپرداخت شد. موجودی کاربر: **{balance:,} تومان**", parse_mode="Markdown")
    try:
        bot.send_message(int(tx['user_id']), f"👛 مبلغ **{amount:,} تومان** بابت تراکنش ناموفق `{tx_id}` به کیف پول شما برگشت.", parse_mode="Markdown")
    except Exception:
        pass


def process_admin_broadcast(message):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE is_active = 1")
    users = cursor.fetchall()
    conn.close()
    
    bot.send_message(ADMIN_ID, f"⏳ فرآیند ارسال آغاز شد...")
    success_count = 0
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=ADMIN_ID, message_id=message.message_id)
            success_count += 1
            time.sleep(0.04)
        except: continue
    bot.send_message(ADMIN_ID, f"✅ تحویل موفق به {success_count} کاربر.")

def process_edit_bank(message, field_type):
    if field_type == "admin:edit_card" or field_type == "edit_card":
        update_db_setting('card_number', message.text.strip())
    elif field_type == "admin:edit_holder" or field_type == "edit_holder":
        update_db_setting('card_holder', message.text.strip())
    elif field_type == "admin:edit_bank" or field_type == "edit_bank":
        update_db_setting('bank_name', message.text.strip())
    bot.send_message(ADMIN_ID, "✅ مشخصات بانکی با موفقیت به‌روزرسانی شد.")

def process_delete_bot_user(message):
    try:
        target_id = int(message.text.strip())
        conn = _db_connect()
        row = conn.execute("SELECT id FROM users WHERE id = ?", (target_id,)).fetchone()
        if not row:
            conn.close()
            bot.send_message(ADMIN_ID, "❌ این کاربر در دیتابیس نیست.")
            return
        # حذف فیزیکی انجام نمی‌شود تا سوابق تست، معرف و کیف پول قابل سوءاستفاده نباشند.
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ کاربر `{target_id}` غیرفعال شد و از پیام‌های همگانی حذف می‌شود. سوابق مالی/معرف برای امنیت حفظ شدند.", parse_mode="Markdown")
    except Exception:
        bot.send_message(ADMIN_ID, "❌ آیدی نامعتبر.")

def process_delete_panel_sub(message):
    email = message.text.strip()
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    try:
        del_url = _xui_url(f"panel/api/clients/del/{quote(str(email), safe='')}") + "?keepTraffic=0"
        res = requests.post(del_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        if res.status_code == 200 and res.json().get("success"):
            bot.send_message(ADMIN_ID, f"✅ اشتراک `{email}` با موفقیت از پنل حذف شد.")
        else: bot.send_message(ADMIN_ID, f"❌ خطای پنل: {res.text}")
    except Exception as e: bot.send_message(ADMIN_ID, f"🚨 خطای ارتباطی")

# --- X-UI AUTO CREATION ENGINE ---
def _xui_headers():
    return {
        "Authorization": f"Bearer {XUI_BEARER_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


def _xui_url(endpoint):
    """Build a 3x-ui API URL while safely honoring the configured web base path."""
    base = (XUI_API_URL or "").strip().rstrip("/")
    base_path = (XUI_BASE_PATH or "").strip()
    if not base:
        raise RuntimeError("XUI_API_URL تنظیم نشده است.")
    if base_path in ("", "/"):
        prefix = ""
    else:
        prefix = "/" + base_path.strip("/")
    return f"{base}{prefix}/{endpoint.lstrip('/')}"


def _subscription_url(sub_id):
    base = (XUI_SUB_SERVER_URL or "").strip().rstrip("/")
    path = (XUI_SUB_PATH or "/sub/").strip()
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return f"{base}{path}{quote(str(sub_id), safe='')}"


def _xui_response_error(response, action):
    """Return a useful diagnostic without ever exposing the Bearer token."""
    status = getattr(response, "status_code", "?")
    url = getattr(response, "url", "")
    body = (getattr(response, "text", "") or "").strip()
    if len(body) > 500:
        body = body[:500] + "…"
    if not body:
        body = "<empty response body>"

    hint = ""
    if status in (401, 403):
        hint = (" | راهنما: احراز هویت رد شده. XUI_BEARER_TOKEN باید خود Token تولیدشده در "
                "Settings → Security → API Token باشد، نه نام Token و نه Web Base Path.")
    elif status == 404:
        hint = (" | راهنما: مسیر API پیدا نشد. XUI_BASE_PATH، نسخه 3x-ui و Reverse Proxy را بررسی کنید. "
                "Endpointهای جدید زیر /panel/api/* هستند.")
    elif isinstance(status, int) and status >= 500:
        hint = " | راهنما: خطا از خود پنل/Reverse Proxy است؛ لاگ 3x-ui را بررسی کنید."

    return f"{action} | HTTP {status} | URL: {url} | پاسخ: {body}{hint}"


def _xui_proxies():
    if DEVELOPMENT_MODE:
        return {
            'http': 'http://127.0.0.1:10808',
            'https': 'http://127.0.0.1:10808'
        }
    return None


def _safe_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def _get_active_inbound_ids(headers, request_proxies):
    get_inbounds_url = _xui_url("panel/api/inbounds/list")
    response = requests.get(
        get_inbounds_url,
        headers=headers,
        proxies=request_proxies,
        timeout=15,
        verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get("success"):
        raise RuntimeError(_xui_response_error(response, "خطا در دریافت Inboundها از پنل"))

    inbounds = data.get("obj", []) or []
    active_ids = [ib["id"] for ib in inbounds if ib.get("enable", True) and ib.get("id") is not None]
    if not active_ids:
        raise RuntimeError("هیچ Inbound فعالی در پنل پیدا نشد.")
    return active_ids


def _get_client_data(user_email, headers, request_proxies):
    client_url = _xui_url(f"panel/api/clients/get/{quote(str(user_email), safe='')}")
    response = requests.get(
        client_url,
        headers=headers,
        proxies=request_proxies,
        timeout=15,
        verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code == 200 and data.get("success"):
        return data.get("obj", {}) or {}
    return {}


def _get_client_links(user_email, headers, request_proxies):
    get_links_url = _xui_url(f"panel/api/clients/links/{quote(str(user_email), safe='')}")
    response = requests.get(
        get_links_url,
        headers=headers,
        proxies=request_proxies,
        timeout=15,
        verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code == 200 and data.get("success"):
        return data.get("obj", []) or []
    return []


def _extract_subscription_id(client_data, config_links=None):
    # طبق API رسمی، لینک Subscription فقط باید از subId ساخته شود.
    # UUID/ID کلاینت جایگزین معتبر subId نیست.
    sub_id = (client_data or {}).get("subId") or (client_data or {}).get("subid")
    return str(sub_id) if sub_id else None


def _get_client_subscription_id(user_email, headers, request_proxies, client_data=None):
    sub_id = _extract_subscription_id(client_data or {})
    if sub_id:
        return sub_id

    # Endpoint رسمی traffic نیز subId را برمی‌گرداند و fallback مطمئنی است.
    traffic_url = _xui_url(f"panel/api/clients/traffic/{quote(str(user_email), safe='')}")
    response = requests.get(
        traffic_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code == 200 and data.get("success"):
        return _extract_subscription_id(data.get("obj") or {})
    return None


def _mark_trial(user_id, status, error=None):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    if status == 'ACTIVE':
        cursor.execute(
            "UPDATE trial_services SET status = 'ACTIVE', activated_at = ?, last_error = NULL WHERE user_id = ?",
            (int(time.time()), user_id)
        )
    else:
        cursor.execute(
            "UPDATE trial_services SET status = ?, last_error = ? WHERE user_id = ?",
            (status, (str(error)[:1000] if error else None), user_id)
        )
    conn.commit()
    conn.close()


def generate_trial_xui_config(user_id, user_email):
    """صدور اکانت تست 1GB / 1 day به صورت idempotent برای هر Telegram user."""
    total_bytes = 1 * 1024 * 1024 * 1024
    expiry_time_ms = int((time.time() + 86400) * 1000)
    headers = _xui_headers()
    request_proxies = _xui_proxies()

    try:
        # اگر تلاش قبلی پس از ساخت کلاینت قطع شده باشد، دوباره کلاینت تکراری نساز.
        client_data = _get_client_data(user_email, headers, request_proxies)

        if not client_data:
            active_inbound_ids = _get_active_inbound_ids(headers, request_proxies)
            payload = {
                "client": {
                    "email": user_email,
                    "totalGB": total_bytes,
                    "expiryTime": expiry_time_ms,
                    "tgId": user_id,
                    "limitIp": 2,
                    "enable": True
                },
                "inboundIds": active_inbound_ids
            }

            add_client_url = _xui_url("panel/api/clients/add")
            add_response = requests.post(
                add_client_url,
                json=payload,
                headers=headers,
                proxies=request_proxies,
                timeout=15,
                verify=not DEVELOPMENT_MODE
            )
            add_data = _safe_json(add_response)
            if add_response.status_code != 200 or not add_data.get("success"):
                raise RuntimeError(_xui_response_error(add_response, "پنل ساخت اکانت تست را رد کرد"))

            time.sleep(1.0)
            client_data = _get_client_data(user_email, headers, request_proxies)

        config_links = _get_client_links(user_email, headers, request_proxies)
        sub_id = _get_client_subscription_id(user_email, headers, request_proxies, client_data)

        if not sub_id and not config_links:
            raise RuntimeError("اکانت ساخته شد اما پنل هیچ لینک سابسکریپشن یا کانفیگی برنگرداند.")

        _mark_trial(user_id, 'ACTIVE')
    except Exception as e:
        _mark_trial(user_id, 'FAILED', e)
        try:
            bot.send_message(
                user_id,
                "❌ در صدور تست رایگان مشکلی پیش آمد. درخواست شما مصرف‌شده حساب نشده؛ کمی بعد دوباره دکمه تست رایگان را بزنید.",
                reply_markup=main_menu()
            )
        except Exception:
            pass
        try:
            bot.send_message(ADMIN_ID, f"🚨 خطا در صدور تست رایگان برای {user_id}:\n{str(e)[:800]}")
        except Exception:
            pass
        return

    msg_text = (
            "🎁 **تست رایگان SpeedPing شما فعال شد!**\n\n"
            "📦 حجم: **1 گیگابایت**\n"
            "⏱ اعتبار: **1 روز**\n"
            "👤 هر کاربر فقط یک‌بار می‌تواند تست رایگان دریافت کند.\n\n"
    )

    if sub_id:
        subscription_url = _subscription_url(sub_id)
        msg_text += f"🌐 **لینک سابسکریپشن:**\n```\n{subscription_url}\n```\n"

    if config_links:
        msg_text += "\n🔑 **کانفیگ‌های اتصال مستقیم:**\n"
        for link in config_links:
            msg_text += f"```\n{link}\n```\n"

    msg_text += "\nاگر سرویس برای شما مناسب بود، از بخش خرید می‌توانید سرویس اصلی را تهیه کنید. ⚡️"

    # خطای ارسال پیام تلگرام نباید یک سرویس واقعاً ساخته‌شده را FAILED کند.
    try:
        bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=main_menu())
    except Exception as e:
        try:
            bot.send_message(ADMIN_ID, f"⚠️ تست کاربر {user_id} ساخته شد اما پیام تحویل به کاربر ارسال نشد: {str(e)[:500]}")
        except Exception:
            pass

    try:
        bot.send_message(ADMIN_ID, f"🎁 تست رایگان برای کاربر `{user_id}` با موفقیت صادر شد.", parse_mode="Markdown")
    except Exception:
        pass


def provision_xui_service(user_id, plan_id, tx_id, user_email):
    """Create/read a paid X-UI client idempotently and return delivery links."""
    plan = PLANS[plan_id]
    total_bytes = plan['volume'] * 1024 * 1024 * 1024 if plan['volume'] > 0 else 0
    expiry_time_ms = int((time.time() + (plan['days'] * 86400)) * 1000)
    headers = _xui_headers()
    request_proxies = _xui_proxies()

    client_data = _get_client_data(user_email, headers, request_proxies)
    if not client_data:
        active_inbound_ids = _get_active_inbound_ids(headers, request_proxies)
        payload = {
            "client": {
                "email": user_email,
                "totalGB": total_bytes,
                "expiryTime": expiry_time_ms,
                "tgId": user_id,
                "limitIp": 2,
                "enable": True
            },
            "inboundIds": active_inbound_ids
        }
        add_client_url = _xui_url("panel/api/clients/add")
        response = requests.post(
            add_client_url,
            json=payload,
            headers=headers,
            proxies=request_proxies,
            timeout=15,
            verify=not DEVELOPMENT_MODE
        )
        data = _safe_json(response)
        if response.status_code != 200 or not data.get('success'):
            # ممکن است پنل کلاینت را ساخته باشد ولی پاسخ ناقص برگشته باشد؛ یک بار استعلام کن.
            time.sleep(0.8)
            client_data = _get_client_data(user_email, headers, request_proxies)
            if not client_data:
                raise RuntimeError(_xui_response_error(response, "پنل ساخت سرویس را رد کرد"))
        else:
            time.sleep(1.0)
            client_data = _get_client_data(user_email, headers, request_proxies)

    config_links = _get_client_links(user_email, headers, request_proxies)
    sub_id = _get_client_subscription_id(user_email, headers, request_proxies, client_data)
    if not sub_id and not config_links:
        raise RuntimeError("سرویس روی پنل وجود دارد اما هیچ لینک قابل تحویلی دریافت نشد.")
    return sub_id, config_links


def _send_paid_service(user_id, plan_id, tx_id, sub_id, config_links):
    plan = PLANS[plan_id]
    msg_text = (
        f"🎉 **سرویس SpeedPing شما فعال شد!**\n\n"
        f"📦 پلن: **{plan['name']}**\n"
        f"🆔 کد تراکنش: `{tx_id}`\n\n"
    )
    if sub_id:
        subscription_url = _subscription_url(sub_id)
        msg_text += f"🌐 **لینک سابسکریپشن:**\n```\n{subscription_url}\n```\n"
    if config_links:
        msg_text += "\n🔑 **کانفیگ‌های اتصال مستقیم:**\n"
        for link in config_links:
            msg_text += f"```\n{link}\n```\n"
    msg_text += "\n📱 لینک‌ها را در نرم‌افزار خود وارد کنید. از SpeedPing لذت ببرید!"
    bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=main_menu())


def finalize_service_transaction(tx_id, admin_message_id=None):
    """Provision the paid service, then mark APPROVED and credit referral commission exactly once."""
    conn = _db_connect()
    tx = conn.execute(
        "SELECT id, user_id, plan_id, status, service_email, payment_method FROM transactions WHERE id = ?",
        (tx_id,)
    ).fetchone()
    conn.close()
    if not tx or tx['status'] not in ('PROCESSING', 'ISSUE'):
        return False

    user_id = int(tx['user_id'])
    plan_id = int(tx['plan_id'])
    user_email = tx['service_email'] or f"speedping_{user_id}_{tx_id}"

    try:
        sub_id, config_links = provision_xui_service(user_id, plan_id, tx_id, user_email)
    except Exception as e:
        error_text = str(e)[:1000]
        conn = _db_connect()
        conn.execute(
            "UPDATE transactions SET status = 'ISSUE', last_error = ?, service_email = ? WHERE id = ? AND status IN ('PROCESSING','ISSUE')",
            (error_text, user_email, tx_id)
        )
        conn.commit()
        conn.close()

        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        admin_markup.add(types.InlineKeyboardButton("🔄 Retry صدور", callback_data=f"admin:retry:{tx_id}"))
        if tx['payment_method'] == 'WALLET':
            admin_markup.add(types.InlineKeyboardButton("↩️ بازپرداخت کیف پول", callback_data=f"admin:refund_wallet:{tx_id}"))
        try:
            bot.send_message(
                ADMIN_ID,
                f"🚨 **تراکنش {tx_id} نیازمند بررسی است**\n\n👤 کاربر: `{user_id}`\n✉️ سرویس: `{user_email}`\n⚠️ خطا: `{error_text}`\n\nRetry به‌صورت idempotent است و اگر کلاینت قبلاً ساخته شده باشد دوباره ساخته نمی‌شود.",
                parse_mode="Markdown",
                reply_markup=admin_markup
            )
        except Exception:
            pass
        try:
            bot.send_message(user_id, f"⚠️ پرداخت تراکنش `{tx_id}` ثبت شده اما صدور سرویس با مشکل موقت روبه‌رو شده است. پشتیبانی به‌صورت خودکار مطلع شد و مبلغ/پرداخت شما محفوظ است.", parse_mode="Markdown", reply_markup=main_menu())
        except Exception:
            pass
        return False

    # ابتدا وضعیت نهایی تراکنش ثبت می‌شود؛ بعد پورسانت و پیام‌ها.
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT status FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if not current or current['status'] == 'APPROVED':
            conn.rollback()
            return True
        conn.execute(
            "UPDATE transactions SET status = 'APPROVED', approved_at = ?, service_email = ?, last_error = NULL WHERE id = ?",
            (int(time.time()), user_email, tx_id)
        )
        conn.commit()
    finally:
        conn.close()

    try:
        _send_paid_service(user_id, plan_id, tx_id, sub_id, config_links)
    except Exception as e:
        try:
            bot.send_message(ADMIN_ID, f"⚠️ سرویس تراکنش {tx_id} ساخته و APPROVED شد، اما پیام تحویل به کاربر خطا داد: {str(e)[:500]}")
        except Exception:
            pass

    reward = credit_referral_commission(tx_id)
    if reward:
        try:
            bot.send_message(
                reward['referrer_id'],
                f"💰 **پورسانت جدید!**\n\nیکی از کاربران دعوت‌شده شما خرید موفق انجام داد.\n➕ مبلغ پورسانت: **{reward['amount']:,} تومان**\n👛 موجودی جدید کیف پول: **{reward['balance']:,} تومان**",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
        except Exception:
            pass

    try:
        bot.send_message(ADMIN_ID, f"✅ سرویس تراکنش `{tx_id}` برای کاربر `{user_id}` با موفقیت صادر شد.", parse_mode="Markdown")
    except Exception:
        pass
    if admin_message_id:
        try:
            bot.edit_message_caption(chat_id=ADMIN_ID, message_id=admin_message_id, caption=f"✅ فیش {tx_id} تایید شد و سرویس با موفقیت صادر شد.")
        except Exception:
            pass
    return True


def recover_processing_transactions():
    """Recover transactions left in PROCESSING if the bot/server restarted mid-provisioning."""
    conn = _db_connect()
    rows = conn.execute(
        "SELECT id FROM transactions WHERE status = 'PROCESSING' ORDER BY id ASC LIMIT 25"
    ).fetchall()
    conn.close()
    for row in rows:
        try:
            finalize_service_transaction(int(row['id']))
        except Exception as e:
            try:
                bot.send_message(ADMIN_ID, f"⚠️ بازیابی خودکار تراکنش {int(row['id'])} خطا داد: {str(e)[:500]}")
            except Exception:
                pass


def reconcile_missing_referral_commissions():
    """Close the tiny crash window between APPROVED and referral wallet credit."""
    conn = _db_connect()
    rows = conn.execute(
        """SELECT t.id FROM transactions t
           JOIN users u ON u.id = t.user_id
           LEFT JOIN referral_commissions rc ON rc.purchase_tx_id = t.id
           WHERE t.status = 'APPROVED' AND t.cash_amount > 0
             AND u.referred_by IS NOT NULL AND rc.id IS NULL
           ORDER BY t.id ASC LIMIT 100"""
    ).fetchall()
    conn.close()
    for row in rows:
        try:
            reward = credit_referral_commission(int(row['id']))
            if reward:
                try:
                    bot.send_message(
                        reward['referrer_id'],
                        f"💰 پورسانت معوق تراکنش بازیابی شد: **{reward['amount']:,} تومان**\n👛 موجودی جدید: **{reward['balance']:,} تومان**",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        except Exception:
            continue


def service_notifications_enabled():
    return get_db_setting('service_notifications_enabled', '1') == '1'


def _safe_int_setting(key, default_value, minimum, maximum):
    try:
        value = int(float(get_db_setting(key, str(default_value))))
        return max(minimum, min(value, maximum))
    except Exception:
        return default_value


def get_service_notification_interval():
    # حداقل 60 ثانیه تا از فشار غیرضروری به API پنل جلوگیری شود.
    return _safe_int_setting('service_notification_interval_seconds', 300, 60, 3600)


def get_service_volume_warning_percent():
    try:
        value = float(get_db_setting('service_volume_warning_percent', '90'))
        return max(50.0, min(value, 99.9))
    except Exception:
        return 90.0


def get_service_expiry_warning_hours(is_trial=False):
    key = 'trial_expiry_warning_hours' if is_trial else 'service_expiry_warning_hours'
    default = 3 if is_trial else 24
    try:
        value = float(get_db_setting(key, str(default)))
        return max(0.0, min(value, 168.0))
    except Exception:
        return float(default)


def _claim_service_notification(service_email, user_id, service_kind, event_type):
    """Atomically claim an event before sending so restarts cannot duplicate it."""
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO service_notifications (service_email, user_id, service_kind, event_type, created_at) VALUES (?, ?, ?, ?, ?)",
            (service_email, int(user_id), service_kind, event_type, int(time.time()))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def _tracked_service_map():
    """Return service_email -> metadata for paid services and free trials issued by this bot."""
    conn = _db_connect()
    result = {}
    try:
        paid_rows = conn.execute(
            "SELECT user_id, service_email, id AS tx_id FROM transactions WHERE status = 'APPROVED' AND service_email IS NOT NULL AND service_email != ''"
        ).fetchall()
        for row in paid_rows:
            result[str(row['service_email'])] = {
                'user_id': int(row['user_id']), 'kind': 'PAID', 'tx_id': int(row['tx_id'])
            }
        trial_rows = conn.execute(
            "SELECT user_id, email FROM trial_services WHERE status = 'ACTIVE'"
        ).fetchall()
        for row in trial_rows:
            result[str(row['email'])] = {
                'user_id': int(row['user_id']), 'kind': 'TRIAL', 'tx_id': None
            }
        return result
    finally:
        conn.close()


def _fetch_xui_clients_for_monitor():
    url = _xui_url("panel/api/clients/list")
    response = requests.get(
        url,
        headers=_xui_headers(),
        proxies=_xui_proxies(),
        timeout=20,
        verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در مانیتور سرویس‌ها"))
    clients = data.get('obj', []) or []
    return {str(c.get('email')): c for c in clients if c.get('email')}


def _service_usage(client):
    traffic = client.get('traffic') or {}
    up = int(traffic.get('up') or client.get('up') or 0)
    down = int(traffic.get('down') or client.get('down') or 0)
    used = max(0, up + down)
    total = int(client.get('totalGB') or client.get('total') or 0)
    expiry_ms = int(client.get('expiryTime') or 0)
    return used, max(0, total), max(0, expiry_ms)


def _human_gb(byte_count):
    return byte_count / (1024 ** 3)


def _send_service_event(meta, email, event_types, client):
    user_id = int(meta['user_id'])
    is_trial = meta['kind'] == 'TRIAL'
    used, total, expiry_ms = _service_usage(client)
    remaining = max(0, total - used) if total > 0 else None
    now_ms = int(time.time() * 1000)
    hours_left = max(0.0, (expiry_ms - now_ms) / 3600000) if expiry_ms > 0 else None

    event_set = set(event_types)
    if 'VOLUME_EXHAUSTED' in event_set and 'TIME_EXPIRED' in event_set:
        title = "⛔️ حجم و اعتبار زمانی سرویس شما به پایان رسید"
        detail = "هم حجم سرویس مصرف شده و هم تاریخ اعتبار آن گذشته است."
    elif 'VOLUME_EXHAUSTED' in event_set:
        title = "📦 حجم سرویس شما تمام شد"
        detail = "سهمیه حجمی این سرویس به پایان رسیده است."
    elif 'TIME_EXPIRED' in event_set:
        title = "⏰ اعتبار سرویس شما تمام شد"
        detail = "مدت اعتبار زمانی این سرویس به پایان رسیده است."
    elif 'VOLUME_WARNING' in event_set:
        percent = (used / total * 100) if total > 0 else 0
        title = "⚠️ حجم سرویس شما رو به اتمام است"
        detail = f"حدود **{percent:.0f}٪** از حجم سرویس مصرف شده و تقریباً **{_human_gb(remaining):.2f} GB** باقی مانده است."
    elif 'TIME_WARNING' in event_set:
        title = "⚠️ اعتبار سرویس شما رو به اتمام است"
        if hours_left is not None and hours_left < 1:
            detail = f"کمتر از **{max(1, int(hours_left * 60))} دقیقه** از اعتبار سرویس باقی مانده است."
        else:
            detail = f"حدود **{hours_left:.1f} ساعت** از اعتبار سرویس باقی مانده است."
    else:
        return

    kind_text = "تست رایگان" if is_trial else "سرویس SpeedPing"
    text = (
        f"{title}\n\n"
        f"🔹 نوع: **{kind_text}**\n"
        f"🔸 شناسه سرویس: `{email}`\n\n"
        f"{detail}\n\n"
        "برای تهیه سرویس جدید از گزینه **🛍 مشاهده و خرید پلان‌ها** استفاده کنید."
    )
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=main_menu())


def check_service_notifications(force=False):
    """Check tracked bot-issued clients and send one-time quota/expiry notifications."""
    if not service_notifications_enabled() and not force:
        return {'enabled': False, 'tracked': 0, 'found': 0, 'sent': 0, 'missing': 0, 'errors': 0}
    if not SERVICE_MONITOR_LOCK.acquire(blocking=False):
        return {'enabled': True, 'busy': True, 'tracked': 0, 'found': 0, 'sent': 0, 'missing': 0, 'errors': 0}
    result = {'enabled': True, 'busy': False, 'tracked': 0, 'found': 0, 'sent': 0, 'missing': 0, 'errors': 0}
    try:
        tracked = _tracked_service_map()
        result['tracked'] = len(tracked)
        if not tracked:
            return result
        clients = _fetch_xui_clients_for_monitor()
        now_ms = int(time.time() * 1000)
        volume_warning_pct = get_service_volume_warning_percent()

        for email, meta in tracked.items():
            client = clients.get(email)
            if not client:
                result['missing'] += 1
                continue
            result['found'] += 1
            try:
                used, total, expiry_ms = _service_usage(client)
                volume_exhausted = total > 0 and used >= total
                time_expired = expiry_ms > 0 and now_ms >= expiry_ms
                warning_events = []
                end_events = []

                if volume_exhausted:
                    end_events.append('VOLUME_EXHAUSTED')
                elif total > 0 and used > 0 and (used / total * 100.0) >= volume_warning_pct:
                    warning_events.append('VOLUME_WARNING')

                if time_expired:
                    end_events.append('TIME_EXPIRED')
                elif expiry_ms > 0:
                    hours_left = (expiry_ms - now_ms) / 3600000.0
                    threshold = get_service_expiry_warning_hours(meta['kind'] == 'TRIAL')
                    if threshold > 0 and 0 < hours_left <= threshold:
                        warning_events.append('TIME_WARNING')

                # اگر سرویس همین حالا تمام شده، هشدار نزدیک اتمام دیگر فرستاده نمی‌شود.
                events_to_send = end_events if end_events else warning_events
                claimed = []
                for event_type in events_to_send:
                    if _claim_service_notification(email, meta['user_id'], meta['kind'], event_type):
                        claimed.append(event_type)
                if claimed:
                    try:
                        _send_service_event(meta, email, claimed, client)
                        result['sent'] += 1
                    except Exception:
                        # رویداد از قبل claim شده تا پس از restart اعلان تکراری ایجاد نشود.
                        result['errors'] += 1

                if end_events and meta['kind'] == 'TRIAL':
                    conn = _db_connect()
                    conn.execute("UPDATE trial_services SET status = 'EXPIRED' WHERE email = ? AND status = 'ACTIVE'", (email,))
                    conn.commit()
                    conn.close()
            except Exception:
                result['errors'] += 1
        return result
    finally:
        SERVICE_MONITOR_LOCK.release()


def _format_monitor_result(result):
    if not result.get('enabled'):
        return "🔕 سیستم اعلان سرویس‌ها غیرفعال است."
    if result.get('busy'):
        return "⏳ یک بررسی دیگر همین حالا در حال اجراست."
    return (
        "🔔 **نتیجه بررسی سرویس‌ها**\n\n"
        f"📋 سرویس‌های تحت پیگیری: **{result.get('tracked', 0)}**\n"
        f"✅ پیدا شده در پنل: **{result.get('found', 0)}**\n"
        f"📨 پیام ارسال‌شده در این بررسی: **{result.get('sent', 0)}**\n"
        f"❓ پیدا نشده در پنل: **{result.get('missing', 0)}**\n"
        f"⚠️ خطاهای پردازش: **{result.get('errors', 0)}**"
    )


def _service_monitor_loop():
    # کمی بعد از startup شروع می‌شود تا polling و recovery فرصت بالا آمدن داشته باشند.
    time.sleep(10)
    consecutive_errors = 0
    while True:
        try:
            if service_notifications_enabled():
                result = check_service_notifications()
                consecutive_errors = 0 if result.get('errors', 0) == 0 else consecutive_errors + 1
            else:
                consecutive_errors = 0
        except Exception as e:
            consecutive_errors += 1
            # برای جلوگیری از اسپم، فقط هر 12 خطای متوالی یک هشدار به ادمین داده می‌شود.
            if consecutive_errors == 1 or consecutive_errors % 12 == 0:
                try:
                    bot.send_message(ADMIN_ID, f"⚠️ مانیتور سرویس‌ها نتوانست پنل را بررسی کند:\n`{str(e)[:700]}`", parse_mode="Markdown")
                except Exception:
                    pass
        time.sleep(get_service_notification_interval())


def start_service_monitor():
    global SERVICE_MONITOR_THREAD
    if SERVICE_MONITOR_THREAD and SERVICE_MONITOR_THREAD.is_alive():
        return
    SERVICE_MONITOR_THREAD = threading.Thread(target=_service_monitor_loop, name="service-monitor", daemon=True)
    SERVICE_MONITOR_THREAD.start()


@bot.message_handler(commands=['notifydiag'])
def notification_diag_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "🔎 در حال بررسی سرویس‌های ثبت‌شده و وضعیت آن‌ها در 3x-ui...")
    result = check_service_notifications(force=True)
    bot.send_message(message.chat.id, _format_monitor_result(result), parse_mode="Markdown")


def generate_xui_config(user_id, plan_id, tx_id):
    """Compatibility wrapper for older callers."""
    return finalize_service_transaction(tx_id)

if __name__ == '__main__':
    print("SpeedPing Bot is running perfectly...")
    bot.remove_webhook()
    recover_processing_transactions()
    reconcile_missing_referral_commissions()
    start_service_monitor()
    bot.infinity_polling()
