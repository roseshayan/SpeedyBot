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
import json
import shutil
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

try:
    import qrcode
except ImportError:
    qrcode = None

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

# --- DEFAULT CATALOG ---
# Plans are persisted in SQLite and can be managed from /sudoadmin.
# On first migration we seed the requested 1/2/3-user unlimited monthly offers.
DEFAULT_PLANS = [
    ("نامحدود یک‌ماهه | ۱ کاربر", 250000, 0, 30, 1, 10),
    ("نامحدود یک‌ماهه | ۲ کاربر", 300000, 0, 30, 2, 20),
    ("نامحدود یک‌ماهه | ۳ کاربر", 350000, 0, 30, 3, 30),
]

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
    _ensure_column(cursor, 'users', 'phone', 'TEXT')
    _ensure_column(cursor, 'users', 'phone_verified_at', 'INTEGER')
    _ensure_column(cursor, 'users', 'pending_discount_code', 'TEXT')

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
        ('kind', "TEXT NOT NULL DEFAULT 'NEW'"),
        ('plan_name_snapshot', 'TEXT'),
        ('plan_days_snapshot', 'INTEGER'),
        ('plan_volume_gb_snapshot', 'REAL'),
        ('plan_ip_limit_snapshot', 'INTEGER'),
        ('discount_code', 'TEXT'),
        ('discount_amount', 'INTEGER NOT NULL DEFAULT 0'),
        ('extra_volume_gb', 'REAL NOT NULL DEFAULT 0'),
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

    cursor.execute('''CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        volume_gb REAL NOT NULL DEFAULT 0,
        days INTEGER NOT NULL DEFAULT 30,
        ip_limit INTEGER NOT NULL DEFAULT 1,
        active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 100,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS volume_packs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        volume_gb REAL NOT NULL,
        price INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        sort_order INTEGER NOT NULL DEFAULT 100,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS discount_codes (
        code TEXT PRIMARY KEY COLLATE NOCASE,
        discount_type TEXT NOT NULL,
        value REAL NOT NULL,
        min_purchase INTEGER NOT NULL DEFAULT 0,
        max_uses INTEGER NOT NULL DEFAULT 0,
        per_user_limit INTEGER NOT NULL DEFAULT 1,
        expires_at INTEGER,
        active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS discount_redemptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        tx_id INTEGER NOT NULL UNIQUE,
        discount_amount INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'RESERVED',
        created_at INTEGER NOT NULL,
        applied_at INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gift_codes (
        code TEXT PRIMARY KEY COLLATE NOCASE,
        amount INTEGER NOT NULL,
        max_uses INTEGER NOT NULL DEFAULT 1,
        expires_at INTEGER,
        active INTEGER NOT NULL DEFAULT 1,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS gift_redemptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        UNIQUE(code, user_id)
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS cashback_rewards (
        tx_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        base_amount INTEGER NOT NULL,
        percent REAL NOT NULL,
        amount INTEGER NOT NULL,
        created_at INTEGER NOT NULL
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT NOT NULL DEFAULT 'ADMIN',
        added_by INTEGER,
        created_at INTEGER NOT NULL
    )''')

    # Seed catalog only once. Existing databases get the requested 3 monthly plans.
    now_seed = int(time.time())
    plan_count = cursor.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    if plan_count == 0:
        for name, price, volume_gb, days, ip_limit, sort_order in DEFAULT_PLANS:
            cursor.execute(
                "INSERT INTO plans (name, price, volume_gb, days, ip_limit, active, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)",
                (name, price, volume_gb, days, ip_limit, sort_order, now_seed, now_seed)
            )
    if ADMIN_ID:
        cursor.execute(
            "INSERT OR IGNORE INTO admins (user_id, role, added_by, created_at) VALUES (?, 'OWNER', ?, ?)",
            (ADMIN_ID, ADMIN_ID, now_seed)
        )

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
        'xui_customers_group': 'Customers',
        'xui_trial_group': 'Trial',
        'phone_verification_required': '0',
        'membership_required': '0',
        'required_channel': '',
        'required_channel_url': '',
        'cashback_percent': '0',
        'service_username_mode': 'telegram_tx',
        'automatic_backup_enabled': '1',
        'automatic_backup_interval_seconds': '86400',
        'automatic_backup_retention': '14',
        'last_automatic_backup_at': '0',
        'welcome_text': 'سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.',
        'faq_text': '📚 **راهنمای SpeedPing**\n\n• برای خرید از بخش پلان‌ها استفاده کنید.\n• لینک Subscription را همیشه نگه دارید و برای به‌روزرسانی کانفیگ‌ها Refresh کنید.\n• برای تمدید یا خرید حجم اضافه وارد حساب کاربری شوید.\n• در صورت مشکل از بخش پشتیبانی پیام بدهید.',
    }
    for key, value in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))

    now_ts = int(time.time())
    cursor.execute("UPDATE users SET created_at = COALESCE(created_at, ?), last_seen_at = COALESCE(last_seen_at, ?) WHERE created_at IS NULL OR last_seen_at IS NULL", (now_ts, now_ts))
    # Backfill historical v2.x transactions before dynamic plans existed.
    cursor.execute("UPDATE transactions SET kind = COALESCE(NULLIF(kind,''), 'NEW')")
    cursor.execute("UPDATE transactions SET plan_name_snapshot = COALESCE(plan_name_snapshot, 'پلان نامحدود (یک‌ماهه)') WHERE plan_id = 1")
    cursor.execute("UPDATE transactions SET plan_days_snapshot = COALESCE(plan_days_snapshot, 30) WHERE plan_id = 1")
    cursor.execute("UPDATE transactions SET plan_volume_gb_snapshot = COALESCE(plan_volume_gb_snapshot, 0) WHERE plan_id = 1")
    cursor.execute("UPDATE transactions SET plan_ip_limit_snapshot = COALESCE(plan_ip_limit_snapshot, 2) WHERE plan_id = 1")
    cursor.execute("UPDATE transactions SET cash_amount = price WHERE payment_method = 'CARD' AND (cash_amount IS NULL OR cash_amount = 0)")
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


def _row_to_plan(row):
    if not row:
        return None
    return {
        'id': int(row['id']),
        'name': row['name'],
        'price': int(row['price']),
        'volume': float(row['volume_gb'] or 0),
        'volume_gb': float(row['volume_gb'] or 0),
        'days': int(row['days']),
        'ip_limit': max(0, int(row['ip_limit'] or 0)),
        'active': bool(row['active']),
        'sort_order': int(row['sort_order'] or 100),
    }


def get_plan(plan_id, include_inactive=True):
    conn = _db_connect()
    sql = "SELECT * FROM plans WHERE id = ?" + ("" if include_inactive else " AND active = 1")
    row = conn.execute(sql, (int(plan_id),)).fetchone()
    conn.close()
    return _row_to_plan(row)


def get_active_plans():
    conn = _db_connect()
    rows = conn.execute("SELECT * FROM plans WHERE active = 1 ORDER BY sort_order, id").fetchall()
    conn.close()
    return [_row_to_plan(r) for r in rows]


class _PlansProxy:
    """Compatibility facade for old code while plans live in SQLite."""
    def get(self, plan_id, default=None):
        return get_plan(plan_id, include_inactive=True) or default

    def __getitem__(self, plan_id):
        plan = get_plan(plan_id, include_inactive=True)
        if not plan:
            raise KeyError(plan_id)
        return plan

    def items(self):
        return [(p['id'], p) for p in get_active_plans()]


PLANS = _PlansProxy()


def get_active_volume_packs():
    conn = _db_connect()
    rows = conn.execute("SELECT * FROM volume_packs WHERE active = 1 ORDER BY sort_order, id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_volume_pack(pack_id, include_inactive=True):
    conn = _db_connect()
    sql = "SELECT * FROM volume_packs WHERE id = ?" + ("" if include_inactive else " AND active = 1")
    row = conn.execute(sql, (int(pack_id),)).fetchone()
    conn.close()
    return dict(row) if row else None


def is_admin(user_id):
    if int(user_id) == int(ADMIN_ID):
        return True
    conn = _db_connect()
    row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (int(user_id),)).fetchone()
    conn.close()
    return bool(row)


def get_admin_ids():
    conn = _db_connect()
    rows = conn.execute("SELECT user_id FROM admins ORDER BY CASE WHEN role='OWNER' THEN 0 ELSE 1 END, created_at").fetchall()
    conn.close()
    ids = [int(r['user_id']) for r in rows]
    if ADMIN_ID and int(ADMIN_ID) not in ids:
        ids.insert(0, int(ADMIN_ID))
    return ids


