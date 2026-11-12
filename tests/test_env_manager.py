import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from speedybot import env_manager


class EnvironmentFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / ".env"

    def test_secret_round_trip_with_quotes_and_shell_characters(self):
        secret = "it's a token with $dollars `commands` \\ # and = signs"
        env_manager.update_env_file({"ROUND_TRIP_SECRET": secret}, self.path)
        with patch.dict(os.environ, {}, clear=True):
            loaded = env_manager.load_env_file(self.path)
            self.assertEqual(loaded["ROUND_TRIP_SECRET"], secret)
            self.assertEqual(os.environ["ROUND_TRIP_SECRET"], secret)

    def test_append_preserves_last_line_without_newline(self):
        self.path.write_text("# Keep this comment\nEXISTING='keep'", encoding="utf-8")
        env_manager.update_env_file({"ADDED": "new"}, self.path)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env_manager.load_env_file(self.path), {"EXISTING": "keep", "ADDED": "new"})

    def test_invalid_names_and_multiline_values_do_not_modify_file(self):
        original = "TOKEN='original'\n"
        self.path.write_text(original, encoding="utf-8")
        for updates in ({"BAD;command": "x"}, {"TOKEN": "x\nexport OTHER='bad'"}, {"TOKEN": "x\x00"}):
            with self.assertRaises(ValueError):
                env_manager.update_env_file(updates, self.path)
            self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_failed_replace_keeps_previous_file_and_removes_temporary(self):
        self.path.write_text("TOKEN='original'\n", encoding="utf-8")
        with patch.object(env_manager.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                env_manager.update_env_file({"TOKEN": "changed"}, self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "TOKEN='original'\n")
        self.assertEqual([p.name for p in self.path.parent.iterdir()], [".env"])

    def test_process_environment_takes_precedence(self):
        self.path.write_text("TOKEN='from-file'\n", encoding="utf-8")
        with patch.dict(os.environ, {"TOKEN": "from-process"}, clear=True):
            self.assertEqual(env_manager.load_env_file(self.path)["TOKEN"], "from-file")
            self.assertEqual(os.environ["TOKEN"], "from-process")

    def test_load_legacy_bash_octal_utf8_path(self):
        # Bash printf %q emits UTF-8 octal bytes in the C locale.
        self.path.write_text(r"export LEGACY_PATH=$'/\331\205\330\263\333\214\330\261'" + "\n", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env_manager.load_env_file(self.path)["LEGACY_PATH"], "/مسیر")

    def test_legacy_bash_hex_and_unicode_escapes(self):
        values = {
            r"$'/\xD9\x85\xD8\xB3\xDB\x8C\xD8\xB1'": "/مسیر",
            r"$'\u0645\u0633\u06CC\u0631 \U0001F680'": "مسیر 🚀",
            r"$'it\'s \\quoted\tvalue\E'": "it's \\quoted\tvalue\x1b",
            r"$'\cA\c?'": "\x01\x7f",
            r"$'line\nother'": "line\nother",
        }
        for quoted, expected in values.items():
            with self.subTest(quoted=quoted):
                self.assertEqual(env_manager._decode_value(quoted), expected)

    def test_legacy_bash_values_never_execute_expansions(self):
        value = r"$'$(touch marker) `commands` $VARIABLE'"
        self.assertEqual(env_manager._decode_value(value), "$(touch marker) `commands` $VARIABLE")

    def test_malformed_legacy_bash_values_are_preserved(self):
        for value in ("$'", "$'unclosed", "$'unexpected'quote'", r"$'\x'", r"$'\uD800'", r"$'\U00110000'", r"$'\xFF'", r"$'\000'"):
            with self.subTest(value=value):
                self.assertEqual(env_manager._decode_value(value), value)


if __name__ == "__main__":
    unittest.main()
