import re
import threading
import time

from . import context as C


VERSION_URL = "https://raw.githubusercontent.com/roseshayan/SpeedyBot/main/VERSION.txt"
REPOSITORY_URL = "https://github.com/roseshayan/SpeedyBot"
_UPDATE_THREAD = None
_UPDATE_LOCK = threading.Lock()


def _version_tuple(value):
    text = str(value or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+", text):
        return None
    return tuple(int(part) for part in text.split("."))


def is_newer(remote, local):
    remote_tuple = _version_tuple(remote)
    local_tuple = _version_tuple(local)
    return bool(remote_tuple and local_tuple and remote_tuple > local_tuple)


def check_once():
    if C.setting("update_notifications_enabled", "1") != "1":
        return False

    from . import VERSION

    try:
        response = C.CORE.requests.get(
            VERSION_URL,
            headers={"Accept": "text/plain", "User-Agent": f"SpeedyBot/{VERSION}"},
            timeout=10,
        )
        if response.status_code != 200:
            return False
        remote = str(response.text or "").strip().lstrip("vV")
    except Exception:
        # Update checks are advisory. Network/GitHub failures must never create
        # another stream of admin alerts or affect the bot runtime.
        return False

    if not is_newer(remote, VERSION):
        return False
    if C.setting("last_update_notified_version", "") == remote:
        return False

    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    markup.add(C.inline("🔗 مشاهده پروژه و تغییرات", url=REPOSITORY_URL, style_name="primary"))
    C.CORE.notify_admins(
        "🚀 <b>آپدیت جدید SpeedyBot منتشر شد</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📌 نسخه نصب‌شده: <code>{VERSION}</code>\n"
        f"✨ نسخه جدید: <code>{remote}</code>\n\n"
        "برای بروزرسانی، داخل پوشه پروژه دستور زیر را اجرا کنید:\n"
        "<code>./update.sh</code>\n\n"
        "قبل از بروزرسانی، Release Notes و تغییرات GitHub را بررسی کنید.",
        parse_mode="HTML",
        reply_markup=markup,
    )
    C.set_setting("last_update_notified_version", remote)
    C.audit("UPDATE_AVAILABLE", None, remote, f"installed={VERSION}", send=False)
    return True


def _loop():
    # Let Telegram polling and panel reconciliation settle first.
    time.sleep(45)
    while True:
        try:
            check_once()
        except Exception:
            pass
        try:
            interval = int(C.setting("update_check_interval_seconds", "21600") or 21600)
        except Exception:
            interval = 21600
        time.sleep(max(3600, min(interval, 604800)))


def start():
    global _UPDATE_THREAD
    with _UPDATE_LOCK:
        if _UPDATE_THREAD and _UPDATE_THREAD.is_alive():
            return
        _UPDATE_THREAD = threading.Thread(target=_loop, name="github-update-check", daemon=True)
        _UPDATE_THREAD.start()
