import time
from html import escape

from . import context as C
from . import trial, ui


def _guard(call):
    if C.is_admin(call.from_user.id):
        return True
    C.BOT.answer_callback_query(call.id, "دسترسی ندارید.", show_alert=True)
    return False


def _back(message):
    if (message.text or "").strip() == "🔙 بازگشت به منوی اصلی":
        C.CORE.go_to_main_menu(message)
        return True
    return False


def _send(chat, text, markup=None):
    C.BOT.send_message(chat, text, parse_mode="HTML", reply_markup=markup)


def _scope_title(scope, plan_id):
    if scope == "trial":
        return "تست رایگان"
    plan = C.CORE.get_plan(int(plan_id), include_inactive=True)
    return f"پلان #{plan_id}" + (f" — {plan['name']}" if plan else "")


def _show_inbounds(chat, message_id=None):
    gb, days, ip = trial.default_values()
    plans = C.CORE.get_active_plans()
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        C.inline(
            f"🎁 تست رایگان: {'🟢 فعال' if C.CORE.trial_enabled() else '🔴 غیرفعال'}",
            callback_data="fix:trial_toggle",
            style_name="success" if C.CORE.trial_enabled() else "danger",
        )
    )
    markup.add(
        C.inline(
            f"⚙️ تنظیم عمومی تست — {gb:g}GB / {days}d / IP {ip}",
            callback_data="fix:trial_defaults",
            style_name="primary",
        )
    )
    markup.add(C.inline("🔀 Inboundهای تست رایگان", callback_data="fix:scope:trial:0", style_name="primary"))
    for plan in plans:
        markup.add(
            C.inline(
                f"📦 Inboundهای پلان #{plan['id']} — {str(plan['name'])[:28]}",
                callback_data=f"fix:scope:plan:{plan['id']}",
                style_name="primary",
            )
        )
    text = (
        "🧪 <b>تست رایگان و مسیریابی Inbound</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        "✅ تیک یعنی Client واقعاً باید به آن Inbound متصل باشد.\n"
        "⬜ یعنی Client نباید به آن Inbound Attach شود.\n\n"
        "بعد از ساخت/تمدید، SpeedyBot عضویت واقعی Client را از 3x-ui دوباره می‌خواند و اگر با انتخاب شما یکی نباشد عملیات را موفق اعلام نمی‌کند."
    )
    if message_id:
        try:
            C.BOT.edit_message_text(text, chat_id=chat, message_id=message_id, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    _send(chat, text, markup)


def _show_scope(chat, scope, plan_id, message_id=None):
    details = C.CORE._get_active_inbound_details(C.CORE._xui_headers(), C.CORE._xui_proxies())
    selected = set(
        C.CORE._selected_inbound_ids_for(
            scope,
            int(plan_id) if scope == "plan" else None,
            C.CORE._xui_headers(),
            C.CORE._xui_proxies(),
        )
    )
    raw = C.ORIGINALS.get("configured_inbounds", C.CORE._configured_inbound_ids)(
        scope, int(plan_id) if scope == "plan" else None
    )
    title = _scope_title(scope, plan_id)
    mode = "همه Inboundهای فعال (پیش‌فرض)" if not raw else f"انتخاب صریح: {len(selected)} Inbound"
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for inbound in details:
        iid = int(inbound["id"])
        mark = "✅" if iid in selected else "⬜"
        markup.add(
            C.inline(
                f"{mark} #{iid} | {str(inbound.get('remark') or '-')[:28]} | {inbound.get('protocol','-')}:{inbound.get('port','-')}",
                callback_data=f"fix:toggle:{scope}:{int(plan_id)}:{iid}",
                style_name="success" if iid in selected else None,
            )
        )
    markup.add(
        C.inline(
            "✅ انتخاب همه Inboundهای فعال",
            callback_data=f"fix:reset:{scope}:{int(plan_id)}",
            style_name="primary",
        )
    )
    markup.add(C.inline("↩️ بازگشت", callback_data="fix:inbounds"))
    text = (
        f"🔀 <b>Inboundهای {escape(title)}</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"حالت: <b>{escape(mode)}</b>\n\n"
        "روی هر ردیف بزنید تا همان Inbound واقعاً به مجموعه Attach/Detach سرویس‌های جدید اضافه یا حذف شود.\n"
        "حداقل یک Inbound باید انتخاب بماند."
    )
    if message_id:
        try:
            C.BOT.edit_message_text(text, chat_id=chat, message_id=message_id, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    _send(chat, text, markup)


def _show_delete_menu(chat):
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    markup.add(C.inline("🗑 حذف پلان", callback_data="fix:plan_delete", style_name="danger"))
    markup.add(C.inline("🗑 حذف دسته‌بندی", callback_data="fix:category_delete", style_name="danger"))
    _send(
        chat,
        "🗑 <b>حذف امن کاتالوگ</b>\n━━━━━━━━━━━━━━━━\n"
        "• پلان دارای سابقه تراکنش Hard Delete نمی‌شود؛ برای حفظ تاریخچه باید غیرفعال بماند.\n"
        "• هنگام حذف دسته، پلان‌های آن به یک دسته دیگر منتقل می‌شوند و حذف نمی‌شوند.",
        markup,
    )


def callback(call):
    if not _guard(call):
        return
    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    chat = call.message.chat.id
    actor = int(call.from_user.id)

    if action == "inbounds":
        C.BOT.answer_callback_query(call.id)
        _show_inbounds(chat, call.message.message_id)
        return

    if action == "trial_toggle":
        new = "0" if C.CORE.trial_enabled() else "1"
        C.set_setting("trial_enabled", new)
        C.audit("TRIAL_TOGGLE", actor, new)
        C.BOT.answer_callback_query(call.id, "ذخیره شد ✅")
        _show_inbounds(chat, call.message.message_id)
        return

    if action == "scope":
        scope = parts[2]
        pid = int(parts[3])
        C.BOT.answer_callback_query(call.id)
        _show_scope(chat, scope, pid, call.message.message_id)
        return

    if action == "toggle":
        scope = parts[2]
        pid = int(parts[3])
        iid = int(parts[4])
        before = set(
            C.CORE._selected_inbound_ids_for(
                scope,
                pid if scope == "plan" else None,
                C.CORE._xui_headers(),
                C.CORE._xui_proxies(),
            )
        )
        selected = C.CORE._set_inbound_toggle(scope, iid, pid if scope == "plan" else None)
        after = set(
            C.CORE._selected_inbound_ids_for(
                scope,
                pid if scope == "plan" else None,
                C.CORE._xui_headers(),
                C.CORE._xui_proxies(),
            )
        )
        if before == after:
            C.BOT.answer_callback_query(call.id, "حداقل یک Inbound باید انتخاب بماند.", show_alert=True)
        else:
            C.BOT.answer_callback_query(call.id, "انتخاب شد ✅" if selected else "حذف شد ✅")
            C.audit("INBOUND_SELECTION_CHANGED", actor, f"{scope}:{pid}", f"inbound={iid}; selected={selected}")
        _show_scope(chat, scope, pid, call.message.message_id)
        return

    if action == "reset":
        scope = parts[2]
        pid = int(parts[3])
        C.CORE._clear_inbound_selection(scope, pid if scope == "plan" else None)
        C.audit("INBOUND_SELECTION_RESET", actor, f"{scope}:{pid}")
        C.BOT.answer_callback_query(call.id, "همه Inboundهای فعال انتخاب شدند ✅")
        _show_scope(chat, scope, pid, call.message.message_id)
        return

    if action == "trial_defaults":
        gb, days, ip = trial.default_values()
        C.BOT.answer_callback_query(call.id)
        msg = C.BOT.send_message(
            chat,
            "⚙️ <b>تنظیم عمومی تست رایگان</b>\n"
            f"فعلی: <b>{gb:g} GB / {days} روز / IP {ip}</b>\n\n"
            "فرمت جدید را بفرستید:\n<code>حجمGB | روز | IP Limit</code>\n"
            "مثال: <code>2 | 2 | 1</code>",
            parse_mode="HTML",
            reply_markup=C.CORE.back_menu(),
        )
        C.BOT.register_next_step_handler(msg, _trial_defaults_save, actor)
        return

    if action == "delete":
        C.BOT.answer_callback_query(call.id)
        _show_delete_menu(chat)
        return

    if action == "plan_delete":
        C.BOT.answer_callback_query(call.id)
        msg = C.BOT.send_message(
            chat,
            "🗑 ID پلان را بفرستید.\nاگر پلان سابقه تراکنش داشته باشد برای حفظ تاریخچه حذف نخواهد شد.",
            reply_markup=C.CORE.back_menu(),
        )
        C.BOT.register_next_step_handler(msg, _plan_delete, actor)
        return

    if action == "category_delete":
        C.BOT.answer_callback_query(call.id)
        msg = C.BOT.send_message(
            chat,
            "🗑 ID دسته‌بندی را بفرستید. پلان‌های داخل آن قبل از حذف به یک دسته دیگر منتقل می‌شوند.",
            reply_markup=C.CORE.back_menu(),
        )
        C.BOT.register_next_step_handler(msg, _category_delete, actor)
        return


def _trial_defaults_save(message, actor):
    if _back(message):
        return
    try:
        parts = [x.strip() for x in (message.text or "").split("|")]
        gb = float(parts[0])
        days = int(parts[1])
        ip = int(parts[2])
        if not (0.1 <= gb <= 1024 and 1 <= days <= 365 and 0 <= ip <= 50):
            raise ValueError
        C.set_setting("trial_default_volume_gb", f"{gb:g}")
        C.set_setting("trial_default_days", str(days))
        C.set_setting("trial_default_ip_limit", str(ip))
        C.audit("TRIAL_DEFAULTS_CHANGED", actor, detail=f"{gb:g}GB/{days}d/ip={ip}")
        C.BOT.send_message(
            message.chat.id,
            f"✅ تنظیم عمومی تست ذخیره شد: <b>{gb:g} GB / {days} روز / IP {ip}</b>",
            parse_mode="HTML",
            reply_markup=ui.admin_menu(),
        )
    except Exception:
        C.BOT.send_message(
            message.chat.id,
            "❌ فرمت نامعتبر است. نمونه: <code>2 | 2 | 1</code>",
            parse_mode="HTML",
            reply_markup=ui.admin_menu(),
        )


def _plan_delete(message, actor):
    if _back(message):
        return
    try:
        pid = int((message.text or "").strip())
        c = C.db()
        plan = c.execute("SELECT id,name FROM plans WHERE id=?", (pid,)).fetchone()
        if not plan:
            c.close()
            raise LookupError("پلان پیدا نشد.")
        used = int(c.execute("SELECT COUNT(*) FROM transactions WHERE plan_id=?", (pid,)).fetchone()[0])
        if used:
            c.close()
            C.BOT.send_message(
                message.chat.id,
                f"⛔️ پلان <b>{escape(plan['name'])}</b> دارای <b>{used}</b> تراکنش تاریخی است و برای جلوگیری از خراب شدن سوابق مالی Hard Delete نمی‌شود.\nاز گزینه فعال/غیرفعال استفاده کنید.",
                parse_mode="HTML",
                reply_markup=ui.admin_menu(),
            )
            return
        c.execute("DELETE FROM plan_inbounds WHERE plan_id=?", (pid,))
        c.execute("DELETE FROM plans WHERE id=?", (pid,))
        c.commit()
        c.close()
        C.audit("PLAN_DELETED", actor, pid, plan["name"])
        C.BOT.send_message(message.chat.id, "✅ پلان بدون سابقه تراکنش حذف شد.", reply_markup=ui.admin_menu())
    except LookupError as exc:
        C.BOT.send_message(message.chat.id, f"❌ {escape(str(exc))}", parse_mode="HTML", reply_markup=ui.admin_menu())
    except Exception:
        C.BOT.send_message(message.chat.id, "❌ ID پلان نامعتبر است.", reply_markup=ui.admin_menu())


def _category_delete(message, actor):
    if _back(message):
        return
    try:
        cid = int((message.text or "").strip())
        c = C.db()
        category = c.execute("SELECT id,name FROM plan_categories WHERE id=?", (cid,)).fetchone()
        if not category:
            c.close()
            raise LookupError("دسته پیدا نشد.")
        fallback = c.execute(
            "SELECT id,name FROM plan_categories WHERE id<>? ORDER BY CASE WHEN name='عمومی' THEN 0 ELSE 1 END,active DESC,sort_order,id LIMIT 1",
            (cid,),
        ).fetchone()
        if not fallback:
            c.close()
            C.BOT.send_message(
                message.chat.id,
                "⛔️ تنها دسته موجود قابل حذف نیست. ابتدا یک دسته دیگر بسازید.",
                reply_markup=ui.admin_menu(),
            )
            return
        moved = int(c.execute("SELECT COUNT(*) FROM plans WHERE category_id=?", (cid,)).fetchone()[0])
        c.execute("UPDATE plans SET category_id=?,updated_at=? WHERE category_id=?", (int(fallback["id"]), int(time.time()), cid))
        c.execute("DELETE FROM plan_categories WHERE id=?", (cid,))
        c.commit()
        c.close()
        C.audit("CATEGORY_DELETED", actor, cid, f"moved={moved}; fallback={fallback['id']}")
        C.BOT.send_message(
            message.chat.id,
            f"✅ دسته حذف شد. <b>{moved}</b> پلان به <b>{escape(fallback['name'])}</b> منتقل شد.",
            parse_mode="HTML",
            reply_markup=ui.admin_menu(),
        )
    except LookupError as exc:
        C.BOT.send_message(message.chat.id, f"❌ {escape(str(exc))}", parse_mode="HTML", reply_markup=ui.admin_menu())
    except Exception:
        C.BOT.send_message(message.chat.id, "❌ ID دسته نامعتبر است.", reply_markup=ui.admin_menu())


def register():
    C.BOT.callback_query_handler(func=lambda call: (call.data or "").startswith("fix:"))(callback)
    C.promote_callback()
