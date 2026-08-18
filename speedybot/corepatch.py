import base64
import time
from html import escape

from . import context as C
from . import trial, ui


PROXY_SCHEMES = ("vless://", "vmess://", "trojan://", "ss://", "hysteria://", "hysteria2://", "hy2://")


def _decode_subscription_text(body):
    """Return direct proxy links from a raw 3x-ui subscription response.

    3x-ui serves the raw /sub/ body either as newline-separated links or as
    standard Base64 when subEncrypt is enabled. Keep this helper pure so it can
    be unit-tested without a live panel.
    """
    text = str(body or "").strip().lstrip("\ufeff")
    if not text:
        return []

    def direct_lines(value):
        out = []
        seen = set()
        for line in str(value or "").replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or not line.lower().startswith(PROXY_SCHEMES) or line in seen:
                continue
            seen.add(line)
            out.append(line)
        return out

    links = direct_lines(text)
    if links:
        return links

    compact = "".join(text.split())
    if not compact:
        return []
    padded = compact + ("=" * ((4 - len(compact) % 4) % 4))
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            decoded = decoder(padded.encode("ascii")).decode("utf-8", errors="strict")
        except Exception:
            continue
        links = direct_lines(decoded)
        if links:
            return links
    return []


def _toggle_effective(active_ids, persisted_ids, clicked_id):
    """Toggle an inbound while preserving the legacy empty=ALL representation.

    Returns (ids_to_persist, clicked_is_selected, changed).
    """
    active = {int(x) for x in active_ids}
    clicked = int(clicked_id)
    raw = {int(x) for x in persisted_ids}
    effective = (set(active) if not raw else (raw & active))

    if clicked not in active:
        return sorted(raw), False, False

    if clicked in effective:
        # 3x-ui requires at least one inbound on client creation. Do not let the
        # UI accidentally represent "none" as the legacy "all" sentinel.
        if len(effective) <= 1:
            return sorted(raw), True, False
        effective.remove(clicked)
    else:
        effective.add(clicked)

    # Empty rows are the backwards-compatible representation for ALL active.
    stored = [] if effective == active else sorted(effective)
    return stored, clicked in effective, True