def notify_admins(text, parse_mode=None, reply_markup=None):
    for admin_id in get_admin_ids():
        try:
            bot.send_message(admin_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception:
            continue


def _discount_row(code):
    if not code:
        return None
    conn = _db_connect()
    row = conn.execute("SELECT * FROM discount_codes WHERE code = ? COLLATE NOCASE", (str(code).strip(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_pending_discount(user_id, code):
    code = (code or '').strip().upper()
    row = _discount_row(code)
    now_ts = int(time.time())
    if not row or not int(row['active'] or 0):
        return False, "کد تخفیف معتبر نیست یا غیرفعال شده است."
    if row.get('expires_at') and int(row['expires_at']) <= now_ts:
        return False, "اعتبار این کد تخفیف تمام شده است."
    conn = _db_connect()
    conn.execute("UPDATE users SET pending_discount_code = ? WHERE id = ?", (row['code'], int(user_id)))
    conn.commit()
    conn.close()
    return True, f"کد تخفیف {row['code']} برای خرید بعدی شما ذخیره شد."


def _calculate_pending_discount(conn, user_id, base_price):
    user = conn.execute("SELECT pending_discount_code FROM users WHERE id = ?", (int(user_id),)).fetchone()
    code = user['pending_discount_code'] if user else None
    if not code:
        return None, 0, int(base_price)
    row = conn.execute("SELECT * FROM discount_codes WHERE code = ? COLLATE NOCASE", (code,)).fetchone()
    now_ts = int(time.time())
    if not row or not int(row['active'] or 0) or (row['expires_at'] and int(row['expires_at']) <= now_ts):
        conn.execute("UPDATE users SET pending_discount_code = NULL WHERE id = ?", (int(user_id),))
        return None, 0, int(base_price)
    if int(base_price) < int(row['min_purchase'] or 0):
        return None, 0, int(base_price)
    used_total = conn.execute("SELECT COUNT(*) AS c FROM discount_redemptions WHERE code = ? COLLATE NOCASE AND status IN ('RESERVED','APPLIED')", (code,)).fetchone()['c']
    used_user = conn.execute("SELECT COUNT(*) AS c FROM discount_redemptions WHERE code = ? COLLATE NOCASE AND user_id = ? AND status IN ('RESERVED','APPLIED')", (code, int(user_id))).fetchone()['c']
    if int(row['max_uses'] or 0) > 0 and int(used_total) >= int(row['max_uses']):
        return None, 0, int(base_price)
    if int(row['per_user_limit'] or 0) > 0 and int(used_user) >= int(row['per_user_limit']):
        return None, 0, int(base_price)
    if str(row['discount_type']).upper() == 'PERCENT':
        amount = int(round(int(base_price) * float(row['value']) / 100.0))
    else:
        amount = int(round(float(row['value'])))
    amount = max(0, min(amount, int(base_price)))
    return str(row['code']), amount, int(base_price) - amount


def _reserve_discount(conn, user_id, tx_id, code, amount):
    if not code or int(amount) <= 0:
        return
    conn.execute(
        "INSERT INTO discount_redemptions (code, user_id, tx_id, discount_amount, status, created_at) VALUES (?, ?, ?, ?, 'RESERVED', ?)",
        (code, int(user_id), int(tx_id), int(amount), int(time.time()))
    )
    conn.execute("UPDATE users SET pending_discount_code = NULL WHERE id = ?", (int(user_id),))


def _finish_discount(tx_id, applied=True):
    conn = _db_connect()
    status = 'APPLIED' if applied else 'RELEASED'
    conn.execute(
        "UPDATE discount_redemptions SET status = ?, applied_at = CASE WHEN ?='APPLIED' THEN ? ELSE applied_at END WHERE tx_id = ? AND status = 'RESERVED'",
        (status, status, int(time.time()), int(tx_id))
    )
    conn.commit()
    conn.close()


def redeem_gift_code(user_id, code):
    code = (code or '').strip().upper()
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM gift_codes WHERE code = ? COLLATE NOCASE", (code,)).fetchone()
        now_ts = int(time.time())
        if not row or not int(row['active'] or 0):
            conn.rollback(); return False, "کد هدیه معتبر نیست یا غیرفعال است."
        if row['expires_at'] and int(row['expires_at']) <= now_ts:
            conn.rollback(); return False, "اعتبار این کد هدیه تمام شده است."
        if conn.execute("SELECT 1 FROM gift_redemptions WHERE code = ? COLLATE NOCASE AND user_id = ?", (code, int(user_id))).fetchone():
            conn.rollback(); return False, "شما قبلاً این کد هدیه را استفاده کرده‌اید."
        used = conn.execute("SELECT COUNT(*) AS c FROM gift_redemptions WHERE code = ? COLLATE NOCASE", (code,)).fetchone()['c']
        if int(row['max_uses'] or 0) > 0 and int(used) >= int(row['max_uses']):
            conn.rollback(); return False, "ظرفیت استفاده از این کد هدیه تکمیل شده است."
        user = conn.execute("SELECT balance FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if not user:
            conn.execute("INSERT INTO users (id,balance,created_at,last_seen_at,is_active) VALUES (?,0,?,?,1)", (int(user_id), now_ts, now_ts))
            balance = 0
        else:
            balance = int(user['balance'] or 0)
        amount = int(row['amount'])
        new_balance = balance + amount
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, int(user_id)))
        conn.execute("INSERT INTO gift_redemptions (code,user_id,amount,created_at) VALUES (?,?,?,?)", (row['code'], int(user_id), amount, now_ts))
        conn.execute("INSERT INTO wallet_transactions (user_id,amount,balance_after,type,description,unique_key,created_at) VALUES (?,?,?,'GIFT_CODE',?,?,?)",
                     (int(user_id), amount, new_balance, f"کد هدیه {row['code']}", f"gift:{row['code']}:{user_id}", now_ts))
        conn.commit()
        return True, f"🎁 مبلغ {amount:,} تومان به کیف پول شما اضافه شد. موجودی جدید: {new_balance:,} تومان"
    except sqlite3.IntegrityError:
        conn.rollback(); return False, "این کد هدیه قبلاً استفاده شده است."
    finally:
        conn.close()


def get_cashback_percent():
    try:
        return max(0.0, min(float(get_db_setting('cashback_percent', '0')), 100.0))
    except Exception:
        return 0.0


def credit_cashback(tx_id):
    percent = get_cashback_percent()
    if percent <= 0:
        return None
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM cashback_rewards WHERE tx_id = ?", (int(tx_id),)).fetchone():
            conn.rollback(); return None
        tx = conn.execute("SELECT user_id,status,cash_amount FROM transactions WHERE id = ?", (int(tx_id),)).fetchone()
        if not tx or tx['status'] != 'APPROVED' or int(tx['cash_amount'] or 0) <= 0:
            conn.rollback(); return None
        base = int(tx['cash_amount'])
        amount = int(base * percent / 100.0)
        if amount <= 0:
            conn.rollback(); return None
        row = conn.execute("SELECT balance FROM users WHERE id = ?", (int(tx['user_id']),)).fetchone()
        balance = int(row['balance'] or 0) if row else 0
        new_balance = balance + amount
        now_ts = int(time.time())
        conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, int(tx['user_id'])))
        conn.execute("INSERT INTO cashback_rewards (tx_id,user_id,base_amount,percent,amount,created_at) VALUES (?,?,?,?,?,?)",
                     (int(tx_id), int(tx['user_id']), base, percent, amount, now_ts))
        conn.execute("INSERT INTO wallet_transactions (user_id,amount,balance_after,type,description,related_tx_id,unique_key,created_at) VALUES (?,?,?,'CASHBACK',?,?,?,?)",
                     (int(tx['user_id']), amount, new_balance, f"کش‌بک خرید #{tx_id}", int(tx_id), f"cashback:{tx_id}", now_ts))
        conn.commit()
        return {'user_id': int(tx['user_id']), 'amount': amount, 'balance': new_balance, 'percent': percent}
    finally:
        conn.close()


def create_database_backup(manual=False):
    backup_root = Path('backups') / 'auto'
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    target = backup_root / f"speedping-{stamp}.db"
    src = sqlite3.connect('speedping.db', timeout=30)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close(); src.close()
    retention = max(1, int(get_db_setting('automatic_backup_retention', '14') or 14))
    backups = sorted(backup_root.glob('speedping-*.db'), key=lambda x: x.stat().st_mtime, reverse=True)
    for old in backups[retention:]:
        try: old.unlink()
        except Exception: pass
    update_db_setting('last_automatic_backup_at', str(int(time.time())))
    return str(target)


def maybe_automatic_backup():
    if get_db_setting('automatic_backup_enabled', '1') != '1':
        return None
    try:
        interval = max(3600, int(get_db_setting('automatic_backup_interval_seconds', '86400')))
        last = int(get_db_setting('last_automatic_backup_at', '0') or 0)
    except Exception:
        interval, last = 86400, 0
    if int(time.time()) - last < interval:
        return None
    return create_database_backup()


def user_phone_verified(user_id):
    conn = _db_connect()
    row = conn.execute("SELECT phone_verified_at FROM users WHERE id = ?", (int(user_id),)).fetchone()
    conn.close()
    return bool(row and row['phone_verified_at'])


def _channel_membership_ok(user_id):
    if get_db_setting('membership_required', '0') != '1':
        return True, None
    channel = get_db_setting('required_channel', '').strip()
    if not channel:
        return False, "کانال اجباری هنوز توسط مدیریت تنظیم نشده است."
    try:
        member = bot.get_chat_member(channel, int(user_id))
        if member.status in ('member', 'administrator', 'creator'):
            return True, None
        return False, "برای خرید باید ابتدا عضو کانال SpeedPing شوید."
    except Exception as e:
        return False, "امکان بررسی عضویت کانال وجود ندارد؛ به پشتیبانی اطلاع دهید."


def purchase_gate(user_id):
    if get_db_setting('phone_verification_required', '0') == '1' and not user_phone_verified(user_id):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add(types.KeyboardButton("📱 ارسال شماره من", request_contact=True))
        kb.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
        bot.send_message(int(user_id), "📱 برای ادامه خرید، شماره تلگرام خودتان را با دکمه زیر تأیید کنید.", reply_markup=kb)
        return False
    ok, error = _channel_membership_ok(user_id)
    if not ok:
        m = types.InlineKeyboardMarkup()
        url = get_db_setting('required_channel_url', '').strip()
        if not url:
            channel = get_db_setting('required_channel', '').strip()
            if channel.startswith('@'):
                url = 'https://t.me/' + channel[1:]
        if url:
            m.add(types.InlineKeyboardButton("📢 عضویت در کانال", url=url))
        m.add(types.InlineKeyboardButton("✅ بررسی مجدد عضویت", callback_data="membership:check"))
        bot.send_message(int(user_id), f"⛔️ {error}", reply_markup=m)
        return False
    return True


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
    markup.row("🎟 کد هدیه / تخفیف", "📚 راهنما و سوالات")
    markup.row("📞 پشتیبانی")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔙 بازگشت به منوی اصلی")
    return markup

def admin_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار و گزارش فروش", callback_data="admin:stats"),
        types.InlineKeyboardButton("📦 مدیریت پلان‌ها", callback_data="admin:plans"),
        types.InlineKeyboardButton("👥 گروه‌های Sanaei", callback_data="admin:groups"),
        types.InlineKeyboardButton("🎟 کدها و پاداش", callback_data="admin:rewards"),
        types.InlineKeyboardButton("🔐 احراز و عضویت", callback_data="admin:security"),
        types.InlineKeyboardButton("👑 مدیران", callback_data="admin:admins"),
        types.InlineKeyboardButton("💾 بکاپ و عملیات", callback_data="admin:ops"),
        types.InlineKeyboardButton("🤝 همکاری در فروش", callback_data="admin:affiliate"),
        types.InlineKeyboardButton("🖥 وضعیت زنده سرور", callback_data="admin:server_status"),
        types.InlineKeyboardButton("🔔 اعلان سرویس‌ها", callback_data="admin:notifications"),
        types.InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin:broadcast"),
        types.InlineKeyboardButton("💳 تنظیمات حساب واریز", callback_data="admin:bank_config"),
        types.InlineKeyboardButton("📝 متن‌ها و راهنما", callback_data="admin:content"),
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

    welcome_text = get_db_setting('welcome_text', "سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.")
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

@bot.message_handler(content_types=['contact'])
def handle_phone_contact(message):
    contact = message.contact
    if not contact or contact.user_id != message.from_user.id:
        bot.send_message(message.chat.id, "❌ فقط شماره متعلق به حساب تلگرام خودتان قابل تأیید است.", reply_markup=main_menu())
        return
    conn = _db_connect()
    conn.execute("UPDATE users SET phone = ?, phone_verified_at = ? WHERE id = ?", (contact.phone_number, int(time.time()), int(message.from_user.id)))
    conn.commit(); conn.close()
    bot.send_message(message.chat.id, "✅ شماره شما با موفقیت تأیید شد. حالا می‌توانید خرید را ادامه دهید.", reply_markup=main_menu())


@bot.callback_query_handler(func=lambda call: call.data == 'membership:check')
def membership_check_callback(call):
    ok, error = _channel_membership_ok(call.from_user.id)
    if ok:
        bot.answer_callback_query(call.id, "عضویت شما تأیید شد ✅", show_alert=True)
        bot.send_message(call.from_user.id, "✅ عضویت تأیید شد؛ حالا خرید را دوباره انتخاب کنید.", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, error or "عضویت هنوز تأیید نشده است.", show_alert=True)


@bot.message_handler(func=lambda message: message.text == "🎟 کد هدیه / تخفیف")
def code_entry_mode(message):
    USER_STATES[message.chat.id] = 'CODE_ENTRY'
    bot.send_message(message.chat.id, "🎟 کد هدیه یا تخفیف را ارسال کنید.\n\nکد هدیه همان لحظه کیف پول را شارژ می‌کند؛ کد تخفیف روی خرید بعدی اعمال می‌شود.", reply_markup=back_menu())


@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'CODE_ENTRY' and bool(message.text))
def process_user_code(message):
    if message.text == "🔙 بازگشت به منوی اصلی":
        go_to_main_menu(message); return
    code = (message.text or '').strip().upper()
    # Gift codes take precedence.
    conn = _db_connect()
    gift = conn.execute("SELECT 1 FROM gift_codes WHERE code = ? COLLATE NOCASE", (code,)).fetchone()
    conn.close()
    if gift:
        ok, text = redeem_gift_code(message.from_user.id, code)
        USER_STATES[message.chat.id] = None
        bot.send_message(message.chat.id, ("✅ " if ok else "❌ ") + text, reply_markup=main_menu())
        return
    ok, text = set_pending_discount(message.from_user.id, code)
    USER_STATES[message.chat.id] = None
    bot.send_message(message.chat.id, ("✅ " if ok else "❌ ") + text, reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "📚 راهنما و سوالات")
def show_faq(message):
    USER_STATES[message.chat.id] = None
    bot.send_message(message.chat.id, get_db_setting('faq_text', 'راهنما هنوز تنظیم نشده است.'), parse_mode="Markdown", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "🛍 مشاهده و خرید پلان‌ها")
