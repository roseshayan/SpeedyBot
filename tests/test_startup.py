"""Boot the complete real Telegram handler stack without external services."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class StartupTests(unittest.TestCase):
    def test_fresh_database_and_handlers_initialize_with_real_dependencies(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env.update({
            "PYTHONPATH": str(repo), "BOT_TOKEN": "12345:TEST_TOKEN",
            "ADMIN_ID": "123456789", "XUI_API_URL": "", "XUI_BASE_PATH": "",
            "XUI_BEARER_TOKEN": "", "XUI_SUB_SERVER_URL": "", "XUI_SUB_PATH": "/sub/",
        })
        script = """
import sqlite3
import speedybot
from speedybot import core, trial, ui
speedybot.install(core)
assert len(core.bot.message_handlers) > 10
assert len(core.bot.callback_query_handlers) > 10
assert core.main_menu().to_json()
assert ui.admin_menu().to_json()
db = sqlite3.connect('speedping.db')
assert db.execute('select count(*) from plans').fetchone()[0] > 0
assert db.execute("select value from settings where key='brand_name'").fetchone()
db.close()
trial.recover_interrupted()
print('startup ok')
"""
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=folder, env=env,
                capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("startup ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