def apply():
    core = C.CORE
    C.ORIGINALS.update({
        "purchase_gate": core.purchase_gate,
        "checkout": core._create_checkout_transaction,
        "trial_enabled": core.trial_enabled,
        "trial_generator": core.generate_trial_xui_config,
        "notify_admins": core.notify_admins,
        "delivery_links": core._get_delivery_links,
        "configured_inbounds": core._configured_inbound_ids,
        "set_inbound_toggle": core._set_inbound_toggle,
        "sync_client_inbounds": core._sync_client_inbounds,
    })

    def purchase_gate(uid):
        blocked, reason = C.blocked(uid)
        if blocked:
            C.BOT.send_message(
                int(uid),
                "🚫 دسترسی خرید این حساب محدود شده است."
                + (f"\nدلیل: {reason}" if reason else "")
                + "\nبرای بررسی با پشتیبانی تماس بگیرید.",
                reply_markup=ui.main_menu(),
            )
            return False
        if C.mode() == "MAINTENANCE":
            C.BOT.send_message(
                int(uid),
                C.setting("maintenance_message", "🛠 سرویس موقتاً در حال نگهداری است."),
                reply_markup=ui.main_menu(),
            )
            return False
        return C.ORIGINALS["purchase_gate"](uid)

    def checkout(uid, plan, payment_method, kind="NEW", target_service_email=None, extra_volume_gb=0):
        blocked, reason = C.blocked(uid)
        if blocked:
            return None, "دسترسی خرید این حساب محدود شده است." + (f" دلیل: {reason}" if reason else "")
        if C.mode() == "MAINTENANCE":
            return None, C.setting("maintenance_message", "🛠 سرویس موقتاً در حال نگهداری است.")
        if C.mode() == "SALES_PAUSED":
            return None, C.setting("sales_paused_message", "🛒 فروش و تمدید موقتاً متوقف شده است.")
        return C.ORIGINALS["checkout"](uid, plan, payment_method, kind, target_service_email, extra_volume_gb)

    def trial_enabled():
        return False if C.mode() == "MAINTENANCE" else bool(C.ORIGINALS["trial_enabled"]())

    def notify(text, parse_mode=None, reply_markup=None):
        out = C.ORIGINALS["notify_admins"](text, parse_mode=parse_mode, reply_markup=reply_markup)
        cid = C.setting("audit_chat_id", "").strip()
        if C.setting("audit_enabled", "1") == "1" and cid:
            try:
                C.BOT.send_message(
                    int(cid),
                    "🧾 <b>SpeedyBot event</b>\n<pre>" + escape(str(text)[:3200]) + "</pre>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
        return out

    def configured_inbounds(scope, plan_id=None):
        """Expose the effective set to UIs: legacy empty rows mean ALL active."""
        raw = C.ORIGINALS["configured_inbounds"](scope, plan_id)
        if raw:
            return raw
        return [
            int(x)
            for x in core._get_active_inbound_ids(core._xui_headers(), core._xui_proxies())
        ]

    def set_inbound_toggle(scope, inbound_id, plan_id=None):
        """Make a click mean what the checkbox says, including default ALL mode."""
        active = [
            int(x)
            for x in core._get_active_inbound_ids(core._xui_headers(), core._xui_proxies())
        ]
        raw = C.ORIGINALS["configured_inbounds"](scope, plan_id)
        stored, selected, changed = _toggle_effective(active, raw, inbound_id)
        if not changed:
            return selected

        conn = C.db()
        try:
            if scope == "trial":
                conn.execute("DELETE FROM trial_inbounds")
                conn.executemany(
                    "INSERT INTO trial_inbounds(inbound_id) VALUES (?)",
                    [(int(i),) for i in stored],
                )
            else:
                pid = int(plan_id)
                conn.execute("DELETE FROM plan_inbounds WHERE plan_id=?", (pid,))
                conn.executemany(
                    "INSERT INTO plan_inbounds(plan_id,inbound_id) VALUES (?,?)",
                    [(pid, int(i)) for i in stored],
                )
            conn.commit()
        finally:
            conn.close()
        return selected

    def sync_client_inbounds(email, desired_ids):
        """Attach/detach on 3x-ui and verify the panel persisted the exact set."""
        result = C.ORIGINALS["sync_client_inbounds"](email, desired_ids)
        expected = {int(x) for x in (desired_ids or [])}
        actual = set()
        for attempt in range(3):
            data = core._get_client_data(email, core._xui_headers(), core._xui_proxies()) or {}
            actual = {int(x) for x in (data.get("inboundIds") or [])}
            if actual == expected:
                return result
            if attempt < 2:
                time.sleep(0.5)
        raise RuntimeError(
            "عضویت Inbound در پنل با تنظیم ربات همگام نشد. "
            f"expected={sorted(expected)} actual={sorted(actual)}"
        )

    def delivery_links(user_email, sub_id, headers, request_proxies):
        """Prefer the real public subscription body for direct configs.

        This makes the manually delivered links match what a customer's
        subscription client actually receives, including public/managed hosts.
        The panel API links remain a fallback when the subscription endpoint is
        temporarily unreachable from the bot server.
        """
        if sub_id:
            try:
                response = core.requests.get(
                    core._subscription_url(sub_id),
                    headers={"Accept": "text/plain", "User-Agent": "SpeedyBot/4.0.1"},
                    proxies=request_proxies,
                    timeout=15,
                    verify=not core.DEVELOPMENT_MODE,
                )
                if response.status_code == 200:
                    links = core._clean_proxy_links(_decode_subscription_text(response.text))
                    if links:
                        return links
            except Exception:
                pass
        return C.ORIGINALS["delivery_links"](user_email, sub_id, headers, request_proxies)

    core.purchase_gate = purchase_gate
    core._create_checkout_transaction = checkout
    core.trial_enabled = trial_enabled
    core.generate_trial_xui_config = trial.generate
    core.notify_admins = notify
    core._configured_inbound_ids = configured_inbounds
    core._set_inbound_toggle = set_inbound_toggle
    core._sync_client_inbounds = sync_client_inbounds
    core._get_delivery_links = delivery_links
    core.main_menu = ui.main_menu
    core.admin_main_menu = ui.admin_menu
