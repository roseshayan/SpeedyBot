import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import Mock, patch

from speedybot import env_manager


# Exercise the real Telegram library without production credentials or an
# import-time migration against the developer's database / .env file.
_import_cwd = os.getcwd()
with tempfile.TemporaryDirectory() as _import_dir:
    with patch.dict(os.environ, {"BOT_TOKEN": "12345:TEST_TOKEN", "ADMIN_ID": "123456789"}):
        try:
            os.chdir(_import_dir)
            from speedybot import core
        finally:
            os.chdir(_import_cwd)


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
        env_patch = patch.dict(os.environ)
        env_patch.start()
        self.addCleanup(env_patch.stop)
        config_patch = patch.multiple(
            core, XUI_API_URL="", XUI_BASE_PATH="", XUI_BEARER_TOKEN="",
            XUI_SUB_SERVER_URL="", XUI_SUB_PATH="/sub/",
        )
        config_patch.start()
        self.addCleanup(config_patch.stop)
        
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

    def test_nested_client_response_preserves_identity_and_membership(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=200)
        response.json.return_value = {"success": True, "obj": {
            "client": {"email": "alice+one@example.com", "subId": "subscription", "totalGB": 1024},
            "inboundIds": [7, 9], "usedTraffic": 128,
        }}
        with patch.object(core.requests, "get", return_value=response) as get:
            client = core._get_client_data("alice+one@example.com", {}, None)
        self.assertEqual(client["totalGB"], 1024)
        self.assertEqual(client["inboundIds"], [7, 9])
        self.assertEqual(core._extract_subscription_id(client), "subscription")
        self.assertIn("alice%2Bone%40example.com", get.call_args.args[0])
        self.assertEqual(core._normalize_client_data({"email": "legacy"}), {"email": "legacy"})

    def test_safe_json_rejects_non_object_envelopes(self):
        for value in (None, [], "unexpected", 7):
            response = Mock()
            response.json.return_value = value
            self.assertEqual(core._safe_json(response), {})

    def test_update_sends_only_changed_fields(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=200)
        response.json.return_value = {"success": True}
        with patch.object(core.requests, "post", return_value=response) as post:
            with patch.object(core.requests, "get") as get:
                self.assertTrue(core._update_exported_client("alice", {"totalGB": 0, "enable": True}))
        self.assertEqual(post.call_args.kwargs["json"], {"totalGB": 0, "enable": True})
        get.assert_not_called()

    def test_topup_rejects_skipped_bulk_result(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=200)
        with patch.object(core, "_get_client_data", return_value={"totalGB": 1024}):
            with patch.object(core.requests, "post", return_value=response):
                response.json.return_value = {"success": True, "obj": {
                    "adjusted": 0, "skipped": [{"email": "alice", "reason": "client not found"}],
                }}
                with self.assertRaises(RuntimeError):
                    core.add_volume_xui_service("alice", 1)
                response.json.return_value = {"success": True, "obj": {"adjusted": 1, "skipped": []}}
                self.assertTrue(core.add_volume_xui_service("alice", 1))

    def test_failed_client_lookup_is_not_treated_as_missing_account(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=403, text="Forbidden", url="https://panel.example.com")
        response.json.return_value = {"success": False}
        with patch.object(core.requests, "get", return_value=response):
            with self.assertRaises(RuntimeError):
                core._get_client_data("alice", {}, None)

    def test_new_protocol_share_links_survive_filtering(self):
        from speedybot import corepatch
        links = ["tuic://user:password@example.com:443", "tg://proxy?server=example.com&port=443&secret=123"]
        self.assertEqual(core._clean_proxy_links(links), links)
        self.assertEqual(corepatch._decode_subscription_text("\n".join(links)), links)

    def test_zero_group_affected_count_is_not_reported_as_successful_updates(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=200)
        response.json.return_value = {"success": True, "obj": {"affected": 0}}
        with patch.object(core, "_xui_ensure_group", return_value=True):
            with patch.object(core.requests, "post", return_value=response):
                self.assertEqual(core._xui_assign_group_bulk(["alice"], "Customers"), 0)

    def test_error_diagnostics_redact_token(self):
        core.update_db_setting("xui_bearer_token", "private-token")
        response = Mock(status_code=403, text="private-token rejected", url="https://panel/private-token")
        error = core._xui_response_error(response, "read")
        self.assertNotIn("private-token", error)
        self.assertIn("[REDACTED]", error)

    def test_ownership_covers_paid_trial_and_linked_accounts(self):
        con = sqlite3.connect("speedping.db")
        con.execute("CREATE TABLE trial_services(user_id INTEGER, email TEXT, status TEXT)")
        con.execute("CREATE TABLE linked_services(user_id INTEGER, email TEXT)")
        con.execute("INSERT INTO transactions(user_id,service_email,status) VALUES (1,'paid','APPROVED')")
        con.execute("INSERT INTO transactions(user_id,service_email,status) VALUES (1,'pending','PENDING')")
        con.execute("INSERT INTO trial_services VALUES (1,'trial','ACTIVE')")
        con.execute("INSERT INTO linked_services VALUES (1,'linked')")
        con.commit()
        con.close()
        for email in ("paid", "trial", "linked"):
            self.assertTrue(core._user_owns_service(1, email))
            self.assertFalse(core._user_owns_service(2, email))
        self.assertFalse(core._user_owns_service(1, "pending"))

    def test_shared_subscription_requires_ownership_of_every_client(self):
        core.update_db_setting("xui_api_url", "https://panel.example.com")
        response = Mock(status_code=200)
        response.json.return_value = {"success": True, "obj": [
            {"client": {"email": "owned"}}, {"client": {"email": "someone-else"}},
        ]}
        with patch.object(core.requests, "get", return_value=response):
            with patch.object(core, "_user_owns_service", side_effect=lambda uid, email: email == "owned"):
                self.assertFalse(core._user_owns_subscription(1, "shared-sub-id"))

    def test_credential_callback_denied_before_fetching_links(self):
        call = Mock(data="getlinks:dir:someone-else")
        call.from_user.id = 1
        call.message.chat.id = 1
        with patch.object(core, "_user_owns_service", return_value=False):
            with patch.object(core.bot, "answer_callback_query") as answer:
                with patch.object(core.requests, "get") as get:
                    with patch.object(core.bot, "send_message") as send:
                        core.handle_account_get_links(call)
        answer.assert_called_once()
        get.assert_not_called()
        send.assert_not_called()

    def test_successful_subscription_callback_is_acknowledged(self):
        call = Mock(data="getlinks:sub:owned-subscription")
        with patch.object(core, "_authorize_service_callback", return_value=True):
            with patch.object(core, "_subscription_url", return_value="https://sub.example.com/sub/owned"):
                with patch.object(core.bot, "answer_callback_query") as answer:
                    with patch.object(core.bot, "send_message"):
                        core.handle_account_get_links(call)
        answer.assert_called_once_with(call.id)

    def test_stale_invoice_decisions_cannot_override_another_admin_claim(self):
        con = sqlite3.connect("speedping.db")
        con.execute("CREATE TABLE discount_redemptions(tx_id INTEGER, status TEXT)")
        con.execute("INSERT INTO transactions(id,user_id,status,kind) VALUES (1,1,'PENDING','RENEWAL')")
        con.execute("INSERT INTO discount_redemptions VALUES (1,'RESERVED')")
        con.commit()
        con.close()

        class RacingConnection:
            def __init__(self):
                self.connection = core._db_connect()

            def execute(self, sql, args=()):
                if sql.startswith("UPDATE transactions SET status"):
                    # Another admin wins after the handler's SELECT and before
                    # its UPDATE. Use a real independent SQLite connection.
                    with closing(sqlite3.connect("speedping.db")) as winner:
                        winner.execute("UPDATE transactions SET status='PROCESSING' WHERE id=1")
                        winner.commit()
                return self.connection.execute(sql, args)

            def __getattr__(self, name):
                return getattr(self.connection, name)

        for action in ("approve", "reject"):
            with self.subTest(action=action):
                with closing(sqlite3.connect("speedping.db")) as reset:
                    reset.execute("UPDATE transactions SET status='PENDING' WHERE id=1")
                    reset.commit()
                stale_connection = RacingConnection()
                with patch.object(core, "_db_connect", return_value=stale_connection):
                    with patch.object(core, "finalize_service_transaction") as finalize:
                        with patch.object(core.bot, "answer_callback_query"):
                            with patch.object(core.bot, "send_message") as send:
                                core.handle_invoice_decision(Mock(), action, 1)
                finalize.assert_not_called()
                send.assert_not_called()
                with closing(sqlite3.connect("speedping.db")) as check:
                    self.assertEqual(check.execute("SELECT status FROM transactions WHERE id=1").fetchone()[0], "PROCESSING")
                    self.assertEqual(check.execute("SELECT status FROM discount_redemptions WHERE tx_id=1").fetchone()[0], "RESERVED")

    def test_backup_delivery_continues_after_one_admin_fails(self):
        with open("backup.db", "wb") as backup:
            backup.write(b"test backup")
        with patch.object(core, "get_admin_ids", return_value=[1, 2]):
            with patch.object(core.bot, "send_document", side_effect=[RuntimeError("blocked"), None]) as send:
                with self.assertLogs(core.logger, level="ERROR"):
                    self.assertEqual(core.send_backup_file_to_admins("backup.db"), 1)
        self.assertEqual([call.args[0] for call in send.call_args_list], [1, 2])

    def test_backup_filenames_do_not_collide_with_identical_timestamps(self):
        with patch.object(core, "datetime") as clock:
            clock.now.return_value.strftime.return_value = "same-instant"
            first = core.create_database_backup()
            second = core.create_database_backup()
        self.assertNotEqual(first, second)
        self.assertTrue(os.path.isfile(first))
        self.assertTrue(os.path.isfile(second))

    def test_restart_does_not_replay_uncertain_renewal_or_topup(self):
        con = sqlite3.connect("speedping.db")
        for tx_id, kind in ((1, "NEW"), (2, "RENEWAL"), (3, "VOLUME")):
            con.execute("INSERT INTO transactions(id,status,kind) VALUES (?,'PROCESSING',?)", (tx_id, kind))
        con.commit()
        con.close()
        with patch.object(core, "finalize_service_transaction") as finalize:
            with patch.object(core, "notify_admins") as notify:
                core.recover_processing_transactions()
        finalize.assert_called_once_with(1)
        self.assertEqual(notify.call_count, 2)
        con = sqlite3.connect("speedping.db")
        statuses = dict(con.execute("SELECT id,status FROM transactions"))
        con.close()
        self.assertEqual(statuses, {1: "PROCESSING", 2: "ISSUE", 3: "ISSUE"})

    def test_retry_requires_review_confirmation_for_topup(self):
        con = sqlite3.connect("speedping.db")
        con.execute("INSERT INTO transactions(id,status,kind) VALUES (1,'ISSUE','VOLUME')")
        con.commit()
        con.close()
        call = Mock()
        with patch.object(core.bot, "answer_callback_query"):
            with patch.object(core.bot, "send_message") as send:
                with patch.object(core, "finalize_service_transaction") as finalize:
                    core.retry_issue_transaction(call, 1)
                    finalize.assert_not_called()
                    self.assertIn("دوباره", send.call_args.args[1])
                    core.retry_issue_transaction(call, 1, confirmed=True)
                    finalize.assert_called_once_with(1)

    def test_large_restore_upload_is_rejected_before_download(self):
        message = Mock(text="")
        message.document.file_name = "backup.db"
        message.document.file_size = 21 * 1024 * 1024
        with patch.object(core, "is_admin", return_value=True):
            with patch.object(core.bot, "send_message") as send:
                with patch.object(core.bot, "get_file") as get_file:
                    core.process_admin_backup_restore(message)
        get_file.assert_not_called()
        self.assertIn("۲۰", send.call_args.args[1])

    def test_domain_replacement_preserves_domain_shaped_secrets(self):
        with open(self.env_path, "a", encoding="utf-8") as config:
            config.write("export OTHER_SECRET='keep.speed-ping.com.secret'\n")
        core.update_db_setting("xui_api_url", "https://panel.speed-ping.com")
        core.replace_domain_in_all_configs("speed-ping.com", "speed-ping.shop")
        with open(self.env_path, encoding="utf-8") as config:
            content = config.read()
        self.assertIn("keep.speed-ping.com.secret", content)

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
