"""Backup and restore management for SpeedyBot SQLite databases.

Provides safe validation, online database backups, safety snapshots,
and comprehensive restore operations for both in-bot and CLI tools.
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple


REQUIRED_TABLES = {"users", "settings", "plans"}


def validate_database_file(db_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate SQLite database integrity and verify essential SpeedyBot tables.

    Returns:
        (is_valid, message, stats_dict)
    """
    path = Path(db_path)
    if not path.is_file():
        return False, f"فایل دیتابیس یافت نشد: {db_path}", {}

    if path.stat().st_size == 0:
        return False, "فایل ارسالی خالی است (حجم صفر بایت).", {}

    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=15)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Integrity check
        cursor.execute("PRAGMA integrity_check;")
        rows = cursor.fetchall()
        if not rows or rows[0][0].lower() != "ok":
            return False, f"تست یکپارچگی SQLite ناموفق بود: {rows[0][0] if rows else 'Unknown error'}", {}

        # 2. Check essential tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {r[0] for r in cursor.fetchall()}
        missing = REQUIRED_TABLES - tables
        if missing:
            return False, f"جداول ضروری ربات در این فایل موجود نیست: {', '.join(sorted(missing))}", {}

        # 3. Read stats
        stats = {
            "users": 0,
            "orders": 0,
            "plans": 0,
            "settings": 0,
            "size_bytes": path.stat().st_size,
            "tables": sorted(tables),
        }

        for table, key in [
            ("users", "users"),
            ("transactions", "orders"),
            ("plans", "plans"),
            ("settings", "settings"),
        ]:
            if table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[key] = cursor.fetchone()[0]
                except Exception:
                    pass

        return True, "فایل پایگاه داده معتبر و سالم است.", stats

    except sqlite3.DatabaseError as exc:
        return False, f"فایل ارسالی یک دیتابیس معتبر SQLite نیست: {exc}", {}
    except Exception as exc:
        return False, f"خطا در بررسی فایل دیتابیس: {exc}", {}
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_database_stats(db_path: str = "speedping.db") -> Dict[str, Any]:
    """Retrieve statistical summary of an existing SQLite database."""
    valid, _, stats = validate_database_file(db_path)
    if valid:
        return stats
    return {"users": 0, "orders": 0, "plans": 0, "settings": 0, "size_bytes": 0}


def create_safety_snapshot(
    source_db: str = "speedping.db",
    prefix: str = "pre-restore",
    dest_dir: Optional[str] = None
) -> Optional[str]:
    """Create a consistent online backup snapshot of current database before modifications.

    Returns the path to the created snapshot, or None if source does not exist.
    """
    src_path = Path(source_db)
    if not src_path.is_file():
        return None

    target_root = Path(dest_dir) if dest_dir else Path("backups") / prefix
    target_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target_file = target_root / f"speedping-{prefix}-{stamp}.db"

    src_conn = sqlite3.connect(str(src_path), timeout=30)
    dst_conn = sqlite3.connect(str(target_file))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    return str(target_file)


def restore_database_from_file(
    backup_path: str,
    target_db: str = "speedping.db",
    pre_restore_backup: bool = True
) -> Tuple[bool, str, Dict[str, Any], Optional[str]]:
    """Atomically restore the target database from a verified backup file.

    Parameters:
        backup_path: Path to the validated backup SQLite file.
        target_db: Destination SQLite database file (default: speedping.db).
        pre_restore_backup: Whether to create an emergency safety snapshot before restoring.

    Returns:
        (success, message, restored_stats, safety_snapshot_path)
    """
    # 1. Validate source backup first
    valid, val_msg, stats = validate_database_file(backup_path)
    if not valid:
        return False, val_msg, {}, None

    # 2. Safety snapshot
    safety_path: Optional[str] = None
    if pre_restore_backup and os.path.isfile(target_db):
        try:
            safety_path = create_safety_snapshot(target_db, prefix="pre-restore")
        except Exception as exc:
            return False, f"ایجاد نسخه پشتیبان اضطراری با خطا مواجه شد: {exc}", {}, None

    # 3. Perform atomic online page-level restore
    try:
        src_conn = sqlite3.connect(backup_path, timeout=30)
        dst_conn = sqlite3.connect(target_db, timeout=30)
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
            src_conn.close()

        # Checkpoint WAL if present
        checkpoint_conn = sqlite3.connect(target_db, timeout=30)
        try:
            checkpoint_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        except Exception:
            pass
        finally:
            checkpoint_conn.close()

    except Exception as exc:
        return False, f"خطا در بازنویسی صفحات دیتابیس: {exc}", {}, safety_path

    # 4. Remove leftover disconnected WAL files if any
    for ext in ("-wal", "-shm"):
        wal_file = Path(f"{target_db}{ext}")
        if wal_file.is_file():
            try:
                wal_file.unlink()
            except Exception:
                pass

    # 5. Verify restored database
    restored_valid, restored_msg, restored_stats = validate_database_file(target_db)
    if not restored_valid:
        return False, f"دیتابیس پس از بازیابی معتبر نبود: {restored_msg}", {}, safety_path

    return True, "بازیابی پایگاه داده با موفقیت به پایان رسید.", restored_stats, safety_path


def list_available_backups(search_dir: str = "backups") -> List[Dict[str, Any]]:
    """Scan and list all valid SQLite backups found under the backup tree."""
    root = Path(search_dir)
    if not root.is_dir():
        return []

    results: List[Dict[str, Any]] = []
    seen = set()

    # Search for .db files in backups, backups/auto, backups/pre-restore, backups/deploy-*
    for p in root.glob("**/*.db"):
        if not p.is_file() or p.name.endswith(("-wal", "-shm")):
            continue
        canon = str(p.resolve())
        if canon in seen:
            continue
        seen.add(canon)

        try:
            stat = p.stat()
            results.append({
                "path": str(p),
                "name": p.name,
                "size_bytes": stat.st_size,
                "mtime": stat.st_mtime,
                "mtime_str": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results
