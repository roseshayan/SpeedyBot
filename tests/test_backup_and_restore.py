"""Unit tests for SpeedyBot backup and restore management."""

import os
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest

from speedybot import backup_manager


class BackupManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)

        # Create a valid test database
        self.valid_db_path = self.dir_path / "valid.db"
        self._init_sample_db(self.valid_db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _init_sample_db(self, path, users_count=5, orders_count=3):
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("CREATE TABLE plans (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
        conn.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, user_id INTEGER, price INTEGER)")

        for i in range(1, users_count + 1):
            conn.execute("INSERT INTO users (id, username) VALUES (?, ?)", (i, f"user_{i}"))

        for i in range(1, orders_count + 1):
            conn.execute("INSERT INTO transactions (id, user_id, price) VALUES (?, ?, ?)", (i, 1, 1000 * i))

        conn.execute("INSERT INTO plans (id, name, price) VALUES (1, 'Pro Plan', 50000)")
        conn.execute("INSERT INTO settings (key, value) VALUES ('brand_name', 'TestBrand')")

        conn.commit()
        conn.close()

    def test_validate_valid_database(self):
        valid, msg, stats = backup_manager.validate_database_file(str(self.valid_db_path))
        self.assertTrue(valid)
        self.assertEqual(stats["users"], 5)
        self.assertEqual(stats["orders"], 3)
        self.assertEqual(stats["plans"], 1)
        self.assertGreater(stats["size_bytes"], 0)

    def test_validate_nonexistent_file(self):
        valid, msg, stats = backup_manager.validate_database_file(str(self.dir_path / "missing.db"))
        self.assertFalse(valid)
        self.assertIn("یافت نشد", msg)

    def test_validate_empty_file(self):
        empty_file = self.dir_path / "empty.db"
        empty_file.touch()
        valid, msg, stats = backup_manager.validate_database_file(str(empty_file))
        self.assertFalse(valid)
        self.assertIn("خالی است", msg)

    def test_validate_corrupt_file(self):
        corrupt_file = self.dir_path / "corrupt.db"
        with open(corrupt_file, "wb") as f:
            f.write(b"NOT A REAL SQLITE FILE CONTENT AT ALL")
        valid, msg, stats = backup_manager.validate_database_file(str(corrupt_file))
        self.assertFalse(valid)

    def test_validate_missing_essential_tables(self):
        incomplete_file = self.dir_path / "incomplete.db"
        conn = sqlite3.connect(str(incomplete_file))
        conn.execute("CREATE TABLE unrelated_table (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        valid, msg, stats = backup_manager.validate_database_file(str(incomplete_file))
        self.assertFalse(valid)
        self.assertIn("جداول ضروری", msg)

    def test_safety_snapshot_creation(self):
        snapshot_dir = self.dir_path / "snapshots"
        snapshot_path = backup_manager.create_safety_snapshot(
            source_db=str(self.valid_db_path),
            prefix="test-safety",
            dest_dir=str(snapshot_dir)
        )
        self.assertIsNotNone(snapshot_path)
        self.assertTrue(os.path.isfile(snapshot_path))

        valid, _, stats = backup_manager.validate_database_file(snapshot_path)
        self.assertTrue(valid)
        self.assertEqual(stats["users"], 5)

    def test_restore_database_from_file(self):
        # Create target database with older data
        target_db = self.dir_path / "target.db"
        self._init_sample_db(target_db, users_count=1, orders_count=1)

        # Create source backup with 10 users
        backup_db = self.dir_path / "backup_10.db"
        self._init_sample_db(backup_db, users_count=10, orders_count=5)

        success, msg, restored_stats, safety_path = backup_manager.restore_database_from_file(
            str(backup_db),
            target_db=str(target_db),
            pre_restore_backup=True
        )

        self.assertTrue(success)
        self.assertEqual(restored_stats["users"], 10)
        self.assertEqual(restored_stats["orders"], 5)

        # Verify the actual target file
        valid, _, verify_stats = backup_manager.validate_database_file(str(target_db))
        self.assertTrue(valid)
        self.assertEqual(verify_stats["users"], 10)

        # Verify safety snapshot was created
        self.assertIsNotNone(safety_path)
        self.assertTrue(os.path.isfile(safety_path))

    def test_list_available_backups(self):
        backup_dir = self.dir_path / "backups"
        auto_dir = backup_dir / "auto"
        auto_dir.mkdir(parents=True)

        b1 = auto_dir / "speedping-20261009-100000.db"
        b2 = auto_dir / "speedping-20261009-120000.db"
        self._init_sample_db(b1)
        time.sleep(0.05)
        self._init_sample_db(b2)

        listed = backup_manager.list_available_backups(str(backup_dir))
        self.assertEqual(len(listed), 2)
        # Should be sorted newest first
        self.assertEqual(listed[0]["name"], b2.name)
        self.assertEqual(listed[1]["name"], b1.name)


if __name__ == "__main__":
    unittest.main()
