import time
from .context import db


def _ensure_column(c, table, col, definition):
    cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def init_db():
    c = db()
    c.execute("PRAGMA journal_mode=WAL")
    now = int(time.time())
    c.execute("CREATE TABLE IF NOT EXISTS user_blocks(user_id INTEGER PRIMARY KEY,reason TEXT,active INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,created_by INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS plan_categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,active INTEGER NOT NULL DEFAULT 1,sort_order INTEGER NOT NULL DEFAULT 100,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
    _ensure_column(c, "plans", "category_id", "INTEGER")
    c.execute("CREATE TABLE IF NOT EXISTS trial_overrides(user_id INTEGER PRIMARY KEY,volume_gb REAL NOT NULL DEFAULT 1,days INTEGER NOT NULL DEFAULT 1,ip_limit INTEGER NOT NULL DEFAULT 1,note TEXT,updated_at INTEGER NOT NULL,updated_by INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS customer_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,rating INTEGER NOT NULL,comment TEXT,created_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,event_type TEXT NOT NULL,actor_id INTEGER,target_id TEXT,detail TEXT,created_at INTEGER NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS broadcast_history(id INTEGER PRIMARY KEY AUTOINCREMENT,admin_id INTEGER NOT NULL,audience TEXT NOT NULL,total INTEGER NOT NULL DEFAULT 0,sent INTEGER NOT NULL DEFAULT 0,failed INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL)")
    r = c.execute("SELECT id FROM plan_categories ORDER BY id LIMIT 1").fetchone()
    if not r:
        cur = c.execute("INSERT INTO plan_categories(name,active,sort_order,created_at,updated_at) VALUES ('عمومی',1,10,?,?)", (now, now))
        cid = int(cur.lastrowid)
    else:
        cid = int(r[0])
    c.execute("UPDATE plans SET category_id=? WHERE category_id IS NULL", (cid,))
    defaults = {
        "operating_mode": "NORMAL",
        "sales_paused_message": "🛒 فروش و تمدید موقتاً متوقف شده است. حساب کاربری، راهنما و پشتیبانی همچنان در دسترس هستند.",
        "maintenance_message": "🛠 سرویس موقتاً در حال نگهداری است. حساب کاربری، راهنما و پشتیبانی همچنان در دسترس هستند.",
        "feedback_enabled": "1",
        "plan_categories_enabled": "1",
        "trial_overrides_enabled": "1",
        "trial_default_volume_gb": "1",
        "trial_default_days": "1",
        "trial_default_ip_limit": "1",
        "audit_enabled": "1",
        "audit_chat_id": "",
        "ui_premium_emoji_enabled": "0",
        "ui_style_buy": "success",
        "ui_style_account": "primary",
        "ui_style_trial": "success",
        "ui_style_guide": "primary",
        "ui_style_support": "primary",
        "ui_style_admin": "primary",
        "ui_emoji_buy": "",
        "ui_emoji_account": "",
        "ui_emoji_trial": "",
        "ui_emoji_guide": "",
        "ui_emoji_support": "",
        "ui_emoji_admin": "",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES (?,?)", (k, v))
    c.commit()
    c.close()


def backfill_categories():
    c = db()
    r = c.execute("SELECT id FROM plan_categories WHERE active=1 ORDER BY sort_order,id LIMIT 1").fetchone()
    if r:
        c.execute(
            "UPDATE plans SET category_id=?,updated_at=COALESCE(updated_at,?) WHERE category_id IS NULL",
            (int(r[0]), int(time.time())),
        )
        c.commit()
    c.close()


def audiences(code):
    c = db()
    sql = {
        "all": "SELECT id FROM users WHERE is_active=1",
        "customers": "SELECT DISTINCT user_id FROM transactions WHERE status='APPROVED' AND kind='NEW'",
        "trial": "SELECT DISTINCT t.user_id FROM trial_services t WHERE NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=t.user_id AND x.status='APPROVED' AND x.kind='NEW')",
        "expired_trial": "SELECT DISTINCT t.user_id FROM trial_services t WHERE t.status='EXPIRED' AND NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=t.user_id AND x.status='APPROVED' AND x.kind='NEW')",
        "never_bought": "SELECT u.id FROM users u WHERE u.is_active=1 AND NOT EXISTS(SELECT 1 FROM transactions x WHERE x.user_id=u.id AND x.status='APPROVED' AND x.kind='NEW')",
    }.get(code)
    rows = c.execute(sql).fetchall() if sql else []
    c.close()
    return [int(r[0]) for r in rows]


def feedback_text():
    from html import escape

    c = db()
    total, avg = c.execute("SELECT COUNT(*),COALESCE(AVG(rating),0) FROM customer_feedback").fetchone()
    dist = {int(r[0]): int(r[1]) for r in c.execute("SELECT rating,COUNT(*) FROM customer_feedback GROUP BY rating")}
    recent = c.execute("SELECT user_id,rating,comment FROM customer_feedback ORDER BY id DESC LIMIT 8").fetchall()
    c.close()
    out = [
        "⭐ <b>بازخورد مشتریان</b>",
        "━━━━━━━━━━━━━━━━",
        f"📊 تعداد: <b>{int(total)}</b>",
        f"⭐ میانگین: <b>{float(avg):.2f}/5</b>",
        "",
    ]
    for n in range(5, 0, -1):
        out.append(f"{'⭐' * n}  {dist.get(n, 0)}")
    if recent:
        out += ["", "🕘 <b>آخرین بازخوردها</b>"]
        for r in recent:
            out.append(
                f"• <code>{r['user_id']}</code> — {r['rating']}/5"
                + (f" — {escape((r['comment'] or '')[:70])}" if r['comment'] else "")
            )
    return "\n".join(out)
