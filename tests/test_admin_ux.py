import unittest
from types import SimpleNamespace

from telebot.handler_backends import ContinueHandling

from speedybot import admin_ux
from speedybot import context as C


class FakeBot:
    def __init__(self):
        self.cleared = []
        self.answered = []

    def clear_step_handler_by_chat_id(self, chat_id):
        self.cleared.append(int(chat_id))

    def answer_callback_query(self, callback_id, *args, **kwargs):
        self.answered.append(str(callback_id))


class FakeCore:
    def __init__(self):
        self.bot = FakeBot()

    def is_admin(self, uid):
        return int(uid) == 1


class AdminUXTests(unittest.TestCase):
    def setUp(self):
        self.core = FakeCore()
        C.configure(self.core)

    def call(self, data, callback_id="cb"):
        return SimpleNamespace(
            id=callback_id,
            data=data,
            from_user=SimpleNamespace(id=1),
            message=SimpleNamespace(chat=SimpleNamespace(id=100)),
        )

    def test_plan_edit_is_intercepted_as_fresh_wizard(self):
        self.assertTrue(admin_ux._is_wizard(self.call("admin:plan_edit")))

    def test_navigation_clears_stale_next_step(self):
        result = admin_ux.state_guard(self.call("admin:plans"))
        self.assertIsInstance(result, ContinueHandling)
        self.assertEqual(self.core.bot.cleared, [100])

    def test_legacy_menu_callback_is_acknowledged(self):
        admin_ux.state_guard(self.call("admin:plans", "plans-cb"))
        self.assertEqual(self.core.bot.answered, ["plans-cb"])

    def test_wizard_callback_is_not_double_acknowledged_by_guard(self):
        admin_ux.state_guard(self.call("admin:plan_edit", "edit-cb"))
        self.assertEqual(self.core.bot.cleared, [100])
        self.assertEqual(self.core.bot.answered, [])

    def test_starting_same_wizard_twice_always_clears_old_state(self):
        call = self.call("admin:plan_edit")
        admin_ux.state_guard(call)
        admin_ux.state_guard(call)
        self.assertEqual(self.core.bot.cleared, [100, 100])


if __name__ == "__main__":
    unittest.main()