def show_plans(message):
    USER_STATES[message.chat.id] = None
    user_id = message.from_user.id
    balance = get_user_balance(user_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    plan_lines = []
    active_plans = get_active_plans()
    for info in active_plans:
        plan_id = int(info['id'])
        volume_text = "نامحدود" if float(info['volume'] or 0) <= 0 else f"{float(info['volume']):g} گیگ"
        ip_text = f"{int(info['ip_limit'])} کاربر/IP" if int(info['ip_limit']) > 0 else "بدون IP Limit"
        plan_lines.append(
            f"• **{info['name']}**\n  💵 `{info['price']:,}` تومان | 📦 {volume_text} | 📅 {int(info['days'])} روز | 👥 {ip_text}"
        )
        markup.add(types.InlineKeyboardButton(
            text=f"💳 خرید {info['name']} — {info['price']:,}",
            callback_data=f"buy:{plan_id}"
        ))
        if balance >= info['price']:
            markup.add(types.InlineKeyboardButton(
                text=f"👛 پرداخت از کیف پول — {info['name']}",
                callback_data=f"walletbuy:{plan_id}"
            ))
    if not active_plans:
        bot.send_message(message.chat.id, "⛔️ در حال حاضر پلن فعالی برای فروش وجود ندارد.", reply_markup=main_menu())
        return
    bot.send_message(
        message.chat.id,
        f"🛒 **لیست پلان‌های SpeedPing**\n\n" + "\n\n".join(plan_lines) +
        f"\n\n👛 موجودی کیف پول شما: `{balance:,} تومان`\n\n💡 تعداد کاربر هر پلن همان IP Limit سرویس روی پنل Sanaei است.",
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
    if not purchase_gate(user_id):
        return
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

def _release_stale_checkouts(user_id=None):
    cutoff = int(time.time()) - 3600
    conn = _db_connect()
    if user_id is None:
        rows = conn.execute("SELECT id FROM transactions WHERE status='AWAITING_RECEIPT' AND created_at < ?", (cutoff,)).fetchall()
    else:
        rows = conn.execute("SELECT id FROM transactions WHERE user_id=? AND status='AWAITING_RECEIPT' AND created_at < ?", (int(user_id), cutoff)).fetchall()
    for row in rows:
        conn.execute("UPDATE transactions SET status='CANCELLED', last_error='checkout expired' WHERE id=?", (int(row['id']),))
        conn.execute("UPDATE discount_redemptions SET status='RELEASED' WHERE tx_id=? AND status='RESERVED'", (int(row['id']),))
    conn.commit(); conn.close()


def _product_snapshot(plan):
    return {
        'plan_id': int(plan.get('id', 0)),
        'name': str(plan.get('name') or 'SpeedPing'),
        'price': int(plan.get('price') or 0),
        'days': int(plan.get('days') or 0),
        'volume': float(plan.get('volume', plan.get('volume_gb', 0)) or 0),
        'ip_limit': int(plan.get('ip_limit') or 0),
    }


def _create_checkout_transaction(user_id, plan, payment_method, kind='NEW', target_service_email=None, extra_volume_gb=0):
    plan = _product_snapshot(plan)
    _release_stale_checkouts(user_id)
    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        code, discount_amount, final_price = _calculate_pending_discount(conn, int(user_id), int(plan['price']))
        wallet_used = final_price if payment_method == 'WALLET' else 0
        cash_amount = final_price if payment_method == 'CARD' else 0
        if payment_method == 'WALLET':
            row = conn.execute("SELECT balance FROM users WHERE id = ?", (int(user_id),)).fetchone()
            balance = int(row['balance'] or 0) if row else 0
            if balance < final_price:
                conn.rollback()
                return None, f"موجودی کافی نیست. موجودی فعلی: {balance:,} تومان"
        status = 'PROCESSING' if payment_method == 'WALLET' else 'AWAITING_RECEIPT'
        now_ts = int(time.time())
        cur = conn.execute(
            """INSERT INTO transactions
               (user_id, photo_id, plan_id, status, price, payment_method, wallet_used, cash_amount, created_at,
                service_email, kind, plan_name_snapshot, plan_days_snapshot, plan_volume_gb_snapshot,
                plan_ip_limit_snapshot, discount_code, discount_amount, extra_volume_gb)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (int(user_id), int(plan['plan_id']), status, int(final_price), payment_method, int(wallet_used), int(cash_amount), now_ts,
             target_service_email, kind, plan['name'], int(plan['days']), float(plan['volume']), int(plan['ip_limit']),
             code, int(discount_amount), float(extra_volume_gb or 0))
        )
        tx_id = int(cur.lastrowid)
        if kind == 'NEW' and not target_service_email:
            username_mode = get_db_setting('service_username_mode', 'telegram_tx')
            if username_mode == 'random':
                service_email = f"speedping_{secrets.token_hex(6)}"
            else:
                service_email = f"speedping_{int(user_id)}_{tx_id}"
            conn.execute("UPDATE transactions SET service_email = ? WHERE id = ?", (service_email, tx_id))
        if code and discount_amount > 0:
            _reserve_discount(conn, int(user_id), tx_id, code, discount_amount)
        if payment_method == 'WALLET':
            row = conn.execute("SELECT balance FROM users WHERE id = ?", (int(user_id),)).fetchone()
            balance = int(row['balance'] or 0)
            new_balance = balance - final_price
            conn.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, int(user_id)))
            conn.execute(
                """INSERT INTO wallet_transactions
                   (user_id, amount, balance_after, type, description, related_tx_id, unique_key, created_at)
                   VALUES (?, ?, ?, 'PURCHASE', ?, ?, ?, ?)""",
                (int(user_id), -int(final_price), new_balance, f"{kind}: {plan['name']}", tx_id, f"wallet_purchase:{tx_id}", now_ts)
            )
        conn.commit()
        return {
            'tx_id': tx_id,
            'price': int(final_price),
            'discount': int(discount_amount),
            'discount_code': code,
            'name': plan['name'],
        }, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()


def _checkout_caption(tx_id):
    conn = _db_connect()
    tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (int(tx_id),)).fetchone()
    conn.close()
    if not tx:
        return "تراکنش نامعتبر"
    kind_names = {'NEW': 'خرید سرویس', 'RENEWAL': 'تمدید سرویس', 'VOLUME': 'خرید حجم اضافه'}
    return (
        f"🔔 **{kind_names.get(tx['kind'], 'تراکنش')} جدید!**\n\n"
        f"👤 کاربر: `{int(tx['user_id'])}`\n"
        f"📦 مورد: {tx['plan_name_snapshot'] or '-'}\n"
        f"💵 مبلغ: **{int(tx['price'] or 0):,} تومان**\n"
        f"🎟 تخفیف: **{int(tx['discount_amount'] or 0):,} تومان**"
        + (f" (`{tx['discount_code']}`)" if tx['discount_code'] else "") + "\n"
        f"✉️ سرویس: `{tx['service_email'] or '-'}`\n"
        f"🆔 کد تراکنش: `{int(tx['id'])}`"
    )


def _send_receipt_to_admins(tx_id, photo_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"admin:approve:{tx_id}"),
        types.InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:reject:{tx_id}")
    )
    caption = _checkout_caption(tx_id)
    for admin_id in get_admin_ids():
        try:
            bot.send_photo(admin_id, photo_id, caption=caption, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            continue


def _start_card_checkout(chat_id, user_id, plan, kind='NEW', target_service_email=None, extra_volume_gb=0):
    result, error = _create_checkout_transaction(user_id, plan, 'CARD', kind, target_service_email, extra_volume_gb)
    if not result:
        bot.send_message(chat_id, f"❌ خطا در ایجاد تراکنش: {error}", reply_markup=main_menu())
        return
    card_num = get_db_setting('card_number')
    card_holder = get_db_setting('card_holder')
    bank_name = get_db_setting('bank_name')
    discount_line = f"\n🎟 تخفیف اعمال‌شده: **{result['discount']:,} تومان**" if result['discount'] else ""
    msg = bot.send_message(
        chat_id,
        f"💵 **{result['name']}**\n\n"
        f"💳 مبلغ قابل پرداخت: **{result['price']:,} تومان**{discount_line}\n\n"
        f"🏦 بانک: *{bank_name}*\n💳 شماره کارت:\n`{card_num}`\n👤 به نام: *{card_holder}*\n\n"
        f"🆔 تراکنش: `{result['tx_id']}`\n📸 پس از واریز، فقط عکس فیش را ارسال کنید.",
        parse_mode="Markdown", reply_markup=back_menu()
    )
    bot.register_next_step_handler(msg, process_receipt, result['tx_id'])


def _start_wallet_checkout(call, plan, kind='NEW', target_service_email=None, extra_volume_gb=0):
    result, error = _create_checkout_transaction(call.from_user.id, plan, 'WALLET', kind, target_service_email, extra_volume_gb)
    if not result:
        bot.answer_callback_query(call.id, error or "خطا در خرید کیف پول", show_alert=True)
        return
    bot.answer_callback_query(call.id, "پرداخت از کیف پول ثبت شد ✅")
    bot.send_message(
        call.from_user.id,
        f"👛 مبلغ **{result['price']:,} تومان** از کیف پول شما کسر شد.\n⚡️ عملیات در حال انجام است...\n🆔 تراکنش: `{result['tx_id']}`",
        parse_mode="Markdown", reply_markup=main_menu()
    )
    finalize_service_transaction(result['tx_id'])


@bot.callback_query_handler(func=lambda call: call.data.startswith('buy:'))
def handle_buy_plan(call):
    plan_id = int(call.data.split(':')[1])
    plan = get_plan(plan_id, include_inactive=False)
    if not plan:
        bot.answer_callback_query(call.id, "پلن نامعتبر یا غیرفعال است.", show_alert=True); return
    if not purchase_gate(call.from_user.id):
        bot.answer_callback_query(call.id, "ابتدا شرایط خرید را تکمیل کنید.", show_alert=True); return
    bot.answer_callback_query(call.id)
    _start_card_checkout(call.message.chat.id, call.from_user.id, plan)


@bot.callback_query_handler(func=lambda call: call.data.startswith('walletbuy:'))
def handle_wallet_buy(call):
    plan_id = int(call.data.split(':')[1])
    plan = get_plan(plan_id, include_inactive=False)
    if not plan:
        bot.answer_callback_query(call.id, "پلن نامعتبر یا غیرفعال است.", show_alert=True); return
    if not purchase_gate(call.from_user.id):
        bot.answer_callback_query(call.id, "ابتدا شرایط خرید را تکمیل کنید.", show_alert=True); return
    _start_wallet_checkout(call, plan)


def process_receipt(message, tx_id):
    conn = _db_connect()
    tx = conn.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (int(tx_id), int(message.from_user.id))).fetchone()
    if not tx or tx['status'] != 'AWAITING_RECEIPT':
        conn.close()
        bot.send_message(message.chat.id, "❌ این تراکنش معتبر نیست یا قبلاً ثبت شده است.", reply_markup=main_menu()); return
    if message.text == "🔙 بازگشت به منوی اصلی":
        conn.execute("UPDATE transactions SET status='CANCELLED' WHERE id=?", (int(tx_id),))
        conn.execute("UPDATE discount_redemptions SET status='RELEASED' WHERE tx_id=? AND status='RESERVED'", (int(tx_id),))
        conn.commit(); conn.close()
        go_to_main_menu(message); return
    if not message.photo:
        conn.close()
        retry_msg = bot.send_message(message.chat.id, "❌ فقط عکس یا اسکرین‌شات فیش را ارسال کنید. تراکنش شما هنوز باز است.", reply_markup=back_menu())
        bot.register_next_step_handler(retry_msg, process_receipt, tx_id)
        return
    photo_id = message.photo[-1].file_id
    conn.execute("UPDATE transactions SET photo_id=?, status='PENDING' WHERE id=?", (photo_id, int(tx_id)))
    conn.commit(); conn.close()
    bot.send_message(message.chat.id, "✅ فیش دریافت شد و برای مدیریت ارسال شد. پس از تأیید، عملیات به‌صورت خودکار انجام می‌شود.", reply_markup=main_menu())
    _send_receipt_to_admins(tx_id, photo_id)


# --- ACCOUNT SECTION ---
@bot.message_handler(func=lambda message: message.text == "👤 حساب کاربری")
def show_account(message):
    USER_STATES[message.chat.id] = None
    user_id = message.chat.id

    conn = _db_connect()
    approved_txs = conn.execute(
        "SELECT id, service_email, payment_method, plan_name_snapshot FROM transactions WHERE user_id = ? AND status = 'APPROVED' AND kind = 'NEW' ORDER BY id DESC",
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
            label = (tx['plan_name_snapshot'] or f"سرویس #{tx_id}")[:45]
            markup.add(types.InlineKeyboardButton(text=f"📦 {label}", callback_data=f"view:status:{tx_id}"))
    else:
        msg_text += "\n❌ در حال حاضر سرویس فعالی ندارید."

    markup.row(
        types.InlineKeyboardButton("🧾 تاریخچه خرید", callback_data="account:purchases"),
        types.InlineKeyboardButton("📜 تاریخچه کیف پول", callback_data="ref:wallet_history")
    )
    bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'account:purchases')
def account_purchase_history(call):
    user_id = int(call.from_user.id)
    conn = _db_connect()
    rows = conn.execute(
        """SELECT id, kind, plan_name_snapshot, price, discount_amount, payment_method, status, created_at, approved_at
           FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 15""",
        (user_id,)
    ).fetchall()
    trial = conn.execute("SELECT status, created_at, activated_at FROM trial_services WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    bot.answer_callback_query(call.id)
    if not rows and not trial:
        bot.send_message(user_id, "🧾 هنوز سابقه خرید یا تستی ثبت نشده است.")
        return
    kind_label = {'NEW':'خرید','RENEWAL':'تمدید','VOLUME':'حجم اضافه'}
    status_label = {'APPROVED':'✅ موفق','PENDING':'⏳ در انتظار','PROCESSING':'⚙️ پردازش','ISSUE':'⚠️ بررسی','REJECTED':'❌ رد','REFUNDED':'↩️ بازپرداخت','CANCELLED':'🚫 لغو','AWAITING_RECEIPT':'📷 منتظر فیش'}
    lines = ["🧾 **تاریخچه خرید و سرویس**\n"]
    if trial:
        lines.append(f"🎁 تست رایگان — `{trial['status']}`")
    for row in rows:
        dt = datetime.fromtimestamp(int(row['created_at'] or 0)).strftime('%Y-%m-%d %H:%M') if row['created_at'] else '-'
        lines.append(
            f"• `#{row['id']}` {kind_label.get(row['kind'], row['kind'])} — **{row['plan_name_snapshot'] or '-'}**\n"
            f"  {status_label.get(row['status'], row['status'])} | `{int(row['price'] or 0):,}` تومان | {dt}"
        )
    bot.send_message(user_id, "\n".join(lines), parse_mode="Markdown")


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
    send_xui_status(user_id, user_email, tx_id)


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


def send_xui_status(user_id, user_email, service_tx_id=None):
    
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
                
            sub_id = _get_client_subscription_id(user_email, headers, request_proxies, data)
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
                markup.row(
                    types.InlineKeyboardButton(text="🌐 لینک سابسکریپشن", callback_data=f"getlinks:sub:{sub_id}"),
                    types.InlineKeyboardButton(text="📷 QR سابسکریپشن", callback_data=f"getqr:sub:{sub_id}")
                )
            markup.row(types.InlineKeyboardButton(text="🔑 دریافت کانفیگ‌های مستقیم", callback_data=f"getlinks:dir:{user_email}"))
            if service_tx_id:
                markup.row(types.InlineKeyboardButton(text="♻️ تمدید سرویس", callback_data=f"service:renew:{service_tx_id}"))
                if total_bytes > 0 and get_active_volume_packs():
                    markup.row(types.InlineKeyboardButton(text="➕ خرید حجم اضافه", callback_data=f"service:volume:{service_tx_id}"))
            
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('getqr:sub:'))
def handle_subscription_qr(call):
    sub_id = call.data.split(':', 2)[2]
    url = _subscription_url(sub_id)
    if qrcode is None:
        bot.answer_callback_query(call.id, "کتابخانه QR روی سرور نصب نیست.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "در حال ساخت QR...")
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    bot.send_photo(call.from_user.id, buf, caption="📷 QR لینک Subscription شما\n\nاین QR را فقط برای دستگاه‌های خودتان استفاده کنید.")


def _owned_service_tx(user_id, tx_id):
    conn = _db_connect()
    row = conn.execute(
        "SELECT * FROM transactions WHERE id=? AND user_id=? AND status='APPROVED' AND kind='NEW'",
        (int(tx_id), int(user_id))
    ).fetchone()
    conn.close()
    return row


@bot.callback_query_handler(func=lambda call: call.data.startswith('service:renew:'))
def service_renew_menu(call):
    tx_id = int(call.data.split(':')[2])
    tx = _owned_service_tx(call.from_user.id, tx_id)
    if not tx:
        bot.answer_callback_query(call.id, "سرویس پیدا نشد.", show_alert=True); return
    if not purchase_gate(call.from_user.id):
        bot.answer_callback_query(call.id, "ابتدا شرایط خرید را تکمیل کنید.", show_alert=True); return
    plans = get_active_plans()
    m = types.InlineKeyboardMarkup(row_width=1)
    for plan in plans:
        m.add(types.InlineKeyboardButton(
            f"💳 تمدید با {plan['name']} — {plan['price']:,} تومان",
            callback_data=f"renewcard:{tx_id}:{plan['id']}"
        ))
        if get_user_balance(call.from_user.id) >= plan['price']:
            m.add(types.InlineKeyboardButton(
                f"👛 کیف پول | {plan['name']}",
                callback_data=f"renewwallet:{tx_id}:{plan['id']}"
            ))
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "♻️ **تمدید سرویس**\n\nپلن تمدید را انتخاب کنید. تعداد کاربر/IP Limit نیز مطابق پلن انتخابی به‌روزرسانی می‌شود.", parse_mode="Markdown", reply_markup=m)


@bot.callback_query_handler(func=lambda call: call.data.startswith('renewcard:'))
def renew_card_checkout(call):
    _, tx_id, plan_id = call.data.split(':')
    tx = _owned_service_tx(call.from_user.id, int(tx_id))
    plan = get_plan(int(plan_id), include_inactive=False)
    if not tx or not plan:
        bot.answer_callback_query(call.id, "سرویس یا پلن نامعتبر است.", show_alert=True); return
    if not purchase_gate(call.from_user.id): return
    bot.answer_callback_query(call.id)
    _start_card_checkout(call.from_user.id, call.from_user.id, plan, 'RENEWAL', tx['service_email'])


@bot.callback_query_handler(func=lambda call: call.data.startswith('renewwallet:'))
def renew_wallet_checkout(call):
    _, tx_id, plan_id = call.data.split(':')
    tx = _owned_service_tx(call.from_user.id, int(tx_id))
    plan = get_plan(int(plan_id), include_inactive=False)
    if not tx or not plan:
        bot.answer_callback_query(call.id, "سرویس یا پلن نامعتبر است.", show_alert=True); return
    if not purchase_gate(call.from_user.id): return
    _start_wallet_checkout(call, plan, 'RENEWAL', tx['service_email'])


@bot.callback_query_handler(func=lambda call: call.data.startswith('service:volume:'))
def service_volume_menu(call):
    tx_id = int(call.data.split(':')[2])
    tx = _owned_service_tx(call.from_user.id, tx_id)
    if not tx:
        bot.answer_callback_query(call.id, "سرویس پیدا نشد.", show_alert=True); return
    packs = get_active_volume_packs()
    if not packs:
        bot.answer_callback_query(call.id, "در حال حاضر بسته حجم اضافه فعالی وجود ندارد.", show_alert=True); return
    m = types.InlineKeyboardMarkup(row_width=1)
    balance = get_user_balance(call.from_user.id)
    for pack in packs:
        m.add(types.InlineKeyboardButton(
            f"💳 {pack['name']} — {int(pack['price']):,} تومان",
            callback_data=f"volcard:{tx_id}:{int(pack['id'])}"
        ))
        if balance >= int(pack['price']):
            m.add(types.InlineKeyboardButton(
                f"👛 کیف پول | {pack['name']}",
                callback_data=f"volwallet:{tx_id}:{int(pack['id'])}"
            ))
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "➕ **خرید حجم اضافه**\nبسته موردنظر را انتخاب کنید:", parse_mode="Markdown", reply_markup=m)


def _pack_as_product(pack):
    return {'id': 0, 'name': pack['name'], 'price': int(pack['price']), 'days': 0, 'volume': float(pack['volume_gb']), 'ip_limit': 0}


@bot.callback_query_handler(func=lambda call: call.data.startswith('volcard:'))
def volume_card_checkout(call):
    _, tx_id, pack_id = call.data.split(':')
    tx = _owned_service_tx(call.from_user.id, int(tx_id))
    pack = get_volume_pack(int(pack_id), include_inactive=False)
    if not tx or not pack:
        bot.answer_callback_query(call.id, "سرویس یا بسته نامعتبر است.", show_alert=True); return
    if not purchase_gate(call.from_user.id): return
    bot.answer_callback_query(call.id)
    _start_card_checkout(call.from_user.id, call.from_user.id, _pack_as_product(pack), 'VOLUME', tx['service_email'], float(pack['volume_gb']))


@bot.callback_query_handler(func=lambda call: call.data.startswith('volwallet:'))
def volume_wallet_checkout(call):
    _, tx_id, pack_id = call.data.split(':')
    tx = _owned_service_tx(call.from_user.id, int(tx_id))
    pack = get_volume_pack(int(pack_id), include_inactive=False)
    if not tx or not pack:
        bot.answer_callback_query(call.id, "سرویس یا بسته نامعتبر است.", show_alert=True); return
    if not purchase_gate(call.from_user.id): return
    _start_wallet_checkout(call, _pack_as_product(pack), 'VOLUME', tx['service_email'], float(pack['volume_gb']))


# --- SUPPORT SYSTEM ---
@bot.message_handler(func=lambda message: message.text == "📞 پشتیبانی")
def support_mode(message):
    USER_STATES[message.chat.id] = 'SUPPORT'
    bot.send_message(message.chat.id, "📞 **بخش پشتیبانی SpeedPing**\n\nپیام خود را ارسال کنید. مدیریت به زودی پاسخ خواهد داد.", reply_markup=back_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message is not None and is_admin(message.from_user.id))
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
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, "🔎 در حال تست Read-only اتصال 3x-ui...")
    bot.send_message(
        message.chat.id,
        "🧪 نتیجه تست 3x-ui:\n\n" + _run_xui_diagnostic() +
        "\n\nاین تست هیچ کاربر یا Inboundی را تغییر نمی‌دهد."
    )


@bot.message_handler(commands=['sudoadmin'])
def super_admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ شما به این منو دسترسی ندارید.")
        return
    bot.send_message(message.chat.id, "🚀 **به پنل مدیریت ارشد SpeedPing خوش آمدید**\nتنظیمات مورد نظر را انتخاب کنید:", reply_markup=admin_main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def handle_admin_panel_callbacks(call):
    if not is_admin(call.from_user.id):
        return
        
    action = call.data.split(':')[1]
    admin_chat = call.message.chat.id
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
        new_sales = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='APPROVED' AND kind='NEW'").fetchone()['c']
        renewals = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='APPROVED' AND kind='RENEWAL'").fetchone()['c']
        volume_sales = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='APPROVED' AND kind='VOLUME'").fetchone()['c']
        day_start = int(time.time()) - (int(time.time()) % 86400)
        today_sales = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='APPROVED' AND approved_at>=?", (day_start,)).fetchone()['c']
        today_revenue = conn.execute("SELECT COALESCE(SUM(cash_amount),0) AS s FROM transactions WHERE status='APPROVED' AND approved_at>=?", (day_start,)).fetchone()['s']
        total_trials_count = conn.execute("SELECT COUNT(*) AS c FROM trial_services WHERE status IN ('ACTIVE','EXPIRED')").fetchone()['c']
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
            f"📦 عملیات مالی موفق: `{int(total_sales_count)} عدد`\n"
            f"  ├ خرید جدید: `{int(new_sales)}` | تمدید: `{int(renewals)}` | حجم اضافه: `{int(volume_sales)}`\n"
            f"📅 امروز: `{int(today_sales)}` عملیات | `{int(today_revenue):,}` تومان دریافت نقدی\n"
            f"🎁 کل تست‌های صادرشده: `{int(total_trials_count)} عدد`\n"
            f"🤝 کاربران ورودی از معرفی: `{int(referrals)} نفر`\n"
            f"💰 پورسانت پرداخت‌شده: `{int(commissions):,} تومان`\n"
            f"💵 ارزش کل فروش: `{int(gross_sales):,} تومان`\n"
            f"🏦 دریافت نقدی/کارت: `{int(cash_revenue):,} تومان`\n"
            f"👛 فروش از کیف پول: `{int(wallet_sales):,} تومان`\n"
            f"⚠️ تراکنش نیازمند بررسی: `{int(issues)} عدد`"
        )
        try:
            live_groups = _xui_list_groups()
            live_online = _xui_online_emails()
            stats_text += f"\n\n🌐 **پنل Sanaei زنده**\n🟢 آنلاین: `{len(live_online)}` کلاینت\n👥 Groups: `{len(live_groups)}` دسته"
        except Exception:
            stats_text += "\n\n🌐 آمار زنده پنل در این لحظه قابل دریافت نبود."
        bot.send_message(admin_chat, stats_text, parse_mode="Markdown")

    elif action == "plans":
        conn = _db_connect()
        plans = conn.execute("SELECT * FROM plans ORDER BY sort_order,id").fetchall()
        packs = conn.execute("SELECT * FROM volume_packs ORDER BY sort_order,id").fetchall()
        conn.close()
        lines = ["📦 **مدیریت پلان‌ها**\n"]
        for row in plans:
            vol = "نامحدود" if float(row['volume_gb'] or 0) <= 0 else f"{float(row['volume_gb']):g}GB"
            lines.append(f"`#{row['id']}` {'🟢' if row['active'] else '🔴'} **{row['name']}** — {int(row['price']):,} تومان — {vol} — {int(row['days'])} روز — IP `{int(row['ip_limit'])}`")
        if packs:
            lines.append("\n➕ **بسته‌های حجم اضافه:**")
            for row in packs:
                lines.append(f"`V#{row['id']}` {'🟢' if row['active'] else '🔴'} {row['name']} — {float(row['volume_gb']):g}GB — {int(row['price']):,} تومان")
        else:
            lines.append("\n➕ بسته حجم اضافه‌ای تعریف نشده است.")
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("➕ افزودن پلان", callback_data="admin:plan_add"),
            types.InlineKeyboardButton("✏️ ویرایش پلان", callback_data="admin:plan_edit"),
            types.InlineKeyboardButton("⏯ فعال/غیرفعال پلان", callback_data="admin:plan_toggle"),
            types.InlineKeyboardButton("➕ افزودن بسته حجم", callback_data="admin:volume_add"),
            types.InlineKeyboardButton("⏯ فعال/غیرفعال حجم", callback_data="admin:volume_toggle"),
            types.InlineKeyboardButton("🔤 روش نام‌گذاری سرویس", callback_data="admin:username_mode")
        )
        bot.send_message(admin_chat, "\n".join(lines), parse_mode="Markdown", reply_markup=m)

    elif action == "plan_add":
        msg = bot.send_message(admin_chat, "➕ پلان جدید را با این فرمت بفرستید:\n`نام | قیمت تومان | حجم GB (0=نامحدود) | روز | IP Limit`\nمثال:\n`سه‌ماهه دوکاربره | 750000 | 0 | 90 | 2`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_plan_add)

    elif action == "plan_edit":
        msg = bot.send_message(admin_chat, "✏️ ویرایش پلان:\n`ID | نام | قیمت | حجمGB | روز | IP Limit`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_plan_edit)

    elif action == "plan_toggle":
        msg = bot.send_message(admin_chat, "⏯ ID پلان را بفرستید. مثال: `2`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_plan_toggle)

    elif action == "volume_add":
        msg = bot.send_message(admin_chat, "➕ بسته حجم اضافه:\n`نام | حجمGB | قیمت تومان`\nمثال: `20 گیگ اضافه | 20 | 90000`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_volume_add)

    elif action == "volume_toggle":
        msg = bot.send_message(admin_chat, "⏯ ID بسته حجم را بفرستید.")
        bot.register_next_step_handler(msg, process_admin_volume_toggle)

    elif action == "username_mode":
        current = get_db_setting('service_username_mode','telegram_tx')
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(
            types.InlineKeyboardButton("🆔 Telegram ID + Transaction", callback_data="admin:username_deterministic"),
            types.InlineKeyboardButton("🎲 Random خصوصی", callback_data="admin:username_random")
        )
        bot.send_message(admin_chat, f"🔤 **روش ساخت نام کاربری سرویس**\n\nحالت فعلی: `{current}`\n\nتغییر فقط روی سرویس‌های جدید اثر دارد.", parse_mode="Markdown", reply_markup=m)

    elif action == "username_deterministic":
        update_db_setting('service_username_mode','telegram_tx')
        bot.answer_callback_query(call.id,"ذخیره شد ✅")
        bot.send_message(admin_chat,"✅ نام سرویس‌های جدید بر اساس Telegram ID و شماره تراکنش ساخته می‌شود.")

    elif action == "username_random":
        update_db_setting('service_username_mode','random')
        bot.answer_callback_query(call.id,"ذخیره شد ✅")
        bot.send_message(admin_chat,"✅ برای سرویس‌های جدید نام تصادفی و غیرقابل حدس ساخته می‌شود.")

    elif action == "groups":
        bot.answer_callback_query(call.id, "در حال استعلام Groups پنل...")
        try:
            groups = _xui_list_groups()
            lines = [f"👥 **Groups زنده پنل Sanaei: {len(groups)} دسته**\n"]
            for g in groups:
                lines.append(f"• **{g.get('name','-')}** — `{int(g.get('clientCount') or 0)}` کلاینت")
            lines.append(f"\n🎯 مشتریان ربات → `{get_db_setting('xui_customers_group','Customers')}`")
            lines.append(f"🎁 تست‌ها → `{get_db_setting('xui_trial_group','Trial')}`")
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(types.InlineKeyboardButton("🧩 ساخت Groups لازم + همگام‌سازی", callback_data="admin:groups_reconcile"))
            bot.send_message(admin_chat, "\n".join(lines), parse_mode="Markdown", reply_markup=m)
        except Exception as e:
            bot.send_message(admin_chat, f"❌ دریافت Groups خطا داد:\n`{str(e)[:800]}`", parse_mode="Markdown")

    elif action == "groups_reconcile":
        bot.answer_callback_query(call.id, "در حال همگام‌سازی...")
        try:
            result = reconcile_service_groups()
            text = f"✅ همگام‌سازی Groups تمام شد.\nکلاینت‌های به‌روزشده: **{result['updated']}**"
            if result['errors']:
                text += f"\n⚠️ خطاها: **{len(result['errors'])}**\n" + "\n".join(result['errors'][:8])
            bot.send_message(admin_chat, text, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(admin_chat, f"❌ همگام‌سازی Groupها خطا داد: `{str(e)[:700]}`", parse_mode="Markdown")

    elif action == "rewards":
        conn = _db_connect()
        discounts = conn.execute("SELECT COUNT(*) AS c FROM discount_codes WHERE active=1").fetchone()['c']
        gifts = conn.execute("SELECT COUNT(*) AS c FROM gift_codes WHERE active=1").fetchone()['c']
        cashbacks = conn.execute("SELECT COALESCE(SUM(amount),0) AS s FROM cashback_rewards").fetchone()['s']
        conn.close()
        text = (
            "🎟 **کدها و پاداش‌ها**\n\n"
            f"کش‌بک فعلی: **{get_cashback_percent():g}٪** از پرداخت نقدی\n"
            f"کد تخفیف فعال: **{int(discounts)}**\n"
            f"کد هدیه فعال: **{int(gifts)}**\n"
            f"کش‌بک پرداخت‌شده: **{int(cashbacks):,} تومان**"
        )
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("💸 تغییر کش‌بک", callback_data="admin:cashback_percent"),
            types.InlineKeyboardButton("🏷 ساخت کد تخفیف", callback_data="admin:discount_add"),
            types.InlineKeyboardButton("🎁 ساخت کد هدیه", callback_data="admin:gift_add"),
            types.InlineKeyboardButton("⏯ کد تخفیف", callback_data="admin:discount_toggle"),
            types.InlineKeyboardButton("⏯ کد هدیه", callback_data="admin:gift_toggle")
        )
        bot.send_message(admin_chat, text, parse_mode="Markdown", reply_markup=m)

    elif action == "cashback_percent":
        msg = bot.send_message(admin_chat, "💸 درصد کش‌بک را بین 0 تا 100 بفرستید. `0` یعنی خاموش.", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_cashback_percent)

    elif action == "discount_add":
        msg = bot.send_message(admin_chat, "🏷 کد تخفیف:\n`CODE | percent/fixed | مقدار | حداقل خرید | حداکثر استفاده | روز اعتبار`\nمثال: `WELCOME20 | percent | 20 | 200000 | 100 | 30`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_discount_add)

    elif action == "gift_add":
        msg = bot.send_message(admin_chat, "🎁 کد هدیه:\n`CODE | مبلغ کیف پول | حداکثر استفاده | روز اعتبار`\nمثال: `GIFT50 | 50000 | 20 | 30`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_gift_add)

    elif action == "discount_toggle":
        msg = bot.send_message(admin_chat, "🏷 کد تخفیفی که باید فعال/غیرفعال شود را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_discount_toggle)

    elif action == "gift_toggle":
        msg = bot.send_message(admin_chat, "🎁 کد هدیه‌ای که باید فعال/غیرفعال شود را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_gift_toggle)

    elif action == "security":
        phone = get_db_setting('phone_verification_required','0') == '1'
        member = get_db_setting('membership_required','0') == '1'
        channel = get_db_setting('required_channel','') or 'تنظیم نشده'
        text = f"🔐 **احراز و عضویت اجباری**\n\n📱 تأیید شماره: {'🟢 فعال' if phone else '🔴 غیرفعال'}\n📢 عضویت کانال: {'🟢 فعال' if member else '🔴 غیرفعال'}\nکانال: `{channel}`"
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(
            types.InlineKeyboardButton("📱 روشن/خاموش شماره", callback_data="admin:phone_toggle"),
            types.InlineKeyboardButton("📢 روشن/خاموش عضویت", callback_data="admin:membership_toggle"),
            types.InlineKeyboardButton("⚙️ تنظیم کانال", callback_data="admin:channel_set")
        )
        bot.send_message(admin_chat, text, parse_mode="Markdown", reply_markup=m)

    elif action == "phone_toggle":
        new = '0' if get_db_setting('phone_verification_required','0') == '1' else '1'
        update_db_setting('phone_verification_required', new)
        bot.answer_callback_query(call.id, "تغییر کرد ✅")
        bot.send_message(admin_chat, f"📱 تأیید شماره {'فعال شد' if new=='1' else 'غیرفعال شد'}.")

    elif action == "membership_toggle":
        new = '0' if get_db_setting('membership_required','0') == '1' else '1'
        update_db_setting('membership_required', new)
        bot.answer_callback_query(call.id, "تغییر کرد ✅")
        bot.send_message(admin_chat, f"📢 عضویت اجباری {'فعال شد' if new=='1' else 'غیرفعال شد'}.")

    elif action == "channel_set":
        msg = bot.send_message(admin_chat, "کانال را بفرستید:\n`@channel | https://t.me/channel`\nبرای کانال خصوصی می‌توانید Chat ID عددی و لینک دعوت را بدهید.", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_channel_set)

    elif action == "admins":
        conn = _db_connect(); rows = conn.execute("SELECT * FROM admins ORDER BY created_at").fetchall(); conn.close()
        text = "👑 **مدیران ربات**\n\n" + "\n".join([f"• `{int(r['user_id'])}` — {r['role']}" for r in rows])
        m = types.InlineKeyboardMarkup(row_width=2)
        if int(call.from_user.id) == int(ADMIN_ID):
            m.add(types.InlineKeyboardButton("➕ افزودن مدیر", callback_data="admin:admin_add"), types.InlineKeyboardButton("➖ حذف مدیر", callback_data="admin:admin_remove"))
        bot.send_message(admin_chat, text, parse_mode="Markdown", reply_markup=m)

    elif action == "admin_add":
        if int(call.from_user.id) != int(ADMIN_ID): return
        msg = bot.send_message(admin_chat, "👑 Telegram ID مدیر جدید را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_add)

    elif action == "admin_remove":
        if int(call.from_user.id) != int(ADMIN_ID): return
        msg = bot.send_message(admin_chat, "➖ Telegram ID مدیری که باید حذف شود را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_remove)

    elif action == "ops":
        last = int(get_db_setting('last_automatic_backup_at','0') or 0)
        last_txt = datetime.fromtimestamp(last).strftime('%Y-%m-%d %H:%M') if last else 'هنوز انجام نشده'
        auto = get_db_setting('automatic_backup_enabled','1') == '1'
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton("💾 بکاپ همین الان", callback_data="admin:backup_now"), types.InlineKeyboardButton("⏯ بکاپ خودکار", callback_data="admin:backup_toggle"))
        bot.send_message(admin_chat, f"💾 **بکاپ و عملیات**\n\nبکاپ خودکار: {'🟢 فعال' if auto else '🔴 غیرفعال'}\nآخرین بکاپ: **{last_txt}**\nRetention: **{get_db_setting('automatic_backup_retention','14')} نسخه**", parse_mode="Markdown", reply_markup=m)

    elif action == "backup_now":
        bot.answer_callback_query(call.id, "در حال بکاپ...")
        try:
            path = create_database_backup(manual=True)
            bot.send_message(admin_chat, f"✅ بکاپ SQLite ساخته شد:\n`{path}`", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(admin_chat, f"❌ بکاپ خطا داد: `{str(e)[:500]}`", parse_mode="Markdown")

    elif action == "backup_toggle":
        new = '0' if get_db_setting('automatic_backup_enabled','1') == '1' else '1'
        update_db_setting('automatic_backup_enabled', new)
        bot.answer_callback_query(call.id, "تغییر کرد ✅")

    elif action == "content":
        m = types.InlineKeyboardMarkup(row_width=1)
        m.add(types.InlineKeyboardButton("✏️ متن خوش‌آمد", callback_data="admin:welcome_edit"), types.InlineKeyboardButton("📚 متن راهنما/FAQ", callback_data="admin:faq_edit"))
        bot.send_message(admin_chat, "📝 متن موردنظر را برای ویرایش انتخاب کنید.", reply_markup=m)

    elif action == "welcome_edit":
        msg = bot.send_message(admin_chat, "متن جدید خوش‌آمد را بفرستید. Markdown مجاز است.")
        bot.register_next_step_handler(msg, process_admin_content, 'welcome_text')

    elif action == "faq_edit":
        msg = bot.send_message(admin_chat, "متن جدید راهنما/FAQ را بفرستید. Markdown مجاز است.")
        bot.register_next_step_handler(msg, process_admin_content, 'faq_text')

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
        bot.send_message(admin_chat, text, parse_mode="Markdown", reply_markup=m)

    elif action == "affiliate_toggle":
        new_value = '0' if referral_enabled() else '1'
        update_db_setting('referral_enabled', new_value)
        bot.answer_callback_query(call.id, "وضعیت تغییر کرد ✅")
        bot.send_message(admin_chat, f"🤝 همکاری در فروش {'فعال شد 🟢' if new_value == '1' else 'غیرفعال شد 🔴'}")

    elif action == "affiliate_percent":
        msg = bot.send_message(admin_chat, "📈 درصد پورسانت جدید را از 0 تا 100 وارد کنید. مثال: `10` یا `7.5`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_affiliate_percent)

    elif action == "affiliate_wallet":
        msg = bot.send_message(admin_chat, "👛 آیدی کاربر و مبلغ را در یک خط بفرستید.\nمثال شارژ: `123456789 50000`\nمثال کسر: `123456789 -20000`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_wallet_adjustment)

    elif action == "affiliate_top":
        conn = _db_connect()
        rows = conn.execute(
            """SELECT referrer_id, COUNT(DISTINCT referred_id) AS buyers, SUM(commission_amount) AS earned
               FROM referral_commissions GROUP BY referrer_id ORDER BY earned DESC LIMIT 10"""
        ).fetchall()
        conn.close()
        if not rows:
            bot.send_message(admin_chat, "🏆 هنوز پورسانتی ثبت نشده است.")
        else:
            lines = ["🏆 **۱۰ معرف برتر**\n"]
            for i, row in enumerate(rows, 1):
                lines.append(f"{i}. `{row['referrer_id']}` — خریدار: {int(row['buyers'])} — پورسانت: **{int(row['earned'] or 0):,} تومان**")
            bot.send_message(admin_chat, "\n".join(lines), parse_mode="Markdown")

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
        bot.send_message(admin_chat, text, parse_mode="Markdown", reply_markup=m)

    elif action == "notifications_toggle":
        new_value = '0' if service_notifications_enabled() else '1'
        update_db_setting('service_notifications_enabled', new_value)
        bot.answer_callback_query(call.id, "وضعیت تغییر کرد ✅")
        bot.send_message(admin_chat, f"🔔 اعلان سرویس‌ها {'فعال شد 🟢' if new_value == '1' else 'غیرفعال شد 🔴'}")

    elif action == "notifications_check":
        bot.answer_callback_query(call.id, "در حال بررسی پنل...")
        result = check_service_notifications(force=True)
        bot.send_message(admin_chat, _format_monitor_result(result), parse_mode="Markdown")

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
                bot.send_message(admin_chat, srv_txt, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(admin_chat, f"🚨 خطا در ارتباط با وب‌سرویس سرور")
            
    elif action == "broadcast":
        msg = bot.send_message(admin_chat, "📣 پیام همگانی خود را بفرستید:")
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
        bot.send_message(admin_chat, bank_txt, parse_mode="Markdown", reply_markup=b_markup)
        
    elif action in ["edit_card", "edit_holder", "edit_bank"]:
        msg = bot.send_message(admin_chat, f"✍️ مقدار جدید را وارد کنید:")
        bot.register_next_step_handler(msg, process_edit_bank, action)
        
    elif action == "delete_user":
        msg = bot.send_message(admin_chat, "👤 آیدی عددی کاربر را برای غیرفعال‌سازی وارد کنید. سوابق مالی، تست و معرف حذف نمی‌شوند:")
        bot.register_next_step_handler(msg, process_delete_bot_user)
        
    elif action == "delete_sub":
        msg = bot.send_message(admin_chat, "🔌 نام اشتراک (Email) مورد نظر در پنل را جهت حذف وارد کنید:")
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
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"⏳ فیش {tx_id} تایید شد و سرویس در حال صدور است..."
            )
        except Exception:
            pass
        finalize_service_transaction(tx_id, admin_message_id=call.message.message_id, admin_chat_id=call.message.chat.id)
    elif action == "reject":
        conn.execute("UPDATE transactions SET status = 'REJECTED', last_error = NULL WHERE id = ?", (tx_id,))
        conn.execute("UPDATE discount_redemptions SET status='RELEASED' WHERE tx_id=? AND status='RESERVED'", (tx_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "فیش رد شد.")
        try:
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=f"❌ فیش {tx_id} رد شد.")
        except Exception:
            pass
        bot.send_message(user_id, "❌ فیش واریزی شما توسط پشتیبانی رد شد.", reply_markup=main_menu())


def _admin_reply(message, text, **kwargs):
    bot.send_message(message.chat.id, text, **kwargs)


def process_admin_plan_add(message):
    try:
        parts = [x.strip() for x in (message.text or '').split('|')]
        if len(parts) != 5:
            raise ValueError
        name = parts[0]
        price = int(parts[1].replace(',', ''))
        volume = float(parts[2])
        days = int(parts[3])
        ip_limit = int(parts[4])
        if not name or price <= 0 or volume < 0 or days <= 0 or ip_limit < 0:
            raise ValueError
        conn = _db_connect()
        sort_order = int(conn.execute("SELECT COALESCE(MAX(sort_order),0)+10 AS n FROM plans").fetchone()['n'])
        now_ts = int(time.time())
        cur = conn.execute("INSERT INTO plans (name,price,volume_gb,days,ip_limit,active,sort_order,created_at,updated_at) VALUES (?,?,?,?,?,1,?,?,?)",
                           (name, price, volume, days, ip_limit, sort_order, now_ts, now_ts))
        conn.commit(); pid = cur.lastrowid; conn.close()
        _admin_reply(message, f"✅ پلان `#{pid}` ساخته شد: **{name}** — {price:,} تومان", parse_mode="Markdown")
    except Exception:
        _admin_reply(message, "❌ فرمت نامعتبر است. مثال:\n`سه‌ماهه | 750000 | 0 | 90 | 2`", parse_mode="Markdown")


def process_admin_plan_edit(message):
    try:
        parts = [x.strip() for x in (message.text or '').split('|')]
        if len(parts) != 6:
            raise ValueError
        pid = int(parts[0]); name=parts[1]; price=int(parts[2].replace(',','')); volume=float(parts[3]); days=int(parts[4]); ip_limit=int(parts[5])
        if price <= 0 or volume < 0 or days <= 0 or ip_limit < 0 or not name:
            raise ValueError
        conn=_db_connect(); row=conn.execute("SELECT id FROM plans WHERE id=?",(pid,)).fetchone()
        if not row:
            conn.close(); _admin_reply(message,"❌ پلان پیدا نشد."); return
        conn.execute("UPDATE plans SET name=?,price=?,volume_gb=?,days=?,ip_limit=?,updated_at=? WHERE id=?",
                     (name,price,volume,days,ip_limit,int(time.time()),pid)); conn.commit(); conn.close()
        _admin_reply(message, f"✅ پلان `#{pid}` ویرایش شد.", parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ فرمت نامعتبر. `ID | نام | قیمت | حجمGB | روز | IP`",parse_mode="Markdown")


def process_admin_plan_toggle(message):
    try:
        pid=int((message.text or '').strip()); conn=_db_connect(); row=conn.execute("SELECT active FROM plans WHERE id=?",(pid,)).fetchone()
        if not row:
            conn.close(); _admin_reply(message,"❌ پلان پیدا نشد."); return
        new=0 if int(row['active']) else 1; conn.execute("UPDATE plans SET active=?,updated_at=? WHERE id=?",(new,int(time.time()),pid)); conn.commit(); conn.close()
        _admin_reply(message,f"✅ پلان `#{pid}` {'فعال' if new else 'غیرفعال'} شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ ID نامعتبر است.")


def process_admin_volume_add(message):
    try:
        parts=[x.strip() for x in (message.text or '').split('|')]
        if len(parts)!=3: raise ValueError
        name=parts[0]; volume=float(parts[1]); price=int(parts[2].replace(',',''))
        if not name or volume<=0 or price<=0: raise ValueError
        conn=_db_connect(); sort_order=int(conn.execute("SELECT COALESCE(MAX(sort_order),0)+10 AS n FROM volume_packs").fetchone()['n'])
        cur=conn.execute("INSERT INTO volume_packs (name,volume_gb,price,active,sort_order,created_at) VALUES (?,?,?,1,?,?)",(name,volume,price,sort_order,int(time.time())))
        conn.commit(); vid=cur.lastrowid; conn.close(); _admin_reply(message,f"✅ بسته حجم `V#{vid}` ساخته شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ فرمت نامعتبر. مثال: `20 گیگ اضافه | 20 | 90000`",parse_mode="Markdown")


def process_admin_volume_toggle(message):
    try:
        vid=int((message.text or '').strip()); conn=_db_connect(); row=conn.execute("SELECT active FROM volume_packs WHERE id=?",(vid,)).fetchone()
        if not row:
            conn.close(); _admin_reply(message,"❌ بسته پیدا نشد."); return
        new=0 if int(row['active']) else 1; conn.execute("UPDATE volume_packs SET active=? WHERE id=?",(new,vid)); conn.commit(); conn.close()
        _admin_reply(message,f"✅ بسته `V#{vid}` {'فعال' if new else 'غیرفعال'} شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ ID نامعتبر.")


def process_admin_cashback_percent(message):
    try:
        value=float((message.text or '').strip().replace('%','').replace('٪',''))
        if value<0 or value>100: raise ValueError
        update_db_setting('cashback_percent',f"{value:g}"); _admin_reply(message,f"✅ کش‌بک روی **{value:g}٪** تنظیم شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ درصد باید بین 0 تا 100 باشد.")


def process_admin_discount_add(message):
    try:
        parts=[x.strip() for x in (message.text or '').split('|')]
        if len(parts)!=6: raise ValueError
        code=parts[0].upper(); dtype=parts[1].upper(); value=float(parts[2]); min_purchase=int(parts[3].replace(',','')); max_uses=int(parts[4]); days=int(parts[5])
        if not re.fullmatch(r'[A-Z0-9_-]{3,32}',code) or dtype not in ('PERCENT','FIXED') or value<=0 or min_purchase<0 or max_uses<0 or days<0: raise ValueError
        if dtype=='PERCENT' and value>100: raise ValueError
        expires=int(time.time())+days*86400 if days>0 else None
        conn=_db_connect(); conn.execute("INSERT OR REPLACE INTO discount_codes (code,discount_type,value,min_purchase,max_uses,per_user_limit,expires_at,active,created_at) VALUES (?,?,?,?,?,1,?,1,?)",
            (code,dtype,value,min_purchase,max_uses,expires,int(time.time()))); conn.commit(); conn.close()
        _admin_reply(message,f"✅ کد تخفیف `{code}` ساخته شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ فرمت نامعتبر. مثال:\n`WELCOME20 | percent | 20 | 200000 | 100 | 30`",parse_mode="Markdown")


def process_admin_gift_add(message):
    try:
        parts=[x.strip() for x in (message.text or '').split('|')]
        if len(parts)!=4: raise ValueError
        code=parts[0].upper(); amount=int(parts[1].replace(',','')); max_uses=int(parts[2]); days=int(parts[3])
        if not re.fullmatch(r'[A-Z0-9_-]{3,32}',code) or amount<=0 or max_uses<=0 or days<0: raise ValueError
        expires=int(time.time())+days*86400 if days>0 else None
        conn=_db_connect(); conn.execute("INSERT OR REPLACE INTO gift_codes (code,amount,max_uses,expires_at,active,created_at) VALUES (?,?,?,?,1,?)",(code,amount,max_uses,expires,int(time.time()))); conn.commit(); conn.close()
        _admin_reply(message,f"✅ کد هدیه `{code}` با مبلغ **{amount:,} تومان** ساخته شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ فرمت نامعتبر. مثال:\n`GIFT50 | 50000 | 20 | 30`",parse_mode="Markdown")


def process_admin_discount_toggle(message):
    code=(message.text or '').strip().upper()
    conn=_db_connect(); row=conn.execute("SELECT active FROM discount_codes WHERE code=?",(code,)).fetchone()
    if not row:
        conn.close(); _admin_reply(message,"❌ کد تخفیف پیدا نشد."); return
    new=0 if int(row['active']) else 1
    conn.execute("UPDATE discount_codes SET active=? WHERE code=?",(new,code)); conn.commit(); conn.close()
    _admin_reply(message,f"✅ کد تخفیف `{code}` {'فعال' if new else 'غیرفعال'} شد.",parse_mode="Markdown")


def process_admin_gift_toggle(message):
    code=(message.text or '').strip().upper()
    conn=_db_connect(); row=conn.execute("SELECT active FROM gift_codes WHERE code=?",(code,)).fetchone()
    if not row:
        conn.close(); _admin_reply(message,"❌ کد هدیه پیدا نشد."); return
    new=0 if int(row['active']) else 1
    conn.execute("UPDATE gift_codes SET active=? WHERE code=?",(new,code)); conn.commit(); conn.close()
    _admin_reply(message,f"✅ کد هدیه `{code}` {'فعال' if new else 'غیرفعال'} شد.",parse_mode="Markdown")


def process_admin_channel_set(message):
    try:
        parts=[x.strip() for x in (message.text or '').split('|')]
        channel=parts[0]; url=parts[1] if len(parts)>1 else ''
        if not channel: raise ValueError
        if channel.lstrip('-').isdigit(): channel=int(channel)
        update_db_setting('required_channel',str(channel)); update_db_setting('required_channel_url',url)
        _admin_reply(message,f"✅ کانال اجباری روی `{channel}` تنظیم شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ فرمت کانال نامعتبر است.")


def process_admin_add(message):
    if int(message.from_user.id)!=int(ADMIN_ID): return
    try:
        uid=int((message.text or '').strip()); conn=_db_connect(); conn.execute("INSERT OR IGNORE INTO admins (user_id,role,added_by,created_at) VALUES (?,'ADMIN',?,?)",(uid,int(ADMIN_ID),int(time.time()))); conn.commit(); conn.close()
        _admin_reply(message,f"✅ `{uid}` به مدیران اضافه شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ Telegram ID نامعتبر است.")


def process_admin_remove(message):
    if int(message.from_user.id)!=int(ADMIN_ID): return
    try:
        uid=int((message.text or '').strip())
        if uid==int(ADMIN_ID): _admin_reply(message,"❌ Owner اصلی قابل حذف نیست."); return
        conn=_db_connect(); conn.execute("DELETE FROM admins WHERE user_id=?",(uid,)); conn.commit(); conn.close(); _admin_reply(message,f"✅ مدیر `{uid}` حذف شد.",parse_mode="Markdown")
    except Exception:
        _admin_reply(message,"❌ Telegram ID نامعتبر است.")


def process_admin_content(message, key):
    text=(message.text or '').strip()
    if not text:
        _admin_reply(message,"❌ متن خالی قابل ذخیره نیست."); return
    update_db_setting(key,text); _admin_reply(message,"✅ متن ذخیره شد.")


@bot.message_handler(commands=['groupsdiag'])
def groups_diag_command(message):
    if not is_admin(message.from_user.id): return
    try:
        groups=_xui_list_groups()
        lines=[f"👥 Groups پنل: **{len(groups)} دسته**"]
        for g in groups:
            lines.append(f"• **{g.get('name','-')}** — `{int(g.get('clientCount') or 0)}`")
        bot.send_message(message.chat.id,"\n".join(lines),parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id,f"❌ `{str(e)[:800]}`",parse_mode="Markdown")


def process_affiliate_percent(message):
    try:
        value = float((message.text or '').strip().replace('٪', '').replace('%', ''))
        if value < 0 or value > 100:
            raise ValueError
        update_db_setting('referral_commission_percent', f"{value:g}")
        bot.send_message(message.chat.id, f"✅ نرخ پورسانت همکاری در فروش روی **{value:g}٪** تنظیم شد.", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ درصد نامعتبر است. عددی بین 0 و 100 وارد کنید.")


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
            bot.send_message(message.chat.id, f"❌ موجودی کاربر برای کسر این مبلغ کافی نیست. موجودی فعلی: {new_balance:,} تومان")
            return
        bot.send_message(message.chat.id, f"✅ کیف پول `{user_id}` اصلاح شد. موجودی جدید: **{new_balance:,} تومان**", parse_mode="Markdown")
        try:
            bot.send_message(user_id, f"👛 کیف پول شما توسط مدیریت **{amount:+,} تومان** تغییر کرد.\nموجودی جدید: **{new_balance:,} تومان**", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.send_message(message.chat.id, "❌ فرمت نامعتبر است. مثال: `123456789 50000` یا `123456789 -20000`", parse_mode="Markdown")


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
        "SELECT user_id, price, payment_method, wallet_used, status, service_email, kind FROM transactions WHERE id = ?",
        (tx_id,)
    ).fetchone()
    conn.close()
    if not tx or tx['status'] != 'ISSUE' or tx['payment_method'] != 'WALLET' or (tx['kind'] or 'NEW') != 'NEW':
        bot.answer_callback_query(call.id, "بازپرداخت خودکار فقط برای خرید سرویس جدید مجاز است؛ تمدید/حجم اضافه باید دستی بررسی شود.", show_alert=True)
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
    _finish_discount(tx_id, applied=False)
    bot.answer_callback_query(call.id, "مبلغ به کیف پول برگشت ✅")
    bot.send_message(call.message.chat.id, f"✅ تراکنش کیف پول `{tx_id}` بازپرداخت شد. موجودی کاربر: **{balance:,} تومان**", parse_mode="Markdown")
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
    
    bot.send_message(message.chat.id, f"⏳ فرآیند ارسال آغاز شد...")
    success_count = 0
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success_count += 1
            time.sleep(0.04)
        except: continue
    bot.send_message(message.chat.id, f"✅ تحویل موفق به {success_count} کاربر.")

def process_edit_bank(message, field_type):
    if field_type == "admin:edit_card" or field_type == "edit_card":
        update_db_setting('card_number', message.text.strip())
    elif field_type == "admin:edit_holder" or field_type == "edit_holder":
        update_db_setting('card_holder', message.text.strip())
    elif field_type == "admin:edit_bank" or field_type == "edit_bank":
        update_db_setting('bank_name', message.text.strip())
    bot.send_message(message.chat.id, "✅ مشخصات بانکی با موفقیت به‌روزرسانی شد.")

def process_delete_bot_user(message):
    try:
        target_id = int(message.text.strip())
        conn = _db_connect()
        row = conn.execute("SELECT id FROM users WHERE id = ?", (target_id,)).fetchone()
        if not row:
            conn.close()
            bot.send_message(message.chat.id, "❌ این کاربر در دیتابیس نیست.")
            return
        # حذف فیزیکی انجام نمی‌شود تا سوابق تست، معرف و کیف پول قابل سوءاستفاده نباشند.
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ کاربر `{target_id}` غیرفعال شد و از پیام‌های همگانی حذف می‌شود. سوابق مالی/معرف برای امنیت حفظ شدند.", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ آیدی نامعتبر.")

def process_delete_panel_sub(message):
    email = message.text.strip()
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    try:
        del_url = _xui_url(f"panel/api/clients/del/{quote(str(email), safe='')}") + "?keepTraffic=0"
        res = requests.post(del_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        if res.status_code == 200 and res.json().get("success"):
            bot.send_message(message.chat.id, f"✅ اشتراک `{email}` با موفقیت از پنل حذف شد.")
        else: bot.send_message(message.chat.id, f"❌ خطای پنل: {res.text}")
    except Exception as e: bot.send_message(message.chat.id, f"🚨 خطای ارتباطی")

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


def _xui_list_groups():
    response = requests.get(
        _xui_url("panel/api/clients/groups"),
        headers=_xui_headers(), proxies=_xui_proxies(), timeout=15, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در دریافت Groups پنل"))
    return data.get('obj', []) or []


def _xui_ensure_group(name):
    name = (name or '').strip()
    if not name:
        return False
    groups = _xui_list_groups()
    if any(str(g.get('name', '')).lower() == name.lower() for g in groups):
        return True
    response = requests.post(
        _xui_url("panel/api/clients/groups/create"),
        json={'name': name}, headers=_xui_headers(), proxies=_xui_proxies(), timeout=15, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, f"خطا در ساخت Group {name}"))
    return True


def _xui_assign_group_bulk(emails, group_name):
    emails = [str(e).strip() for e in (emails or []) if str(e).strip()]
    if not emails:
        return 0
    _xui_ensure_group(group_name)
    response = requests.post(
        _xui_url("panel/api/clients/groups/bulkAdd"),
        json={'emails': sorted(set(emails)), 'group': str(group_name)},
        headers=_xui_headers(), proxies=_xui_proxies(), timeout=30, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, f"خطا در افزودن کلاینت‌ها به Group {group_name}"))
    obj = data.get('obj') or {}
    return int(obj.get('affected') or len(set(emails)))


def _xui_assign_group(email, group_name):
    _xui_assign_group_bulk([email], group_name)
    return True


def ensure_required_xui_groups():
    customer_group = get_db_setting('xui_customers_group', 'Customers') or 'Customers'
    trial_group = get_db_setting('xui_trial_group', 'Trial') or 'Trial'
    _xui_ensure_group(customer_group)
    _xui_ensure_group(trial_group)
    return customer_group, trial_group


def _xui_online_emails():
    response = requests.post(
        _xui_url("panel/api/clients/onlines"), headers=_xui_headers(), proxies=_xui_proxies(), timeout=15, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در دریافت کاربران آنلاین"))
    return data.get('obj', []) or []


def reconcile_service_groups():
    customer_group, trial_group = ensure_required_xui_groups()
    conn = _db_connect()
    paid = conn.execute("SELECT DISTINCT service_email FROM transactions WHERE status='APPROVED' AND kind='NEW' AND service_email IS NOT NULL").fetchall()
    trials = conn.execute("SELECT email FROM trial_services WHERE status IN ('ACTIVE','EXPIRED')").fetchall()
    conn.close()
    ok = 0; errors = []
    try:
        ok += _xui_assign_group_bulk([row['service_email'] for row in paid], customer_group)
    except Exception as e:
        errors.append(f"Customers: {str(e)[:300]}")
    try:
        ok += _xui_assign_group_bulk([row['email'] for row in trials], trial_group)
    except Exception as e:
        errors.append(f"Trial: {str(e)[:300]}")
    return {'updated': ok, 'errors': errors, 'customer_group': customer_group, 'trial_group': trial_group}


def _get_exported_client(email):
    response = requests.get(
        _xui_url("panel/api/clients/export"), headers=_xui_headers(), proxies=_xui_proxies(), timeout=20, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در Export کلاینت‌ها"))
    for item in data.get('obj', []) or []:
        client = item.get('client') or {}
        if str(client.get('email')) == str(email):
            return client, item.get('inboundIds', []) or []
    return None, []


def _update_exported_client(email, changes):
    client, _ = _get_exported_client(email)
    if not client:
        raise RuntimeError(f"کلاینت {email} در پنل پیدا نشد.")
    payload = dict(client)
    payload.update(changes)
    # traffic/inbound metadata are not part of the client update body.
    for key in ('traffic', 'inboundIds', 'clientStats'):
        payload.pop(key, None)
    response = requests.post(
        _xui_url(f"panel/api/clients/update/{quote(str(email), safe='')}"),
        json=payload, headers=_xui_headers(), proxies=_xui_proxies(), timeout=20, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در Update کلاینت"))
    return True


def renew_xui_service(user_id, user_email, days, volume_gb, ip_limit):
    client, _ = _get_exported_client(user_email)
    if not client:
        raise RuntimeError("سرویس برای تمدید در پنل پیدا نشد.")
    now_ms = int(time.time() * 1000)
    current_expiry = int(client.get('expiryTime') or 0)
    base = max(now_ms, current_expiry) if current_expiry else now_ms
    new_expiry = base + int(days) * 86400 * 1000
    total_bytes = 0 if float(volume_gb or 0) <= 0 else int(float(volume_gb) * 1024**3)
    _update_exported_client(user_email, {
        'expiryTime': new_expiry,
        'totalGB': total_bytes,
        'limitIp': int(ip_limit),
        'tgId': int(user_id),
        'enable': True,
    })
    # New period starts clean; this endpoint also re-enables the client in Xray.
    reset = requests.post(
        _xui_url(f"panel/api/clients/resetTraffic/{quote(str(user_email), safe='')}"),
        headers=_xui_headers(), proxies=_xui_proxies(), timeout=15, verify=not DEVELOPMENT_MODE
    )
    if reset.status_code != 200 or not _safe_json(reset).get('success'):
        raise RuntimeError(_xui_response_error(reset, "تمدید انجام شد ولی Reset Traffic خطا داد"))
    try:
        _xui_assign_group(user_email, get_db_setting('xui_customers_group', 'Customers') or 'Customers')
    except Exception as e:
        notify_admins(f"⚠️ تمدید {user_email} انجام شد ولی Group Customers به‌روزرسانی نشد: {str(e)[:300]}")
    return new_expiry


def add_volume_xui_service(user_email, volume_gb):
    volume_bytes = int(float(volume_gb) * 1024**3)
    if volume_bytes <= 0:
        raise RuntimeError("حجم اضافه نامعتبر است.")
    client = _get_client_data(user_email, _xui_headers(), _xui_proxies())
    if not client:
        raise RuntimeError("سرویس در پنل پیدا نشد.")
    if int(client.get('totalGB') or client.get('total') or 0) == 0:
        raise RuntimeError("این سرویس نامحدود است و خرید حجم اضافه برای آن کاربردی ندارد.")
    response = requests.post(
        _xui_url("panel/api/clients/bulkAdjust"),
        json={'emails': [str(user_email)], 'addDays': 0, 'addBytes': volume_bytes, 'flow': ''},
        headers=_xui_headers(), proxies=_xui_proxies(), timeout=20, verify=not DEVELOPMENT_MODE
    )
    data = _safe_json(response)
    if response.status_code != 200 or not data.get('success'):
        raise RuntimeError(_xui_response_error(response, "خطا در افزودن حجم"))
    return True


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
                    "limitIp": 1,
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

        try:
            _xui_assign_group(user_email, get_db_setting('xui_trial_group', 'Trial') or 'Trial')
        except Exception as group_error:
            notify_admins(f"⚠️ تست {user_email} ساخته شد اما عضویت Group Trial خطا داد: {str(group_error)[:350]}")
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
            notify_admins(f"🚨 خطا در صدور تست رایگان برای {user_id}:\n{str(e)[:800]}")
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
            notify_admins(f"⚠️ تست کاربر {user_id} ساخته شد اما پیام تحویل به کاربر ارسال نشد: {str(e)[:500]}")
        except Exception:
            pass

    try:
        notify_admins(f"🎁 تست رایگان برای کاربر `{user_id}` با موفقیت صادر شد.", parse_mode="Markdown")
    except Exception:
        pass


def _tx_plan_snapshot(tx):
    plan = get_plan(int(tx['plan_id']), include_inactive=True) if int(tx['plan_id'] or 0) > 0 else None
    return {
        'id': int(tx['plan_id'] or 0),
        'name': tx['plan_name_snapshot'] or (plan['name'] if plan else 'SpeedPing'),
        'price': int(tx['price'] or 0),
        'days': int(tx['plan_days_snapshot'] if tx['plan_days_snapshot'] is not None else (plan['days'] if plan else 0)),
        'volume': float(tx['plan_volume_gb_snapshot'] if tx['plan_volume_gb_snapshot'] is not None else (plan['volume'] if plan else 0)),
        'ip_limit': int(tx['plan_ip_limit_snapshot'] if tx['plan_ip_limit_snapshot'] is not None else (plan['ip_limit'] if plan else 1)),
    }


def provision_xui_service(user_id, plan_id, tx_id, user_email):
    """Create/read a paid X-UI client idempotently and return delivery links."""
    conn = _db_connect()
    tx = conn.execute("SELECT * FROM transactions WHERE id=?", (int(tx_id),)).fetchone()
    conn.close()
    if not tx:
        raise RuntimeError("تراکنش برای صدور پیدا نشد.")
    plan = _tx_plan_snapshot(tx)
    total_bytes = int(float(plan['volume']) * 1024**3) if float(plan['volume']) > 0 else 0
    expiry_time_ms = int((time.time() + (int(plan['days']) * 86400)) * 1000)
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
                "tgId": int(user_id),
                "limitIp": int(plan['ip_limit']),
                "enable": True
            },
            "inboundIds": active_inbound_ids
        }
        response = requests.post(
            _xui_url("panel/api/clients/add"), json=payload, headers=headers,
            proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE
        )
        data = _safe_json(response)
        if response.status_code != 200 or not data.get('success'):
            time.sleep(0.8)
            client_data = _get_client_data(user_email, headers, request_proxies)
            if not client_data:
                raise RuntimeError(_xui_response_error(response, "پنل ساخت سرویس را رد کرد"))
        else:
            time.sleep(1.0)
            client_data = _get_client_data(user_email, headers, request_proxies)

    try:
        _xui_assign_group(user_email, get_db_setting('xui_customers_group', 'Customers') or 'Customers')
    except Exception as group_error:
        notify_admins(f"⚠️ سرویس {user_email} ساخته شد اما Group Customers خطا داد: {str(group_error)[:350]}")

    config_links = _get_client_links(user_email, headers, request_proxies)
    sub_id = _get_client_subscription_id(user_email, headers, request_proxies, client_data)
    if not sub_id and not config_links:
        raise RuntimeError("سرویس روی پنل وجود دارد اما هیچ لینک قابل تحویلی دریافت نشد.")
    return sub_id, config_links


def _send_transaction_success(tx_id, sub_id=None, config_links=None):
    conn = _db_connect()
    tx = conn.execute("SELECT * FROM transactions WHERE id=?", (int(tx_id),)).fetchone()
    conn.close()
    if not tx:
        return
    user_id = int(tx['user_id'])
    kind = tx['kind'] or 'NEW'
    name = tx['plan_name_snapshot'] or 'SpeedPing'
    if kind == 'NEW':
        msg_text = f"🎉 **سرویس SpeedPing شما فعال شد!**\n\n📦 پلن: **{name}**\n🆔 تراکنش: `{tx_id}`\n\n"
        if sub_id:
            msg_text += f"🌐 **لینک سابسکریپشن:**\n```\n{_subscription_url(sub_id)}\n```\n"
        if config_links:
            msg_text += "\n🔑 **کانفیگ‌های اتصال مستقیم:**\n"
            for link in config_links:
                msg_text += f"```\n{link}\n```\n"
        msg_text += "\nاز بخش حساب کاربری می‌توانید وضعیت، QR و تمدید سرویس را مدیریت کنید."
    elif kind == 'RENEWAL':
        msg_text = (
            f"♻️ **تمدید سرویس با موفقیت انجام شد.**\n\n"
            f"📦 پلن تمدید: **{name}**\n"
            f"⏱ مدت افزوده‌شده: **{int(tx['plan_days_snapshot'] or 0)} روز**\n"
            f"👥 IP Limit جدید: **{int(tx['plan_ip_limit_snapshot'] or 0)}**\n"
            f"🆔 تراکنش: `{tx_id}`\n\n"
            "لینک Subscription قبلی شما همان لینک است و نیازی به تعویض ندارد."
        )
    else:
        msg_text = (
            f"➕ **حجم اضافه با موفقیت اعمال شد.**\n\n"
            f"📦 بسته: **{name}**\n"
            f"➕ حجم افزوده‌شده: **{float(tx['extra_volume_gb'] or 0):g} GB**\n"
            f"🆔 تراکنش: `{tx_id}`"
        )
    bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=main_menu())


def finalize_service_transaction(tx_id, admin_message_id=None, admin_chat_id=None):
    """Fulfil NEW / RENEWAL / VOLUME transactions idempotently, then settle rewards."""
    conn = _db_connect()
    tx = conn.execute("SELECT * FROM transactions WHERE id = ?", (int(tx_id),)).fetchone()
    conn.close()
    if not tx or tx['status'] not in ('PROCESSING', 'ISSUE'):
        return False

    user_id = int(tx['user_id'])
    user_email = tx['service_email'] or f"speedping_{user_id}_{tx_id}"
    kind = tx['kind'] or 'NEW'
    sub_id = None
    config_links = []

    try:
        if kind == 'NEW':
            sub_id, config_links = provision_xui_service(user_id, int(tx['plan_id']), int(tx_id), user_email)
        elif kind == 'RENEWAL':
            renew_xui_service(
                user_id, user_email, int(tx['plan_days_snapshot'] or 0),
                float(tx['plan_volume_gb_snapshot'] or 0), int(tx['plan_ip_limit_snapshot'] or 1)
            )
            client = _get_client_data(user_email, _xui_headers(), _xui_proxies())
            sub_id = _get_client_subscription_id(user_email, _xui_headers(), _xui_proxies(), client)
        elif kind == 'VOLUME':
            add_volume_xui_service(user_email, float(tx['extra_volume_gb'] or 0))
        else:
            raise RuntimeError(f"نوع تراکنش ناشناخته: {kind}")
    except Exception as e:
        error_text = str(e)[:1000]
        conn = _db_connect()
        conn.execute(
            "UPDATE transactions SET status='ISSUE', last_error=?, service_email=? WHERE id=? AND status IN ('PROCESSING','ISSUE')",
            (error_text, user_email, int(tx_id))
        )
        conn.commit(); conn.close()
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        admin_markup.add(types.InlineKeyboardButton("🔄 Retry", callback_data=f"admin:retry:{tx_id}"))
        # بازپرداخت خودکار فقط برای خرید NEW امن است؛ در تمدید/حجم اضافه ممکن است بخشی از عملیات روی پنل اعمال شده باشد.
        if tx['payment_method'] == 'WALLET' and kind == 'NEW':
            admin_markup.add(types.InlineKeyboardButton("↩️ بازپرداخت کیف پول", callback_data=f"admin:refund_wallet:{tx_id}"))
        notify_admins(
            f"🚨 **تراکنش {tx_id} نیازمند بررسی است**\n\n👤 `{user_id}`\nنوع: `{kind}`\n✉️ `{user_email}`\n⚠️ `{error_text}`",
            parse_mode="Markdown", reply_markup=admin_markup
        )
        try:
            bot.send_message(user_id, f"⚠️ پرداخت تراکنش `{tx_id}` ثبت شده اما اجرای سرویس با مشکل موقت روبه‌رو شد. مدیریت مطلع شده و پرداخت شما محفوظ است.", parse_mode="Markdown", reply_markup=main_menu())
        except Exception:
            pass
        return False

    conn = _db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute("SELECT status FROM transactions WHERE id=?", (int(tx_id),)).fetchone()
        if not current or current['status'] == 'APPROVED':
            conn.rollback(); return True
        conn.execute("UPDATE transactions SET status='APPROVED', approved_at=?, service_email=?, last_error=NULL WHERE id=?",
                     (int(time.time()), user_email, int(tx_id)))
        conn.commit()
    finally:
        conn.close()

    _finish_discount(tx_id, applied=True)
    try:
        _send_transaction_success(tx_id, sub_id, config_links)
    except Exception as e:
        notify_admins(f"⚠️ تراکنش {tx_id} APPROVED شد اما پیام تحویل خطا داد: {str(e)[:500]}")

    reward = credit_referral_commission(tx_id)
    if reward:
        try:
            bot.send_message(reward['referrer_id'], f"💰 **پورسانت جدید!**\n➕ **{reward['amount']:,} تومان**\n👛 موجودی: **{reward['balance']:,} تومان**", parse_mode="Markdown", reply_markup=main_menu())
        except Exception:
            pass
    cashback = credit_cashback(tx_id)
    if cashback:
        try:
            bot.send_message(cashback['user_id'], f"🎁 **کش‌بک خرید**\n➕ **{cashback['amount']:,} تومان** به کیف پول شما برگشت.\n👛 موجودی: **{cashback['balance']:,} تومان**", parse_mode="Markdown")
        except Exception:
            pass

    notify_admins(f"✅ تراکنش `{tx_id}` ({kind}) برای کاربر `{user_id}` با موفقیت انجام شد.", parse_mode="Markdown")
    if admin_message_id and admin_chat_id:
        try:
            bot.edit_message_caption(chat_id=admin_chat_id, message_id=admin_message_id, caption=f"✅ تراکنش {tx_id} تایید و با موفقیت اجرا شد.")
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
                notify_admins(f"⚠️ بازیابی خودکار تراکنش {int(row['id'])} خطا داد: {str(e)[:500]}")
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
            "SELECT user_id, service_email, id AS tx_id FROM transactions WHERE status = 'APPROVED' AND kind = 'NEW' AND service_email IS NOT NULL AND service_email != ''"
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
            try:
                maybe_automatic_backup()
            except Exception as backup_error:
                notify_admins(f"⚠️ بکاپ خودکار SpeedPing خطا داد: {str(backup_error)[:500]}")
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
                    notify_admins(f"⚠️ مانیتور سرویس‌ها نتوانست پنل را بررسی کند:\n`{str(e)[:700]}`", parse_mode="Markdown")
                except Exception:
                    pass
        time.sleep(get_service_notification_interval())


def _startup_panel_reconcile():
    # اجرای غیرمسدودکننده: خرابی/قطعی پنل نباید polling ربات را متوقف کند.
    time.sleep(15)
    try:
        result = reconcile_service_groups()
        if result.get('errors'):
            notify_admins(f"⚠️ همگام‌سازی اولیه Groups با {len(result['errors'])} خطا تمام شد: " + "; ".join(result['errors'][:3]))
    except Exception as e:
        notify_admins(f"⚠️ همگام‌سازی اولیه Groups انجام نشد: {str(e)[:500]}")


def start_startup_panel_reconcile():
    threading.Thread(target=_startup_panel_reconcile, name="group-reconcile", daemon=True).start()


def start_service_monitor():
    global SERVICE_MONITOR_THREAD
    if SERVICE_MONITOR_THREAD and SERVICE_MONITOR_THREAD.is_alive():
        return
    SERVICE_MONITOR_THREAD = threading.Thread(target=_service_monitor_loop, name="service-monitor", daemon=True)
    SERVICE_MONITOR_THREAD.start()


@bot.message_handler(commands=['notifydiag'])
def notification_diag_command(message):
    if not is_admin(message.from_user.id):
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
    start_startup_panel_reconcile()
    start_service_monitor()
    bot.infinity_polling()
