#!/usr/bin/env python3
"""SpeedyBot CLI Database Restore Utility.

Safely restores an SQLite backup into the active SpeedyBot database.
Can be run interactively or by passing the path to a .db backup file.

Usage:
    python restore.py [path_to_backup.db] [--latest] [-y|--yes]
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

# Ensure repository root is in python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from speedybot import backup_manager, env_manager


def check_service_status(service_name="xui-bot.service"):
    """Check if the systemd service is active."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        res = subprocess.run(
            ["systemctl", "is-active", "--quiet", service_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        return False


def restart_service(service_name="xui-bot.service"):
    """Restart the systemd service if running as root."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        subprocess.run(["systemctl", "restart", service_name], check=True)
        return True
    except Exception as e:
        print(f"[WARN] Failed to restart service {service_name}: {e}")
        return False


def format_size(bytes_num):
    """Format bytes into readable string."""
    if bytes_num < 1024:
        return f"{bytes_num} B"
    if bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    return f"{bytes_num / (1024 * 1024):.2f} MB"


def main():
    parser = argparse.ArgumentParser(description="SpeedyBot SQLite Database Restore Utility")
    parser.add_argument("backup_file", nargs="?", default=None, help="Path to SQLite backup (.db) file")
    parser.add_argument("--latest", action="store_true", help="Restore the latest available backup automatically")
    parser.add_argument("-y", "--yes", action="store_true", help="Confirm restoration without interactive prompt")
    parser.add_argument("--target", default="speedping.db", help="Target SQLite database file (default: speedping.db)")
    args = parser.parse_args()

    target_db = args.target
    backup_file_path = args.backup_file

    print("==================================================")
    print("      SpeedyBot Database Restore Tool             ")
    print("      ابزار بازیابی پایگاه داده ربات SpeedyBot      ")
    print("==================================================")

    # 1. Determine backup file
    if args.latest:
        backups = backup_manager.list_available_backups("backups")
        if not backups:
            print("[ERROR] No backups found in backups/ directory.")
            print("[خطا] هیچ فایل بکاپی در مسیر backups یافت نشد.")
            sys.exit(1)
        backup_file_path = backups[0]["path"]
        print(f"[INFO] Selected latest backup: {backup_file_path}")

    elif not backup_file_path:
        backups = backup_manager.list_available_backups("backups")
        if not backups:
            print("[WARN] No backups found in backups/ directory.")
            print("لطفاً مسیر فایل بکاپ را به صورت مستقیم وارد نمایید:")
            try:
                entered = input("Path to backup file (or 'q' to quit): ").strip()
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)
            if not entered or entered.lower() in ("q", "quit", "exit"):
                sys.exit(0)
            backup_file_path = entered
        else:
            print("\nAvailable backups found on this server:")
            print("فایل‌های پشتیبان یافت‌شده روی این سرور:")
            print("--------------------------------------------------")
            for idx, b in enumerate(backups[:15], 1):
                sz = format_size(b["size_bytes"])
                print(f" [{idx:2d}] {b['name']} ({sz}) - {b['mtime_str']}")
                print(f"      Path: {b['path']}")
            print("--------------------------------------------------")
            try:
                choice = input("Enter backup number or file path [1]: ").strip()
            except (KeyboardInterrupt, EOFError):
                sys.exit(0)

            if not choice:
                backup_file_path = backups[0]["path"]
            elif choice.isdigit() and 1 <= int(choice) <= len(backups):
                backup_file_path = backups[int(choice) - 1]["path"]
            elif choice.lower() in ("q", "quit", "exit"):
                sys.exit(0)
            else:
                backup_file_path = choice

    # 2. Validate selected backup file
    print(f"\n[INFO] Validating backup: {backup_file_path} ...")
    valid, msg, stats = backup_manager.validate_database_file(backup_file_path)
    if not valid:
        print(f"[ERROR] Invalid backup file: {msg}")
        print(f"[خطا] فایل بکاپ معتبر نیست: {msg}")
        sys.exit(1)

    print("[OK] Backup file integrity check passed!")
    print(f"     • Users (کاربران): {stats.get('users', 0):,}")
    print(f"     • Orders (تراکنش‌ها): {stats.get('orders', 0):,}")
    print(f"     • Plans (پلان‌ها): {stats.get('plans', 0):,}")
    print(f"     • Size (حجم فایل): {format_size(stats.get('size_bytes', 0))}")

    # 3. Confirmation prompt
    if not args.yes:
        print("\n⚠️  WARNING: Restoring will overwrite the current database!")
        print("⚠️  هشدار: عملیات بازیابی، پایگاه داده فعلی را بازنویسی خواهد کرد.")
        print("    (یک نسخه پشتیبان اضطراری از داده‌های فعلی به طور خودکار گرفته خواهد شد)")
        try:
            confirm = input("\nProceed with restore? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

        if confirm not in ("y", "yes"):
            print("Restoration cancelled.")
            sys.exit(0)

    # 4. Check service status
    service_active = check_service_status("xui-bot.service")
    if service_active:
        print("[INFO] Bot service 'xui-bot.service' is running.")

    # 5. Perform restoration
    print(f"\n[INFO] Restoring database into {target_db} ...")
    success, res_msg, restored_stats, safety_path = backup_manager.restore_database_from_file(
        backup_file_path,
        target_db=target_db,
        pre_restore_backup=True,
    )

    if not success:
        print(f"[ERROR] Restore failed: {res_msg}")
        print(f"[خطا] بازیابی با خطا مواجه شد: {res_msg}")
        sys.exit(1)

    print("[SUCCESS] Database restored successfully!")
    print("[موفقیت] پایگاه داده با موفقیت بازیابی شد!")
    if safety_path:
        print(f"[INFO] Pre-restore safety snapshot created at:\n       {safety_path}")

    # 6. Run package schema migrations
    try:
        from speedybot import storage
        storage.init_db()
        print("[OK] Schema migrations verified.")
    except Exception as e:
        print(f"[WARN] Schema migration check notice: {e}")

    # 7. Restart service if needed
    if service_active:
        print("[INFO] Restarting xui-bot.service ...")
        if restart_service("xui-bot.service"):
            print("[OK] Service restarted successfully.")
        else:
            print("[WARN] Please restart the service manually: systemctl restart xui-bot.service")
    else:
        print("\n[HINT] You can now start the bot using:")
        print("       ./run.sh  OR  systemctl start xui-bot.service")

    print("\nRestore operation completed.")


if __name__ == "__main__":
    main()
