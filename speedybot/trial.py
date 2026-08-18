import html
import time

from . import context as C


def override(uid):
    if C.setting("trial_overrides_enabled", "1") != "1":
        return None
    c = C.db()
    row = c.execute("SELECT * FROM trial_overrides WHERE user_id=?", (int(uid),)).fetchone()
    c.close()
    return row


def default_values():
    try:
        gb = max(0.1, min(1024.0, float(C.setting("trial_default_volume_gb", "1"))))
    except Exception:
        gb = 1.0
    try:
        days = max(1, min(365, int(float(C.setting("trial_default_days", "1")))))
    except Exception:
        days = 1
    try:
        ip = max(0, min(50, int(float(C.setting("trial_default_ip_limit", "1")))))
    except Exception:
        ip = 1
    return gb, days, ip


def values(uid):
    ov = override(uid)
    if ov:
        return (
            max(0.1, min(1024.0, float(ov["volume_gb"]))),
            max(1, min(365, int(ov["days"]))),
            max(0, min(50, int(ov["ip_limit"]))),
            True,
        )
    gb, days, ip = default_values()
    return gb, days, ip, False


def generate(uid, email):
    gb, days, ip, is_override = values(uid)
    headers = C.CORE._xui_headers()
    proxies = C.CORE._xui_proxies()
    try:
        desired = C.CORE._selected_inbound_ids_for("trial", None, headers, proxies)
        client = C.CORE._get_client_data(email, headers, proxies)
        if not client:
            payload = {
                "client": {
                    "email": email,
                    "totalGB": int(gb * 1024**3),
                    "expiryTime": int((time.time() + days * 86400) * 1000),
                    "tgId": int(uid),
                    "limitIp": ip,
                    "enable": True,
                },
                "inboundIds": desired,
            }
            response = C.CORE.requests.post(
                C.CORE._xui_url("panel/api/clients/add"),
                json=payload,
                headers=headers,
                proxies=proxies,
                timeout=15,
                verify=not C.CORE.DEVELOPMENT_MODE,
            )
            data = C.CORE._safe_json(response)
            if response.status_code != 200 or not data.get("success"):
                raise RuntimeError(C.CORE._xui_response_error(response, "پنل ساخت تست رایگان را رد کرد"))
            time.sleep(1)
            client = C.CORE._get_client_data(email, headers, proxies)

        if client:
            # This now performs real attach/detach and verifies the persisted
            # inboundIds on the panel before the Trial is considered active.
            C.CORE._sync_client_inbounds(email, desired)
            client = C.CORE._get_client_data(email, headers, proxies) or client

        sub = C.CORE._get_client_subscription_id(email, headers, proxies, client)
        links = C.CORE._get_delivery_links(email, sub, headers, proxies)
        if not sub and not links:
            raise RuntimeError("هیچ لینک تحویلی از پنل برنگشت.")

        try:
            C.CORE._xui_assign_group(email, C.setting("xui_trial_group", "Trial") or "Trial")
        except Exception as group_error:
            C.CORE.notify_admins(
                f"⚠️ تست {email} ساخته شد اما عضویت Group Trial خطا داد: {str(group_error)[:350]}"
            )
        C.CORE._mark_trial(uid, "ACTIVE")
    except Exception as exc:
        C.CORE._mark_trial(uid, "FAILED", exc)
        try:
            C.BOT.send_message(
                uid,
                "❌ صدور تست رایگان خطا داد؛ درخواست مصرف‌شده حساب نشد و می‌توانید دوباره تلاش کنید.",
                reply_markup=C.CORE.main_menu(),
            )
        except Exception:
            pass
        C.CORE.notify_admins(f"🚨 خطا در صدور تست {uid}: {str(exc)[:700]}")
        return

    title = "تست اختصاصی" if is_override else "تست رایگان"
    text = (
        f"🎁 <b>{title} فعال شد</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📦 حجم: <b>{gb:g} GB</b>\n"
        f"⏱ اعتبار: <b>{days} روز</b>\n"
        f"👥 IP Limit: <b>{ip if ip else 'بدون محدودیت'}</b>\n"
    )
    if sub:
        text += f"\n🌐 <b>Subscription</b>\n<code>{html.escape(C.CORE._subscription_url(sub))}</code>\n"
    if links:
        text += "\n🔑 <b>Direct configs</b>\n" + "\n".join(
            f"<code>{html.escape(link)}</code>" for link in links
        )
    C.BOT.send_message(uid, text, parse_mode="HTML", reply_markup=C.CORE.main_menu())
    C.CORE._send_guide_cta(uid)
    C.audit(
        "TRIAL_ISSUED",
        uid,
        email,
        f"{gb:g}GB/{days}d/ip={ip}/override={1 if is_override else 0}",
    )


def request(message):
    """Handle the Trial button with dynamic global/per-user settings."""
    try:
        C.CORE.USER_STATES[message.chat.id] = None
    except Exception:
        pass
    uid = int(message.from_user.id)
    if not C.CORE.trial_enabled():
        C.BOT.send_message(
            message.chat.id,
            "⛔️ دریافت تست رایگان در حال حاضر توسط مدیریت غیرفعال شده است.",
            reply_markup=C.CORE.main_menu(),
        )
        return
    if not C.CORE.purchase_gate(uid):
        return

    email = f"speedping_trial_{uid}"
    c = C.db()
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT status FROM trial_services WHERE user_id=?", (uid,)).fetchone()
        if row and row["status"] != "FAILED":
            c.rollback()
            if row["status"] == "CREATING":
                text = "⏳ درخواست تست شما قبلاً ثبت شده و در حال صدور است."
            else:
                text = "🎁 شما قبلاً تست رایگان را دریافت کرده‌اید. هر کاربر فقط یک‌بار امکان دریافت تست دارد."
            C.BOT.send_message(message.chat.id, text, reply_markup=C.CORE.main_menu())
            return

        now = int(time.time())
        if row:
            c.execute(
                "UPDATE trial_services SET status='CREATING',last_error=NULL,created_at=? WHERE user_id=?",
                (now, uid),
            )
        else:
            c.execute(
                "INSERT INTO trial_services(user_id,email,status,created_at) VALUES (?,?,'CREATING',?)",
                (uid, email, now),
            )
        c.commit()
    except Exception:
        c.rollback()
        C.BOT.send_message(
            message.chat.id,
            "🎁 تست رایگان برای این حساب قبلاً ثبت شده است.",
            reply_markup=C.CORE.main_menu(),
        )
        return
    finally:
        c.close()

    gb, days, ip, is_override = values(uid)
    label = "تنظیم اختصاصی شما" if is_override else "تنظیم عمومی تست"
    C.BOT.send_message(
        message.chat.id,
        "⚡️ در حال ساخت تست رایگان شما هستم...\n\n"
        f"📦 حجم: <b>{gb:g} GB</b>\n"
        f"⏱ اعتبار: <b>{days} روز</b>\n"
        f"👥 IP Limit: <b>{ip if ip else 'بدون محدودیت'}</b>\n"
        f"⚙️ {label}",
        parse_mode="HTML",
        reply_markup=C.CORE.main_menu(),
    )
    C.CORE.generate_trial_xui_config(uid, email)


def register():
    C.BOT.message_handler(func=lambda m: m.text == "🎁 دریافت تست رایگان")(request)
    C.promote_message()
