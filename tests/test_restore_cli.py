"""Restore must quiesce only the installed database and resume on failure."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import restore


class RestoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        root_patch = patch.object(restore, "ROOT_DIR", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.target = self.root / "speedping.db"
        self.result = (True, "restored", {"users": 1}, "safety.db")

    def test_active_bot_is_stopped_before_restore_and_restarted(self):
        events = []
        with (
            patch.object(restore, "check_service_status", return_value=True),
            patch.object(restore.subprocess, "run", side_effect=lambda *a, **k: events.append("stop")),
            patch.object(restore.backup_manager, "restore_database_from_file", side_effect=lambda *a, **k: (events.append("restore"), self.result)[1]),
            patch.object(restore, "restart_service", side_effect=lambda: (events.append("restart"), True)[1]),
        ):
            self.assertEqual(restore.restore_with_service_control("backup.db", self.target), self.result)
        self.assertEqual(events, ["stop", "restore", "restart"])

    def test_stop_failure_does_not_touch_database(self):
        with (
            patch.object(restore, "check_service_status", return_value=True),
            patch.object(restore.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "systemctl")),
            patch.object(restore.backup_manager, "restore_database_from_file") as replace,
            patch.object(restore, "restart_service") as restart,
        ):
            result = restore.restore_with_service_control("backup.db", self.target)
        self.assertFalse(result[0])
        replace.assert_not_called()
        restart.assert_not_called()

    def test_unknown_service_status_does_not_touch_database(self):
        with (
            patch.object(restore, "check_service_status", side_effect=RuntimeError("status timeout")),
            patch.object(restore.backup_manager, "restore_database_from_file") as replace,
        ):
            result = restore.restore_with_service_control("backup.db", self.target)
        self.assertFalse(result[0])
        replace.assert_not_called()

    def test_service_query_failure_is_not_treated_as_inactive(self):
        with (
            patch.object(restore.sys, "platform", "linux"),
            patch.object(restore.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)),
        ):
            with self.assertRaisesRegex(RuntimeError, "systemctl exit 1"):
                restore.check_service_status()

    def test_service_auto_restart_state_is_quiesced_as_active(self):
        with (
            patch.object(restore.sys, "platform", "linux"),
            patch.object(restore.subprocess, "run", return_value=subprocess.CompletedProcess([], 3, stdout="activating\n")),
        ):
            self.assertTrue(restore.check_service_status())

    def test_restore_error_still_restarts_service(self):
        with (
            patch.object(restore, "check_service_status", return_value=True),
            patch.object(restore.subprocess, "run"),
            patch.object(restore.backup_manager, "restore_database_from_file", side_effect=OSError("disk failed")),
            patch.object(restore, "restart_service", return_value=True) as restart,
        ):
            with self.assertRaisesRegex(OSError, "disk failed"):
                restore.restore_with_service_control("backup.db", self.target)
        restart.assert_called_once()

    def test_custom_target_does_not_control_installed_service(self):
        with (
            patch.object(restore, "check_service_status") as status,
            patch.object(restore.backup_manager, "restore_database_from_file", return_value=self.result),
            patch.object(restore, "restart_service") as restart,
        ):
            restore.restore_with_service_control("backup.db", self.root / "recovered.db")
        status.assert_not_called()
        restart.assert_not_called()

    def test_restart_failure_reports_unsuccessful_operation(self):
        with (
            patch.object(restore, "check_service_status", return_value=True),
            patch.object(restore.subprocess, "run"),
            patch.object(restore.backup_manager, "restore_database_from_file", return_value=self.result),
            patch.object(restore, "restart_service", return_value=False),
        ):
            result = restore.restore_with_service_control("backup.db", self.target)
        self.assertFalse(result[0])
        self.assertEqual(result[3], "safety.db")
        self.assertIn("Service restart failed", result[1])


if __name__ == "__main__":
    unittest.main()
