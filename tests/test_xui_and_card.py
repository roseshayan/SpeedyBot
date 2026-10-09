import os
import sqlite3
import sys
import tempfile
import unittest

try:
    import telebot
except ImportError:
    class MockTelebot:
        class TeleBot:
            def __init__(self, *args, **kwargs):
                self.message_handlers = []
                self.callback_query_handlers = []
            def message_handler(self, *args, **kwargs):
                def decorator(fn): return fn
                return decorator
            def callback_query_handler(self, *args, **kwargs):
                def decorator(fn): return fn
                return decorator
            def register_next_step_handler(self, *args, **kwargs): pass
            def send_message(self, *args, **kwargs): pass
            def send_photo(self, *args, **kwargs): pass
            def remove_webhook(self, *args, **kwargs): pass
            def answer_callback_query(self, *args, **kwargs): pass
        class types:
            class InlineKeyboardMarkup:
                def __init__(self, *args, **kwargs): pass
                def add(self, *args, **kwargs): pass
                def row(self, *args, **kwargs): pass
            class InlineKeyboardButton:
                def __init__(self, *args, **kwargs): self.kwargs = kwargs
            class ReplyKeyboardMarkup:
                def __init__(self, *args, **kwargs): pass
                def row(self, *args, **kwargs): pass
            class KeyboardButton:
                def __init__(self, *args, **kwargs): self.kwargs = kwargs
            class Message:
                pass
        class apihelper:
            pass
    m = MockTelebot()
    sys.modules['telebot'] = m
    sys.modules['telebot.types'] = m.types
    sys.modules['telebot.apihelper'] = m.apihelper

from speedybot import env_manager, core


class FakeMessage:
    def __init__(self, text=None, photo=None, document=None):
        self.text = text
        self.photo = photo
        self.document = document
        self.chat = type("Chat", (), {"id": 123456789})()
        self.message_id = 1


class FakePhotoSize:
    def __init__(self, file_id):
        self.file_id = file_id


