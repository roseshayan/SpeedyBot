import os
import sqlite3
import tempfile
import unittest

from speedybot import context as C, storage


class FakeTypes:
    class InlineKeyboardButton:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class KeyboardButton:
        def __init__(self, **kwargs):
            self.kwargs = kwargs


class FakeBot:
    def send_message(self, *args, **kwargs):
        return None


class FakeCore:
    types = FakeTypes
    bot = FakeBot()

    def get_db_setting(self, key, default=""):
        con = sqlite3.connect("speedping.db")
        try:
            row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default
        finally:
            con.close()

    def update_db_setting(self, key, value):
        con = sqlite3.connect("speedping.db")
        con.execute(
            "INSERT INTO settings(key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        con.commit()
        con.close()

    def is_admin(self, uid):
        return int(uid) == 1


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        con = sqlite3.connect("speedping.db")
        con.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
        con.execute(
            "CREATE TABLE plans(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,price INTEGER,"
            "volume_gb REAL,days INTEGER,ip_limit INTEGER,active INTEGER,sort_order INTEGER,"
            "created_at INTEGER,updated_at INTEGER)"
        )
        con.execute(
            "INSERT INTO plans(name,price,volume_gb,days,ip_limit,active,sort_order,created_at,updated_at) "
            "VALUES ('Plan A',100,0,30,1,1,10,1,1)"
        )
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,is_active INTEGER,balance INTEGER)")
        con.execute("CREATE TABLE transactions(id INTEGER PRIMARY KEY,user_id INTEGER,status TEXT,kind TEXT)")
        con.execute("CREATE TABLE trial_services(user_id INTEGER,status TEXT)")
        con.executemany("INSERT INTO users(id,is_active,balance) VALUES (?,?,0)", [(10, 1), (20, 1), (30, 1)])
        con.execute("INSERT INTO transactions(id,user_id,status,kind) VALUES (1,10,'APPROVED','NEW')")
        con.execute("INSERT INTO trial_services(user_id,status) VALUES (20,'EXPIRED')")
        con.commit()
        con.close()
        C.configure(FakeCore())
        storage.init_db()

    def tearDown(self):
        os.chdir(self.old)
        self.tmp.cleanup()

    def test_migration_and_category_backfill(self):
        con = sqlite3.connect("speedping.db")
        con.row_factory = sqlite3.Row
        category = con.execute("SELECT id,name FROM plan_categories").fetchone()
        plan = con.execute("SELECT category_id FROM plans WHERE id=1").fetchone()
        con.close()
        self.assertEqual(category["name"], "عمومی")
        self.assertEqual(plan["category_id"], category["id"])

    def test_blacklist_lookup(self):
        con = sqlite3.connect("speedping.db")
        con.execute(
            "INSERT INTO user_blocks(user_id,reason,active,created_at,created_by,updated_at) "
            "VALUES (20,'abuse',1,1,1,1)"
        )
        con.commit()
        con.close()
        self.assertEqual(C.blocked(20), (True, "abuse"))
        self.assertEqual(C.blocked(30), (False, ""))

    def test_audience_segments(self):
        self.assertEqual(storage.audiences("customers"), [10])
        self.assertEqual(storage.audiences("expired_trial"), [20])
        self.assertEqual(set(storage.audiences("never_bought")), {20, 30})

    def test_style_and_custom_emoji_payload(self):
        C.set_setting("ui_style_buy", "success")
        C.set_setting("ui_premium_emoji_enabled", "1")
        C.set_setting("ui_emoji_buy", "12345")
        button = C.inline("Buy", callback_data="x", emoji_key="buy")
        self.assertEqual(button.kwargs["style"], "success")
        self.assertEqual(button.kwargs["icon_custom_emoji_id"], "12345")

    def test_feedback_summary(self):
        con = sqlite3.connect("speedping.db")
        con.execute(
            "INSERT INTO customer_feedback(user_id,rating,comment,created_at) VALUES (10,5,?,1)",
            ("great",),
        )
        con.commit()
        con.close()
        text = storage.feedback_text()
        self.assertIn("5.00/5", text)
        self.assertIn("great", text)


if __name__ == "__main__":
    unittest.main()