class XuiAndCardTests(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        os.chdir(self.tmp.name)
        
        # Setup temporary sqlite database
        con = sqlite3.connect("speedping.db")
        con.execute("CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT)")
        con.execute(
            "CREATE TABLE users(id INTEGER PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0, created_at INTEGER, "
            "last_seen_at INTEGER, is_active INTEGER NOT NULL DEFAULT 1, referred_by INTEGER, referral_bound_at INTEGER, "
            "phone TEXT, phone_verified_at INTEGER, pending_discount_code TEXT)"
        )
        con.execute(
            "CREATE TABLE transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, photo_id TEXT, "
            "plan_id INTEGER, status TEXT, price INTEGER, payment_method TEXT, wallet_used INTEGER, cash_amount INTEGER, "
            "created_at INTEGER, approved_at INTEGER, service_email TEXT, last_error TEXT, kind TEXT, "
            "plan_name_snapshot TEXT, plan_days_snapshot INTEGER, plan_volume_gb_snapshot REAL, plan_ip_limit_snapshot INTEGER, "
            "discount_code TEXT, discount_amount INTEGER, extra_volume_gb REAL)"
        )
        con.execute(
            "CREATE TABLE plans(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, volume_gb REAL, "
            "days INTEGER, ip_limit INTEGER, active INTEGER, sort_order INTEGER, created_at INTEGER, updated_at INTEGER, category_id INTEGER)"
        )
        con.execute(
            "INSERT INTO plans(id, name, price, volume_gb, days, ip_limit, active, sort_order, created_at, updated_at, category_id) "
            "VALUES (1, 'یک‌ماهه VIP', 150000, 30, 30, 2, 1, 10, 1, 1, 1)"
        )
        con.execute(
            "INSERT INTO users(id, balance, is_active) VALUES (123456789, 0, 1)"
        )
        con.commit()
        con.close()

        # Setup temporary .env file
        self.env_path = os.path.join(self.tmp.name, ".env")
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.write(
                "export BOT_TOKEN='12345:TEST_TOKEN'\n"
                "export ADMIN_ID='123456789'\n"
                "export XUI_API_URL='https://panel.speed-ping.com:2053'\n"
                "export XUI_BASE_PATH='/my-base'\n"
                "export XUI_BEARER_TOKEN='token_old_12345678'\n"
                "export XUI_SUB_SERVER_URL='https://sub.speed-ping.com:2096'\n"
                "export XUI_SUB_PATH='/sub/'\n"
            )

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_env_manager_load_and_update(self):
        loaded = env_manager.load_env_file(self.env_path)
        self.assertEqual(loaded["XUI_API_URL"], "https://panel.speed-ping.com:2053")
        self.assertEqual(loaded["XUI_SUB_SERVER_URL"], "https://sub.speed-ping.com:2096")

        env_manager.update_env_file(
            {
                "XUI_API_URL": "https://panel.speed-ping.shop:2053",
                "XUI_SUB_SERVER_URL": "https://sub.speed-ping.shop:2096",
            },
            self.env_path,
        )

        with open(self.env_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        self.assertIn("https://panel.speed-ping.shop:2053", updated_content)
        self.assertIn("https://sub.speed-ping.shop:2096", updated_content)
        self.assertIn("BOT_TOKEN", updated_content)

    def test_xui_getters_and_setters(self):
        core.update_db_setting("xui_api_url", "https://panel.speed-ping.com:2053")
        core.update_db_setting("xui_sub_server_url", "https://sub.speed-ping.com:2096")
        core.update_db_setting("xui_base_path", "/panel-path")
        core.update_db_setting("xui_bearer_token", "secret_bearer_token")

        self.assertEqual(core.get_xui_api_url(), "https://panel.speed-ping.com:2053")
        self.assertEqual(core.get_xui_sub_server_url(), "https://sub.speed-ping.com:2096")
        self.assertEqual(core.get_xui_base_path(), "/panel-path")
        self.assertEqual(core.get_xui_bearer_token(), "secret_bearer_token")

        # Test URL builders
        sub_link = core._subscription_url("mysub123")
        self.assertEqual(sub_link, "https://sub.speed-ping.com:2096/sub/mysub123")

        api_url = core._xui_url("panel/api/inbounds/list")
        self.assertEqual(api_url, "https://panel.speed-ping.com:2053/panel-path/panel/api/inbounds/list")

        # Update XUI config dynamically
        core.update_xui_config("xui_sub_server_url", "https://sub.speed-ping.shop:2096")
        new_sub_link = core._subscription_url("mysub123")
        self.assertEqual(new_sub_link, "https://sub.speed-ping.shop:2096/sub/mysub123")

    def test_domain_replacement_across_db_and_env(self):
        core.update_db_setting("xui_api_url", "https://panel.speed-ping.com:2053")
        core.update_db_setting("xui_sub_server_url", "https://sub.speed-ping.com:2096")
        core.update_db_setting("welcome_text", "خوش آمدید به https://speed-ping.com")
        core.update_db_setting("faq_text", "راهنمای اتصال به speed-ping.com")

        ok, msg = core.replace_domain_in_all_configs("speed-ping.com", "speed-ping.shop")
        self.assertTrue(ok)
        self.assertIn("speed-ping.shop", core.get_xui_api_url())
        self.assertIn("speed-ping.shop", core.get_xui_sub_server_url())
        self.assertIn("speed-ping.shop", core.get_db_setting("welcome_text"))
        self.assertIn("speed-ping.shop", core.get_db_setting("faq_text"))

        # Verify .env file was also updated
        with open(self.env_path, "r", encoding="utf-8") as f:
            env_txt = f.read()
        self.assertIn("speed-ping.shop", env_txt)
        self.assertNotIn("speed-ping.com", env_txt)

    def test_card_photo_setting_and_checkout(self):
        # Default card photo is empty
        self.assertEqual(core.get_db_setting("card_photo", ""), "")

        # Process photo upload
        msg = FakeMessage(photo=[FakePhotoSize("AgACAgIAAxkBAAI_test_photo_id")])
        sent_messages = []
        original_send_message = core.bot.send_message
        original_send_photo = getattr(core.bot, "send_photo", None)

        def mock_send_message(chat_id, text, *args, **kwargs):
            sent_messages.append(("text", chat_id, text))
            m = FakeMessage(text=text)
            return m

        def mock_send_photo(chat_id, photo, *args, **kwargs):
            sent_messages.append(("photo", chat_id, photo, kwargs.get("caption", "")))
            m = FakeMessage(text=kwargs.get("caption", ""))
            return m

        core.bot.send_message = mock_send_message
        core.bot.send_photo = mock_send_photo

        try:
            core.process_edit_card_image(msg)
            self.assertEqual(core.get_db_setting("card_photo"), "AgACAgIAAxkBAAI_test_photo_id")

            # Test checkout with card photo set
            plan = core.get_plan(1)
            core._start_card_checkout(123456789, 123456789, plan)
            
            # Last message should be a photo
            self.assertEqual(sent_messages[-1][0], "photo")
            self.assertEqual(sent_messages[-1][2], "AgACAgIAAxkBAAI_test_photo_id")
            self.assertIn("یک‌ماهه VIP", sent_messages[-1][3])
            self.assertIn("شماره کارت", sent_messages[-1][3])

            # Clear card photo (delete photo)
            core.update_db_setting("card_photo", "")
            core._start_card_checkout(123456789, 123456789, plan)

            # Now it should be sent as text message
            self.assertEqual(sent_messages[-1][0], "text")
            self.assertIn("یک‌ماهه VIP", sent_messages[-1][2])
            self.assertIn("شماره کارت", sent_messages[-1][2])

            # Test fallback if send_photo throws exception
            core.update_db_setting("card_photo", "invalid_expired_photo_id")
            def failing_send_photo(*args, **kwargs):
                raise RuntimeError("Telegram API error: file not found")
            core.bot.send_photo = failing_send_photo
            
            core._start_card_checkout(123456789, 123456789, plan)
            # Should have gracefully fallen back to send_message
            self.assertEqual(sent_messages[-1][0], "text")
            self.assertIn("یک‌ماهه VIP", sent_messages[-1][2])

        finally:
            core.bot.send_message = original_send_message
            if original_send_photo:
                core.bot.send_photo = original_send_photo


if __name__ == "__main__":
    unittest.main()
