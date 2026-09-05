from html import escape

from . import context as C


def _owned_linked_service(user_id, linked_id):
    c = C.db()
    row = c.execute(
        "SELECT id,email FROM linked_services WHERE id=? AND user_id=?",
        (int(linked_id), int(user_id)),
    ).fetchone()
    c.close()
    return row


def _renew_menu(user_id, linked_id):
    service = _owned_linked_service(user_id, linked_id)
    if not service:
        C.BOT.send_message(user_id, "❌ سرویس متصل‌شده پیدا نشد.")
        return
    if not C.CORE.purchase_gate(user_id):
        return

    plans = C.CORE.get_active_plans()
    if not plans:
        C.BOT.send_message(user_id, "⛔️ در حال حاضر پلن فعالی برای تمدید وجود ندارد.")
        return

    balance = int(C.CORE.get_user_balance(user_id) or 0)
    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for plan in plans:
        pid = int(plan["id"])
        price = int(plan["price"] or 0)
        name = str(plan["name"] or f"پلن #{pid}")
        markup.add(
            C.inline(
                f"💳 تمدید با {name[:35]} — {price:,} تومان",
                callback_data=f"linked:renewcard:{int(linked_id)}:{pid}",
                style_name="primary",
            )
        )
        if balance >= price:
            markup.add(
                C.inline(
                    f"👛 کیف پول | {name[:35]}",
                    callback_data=f"linked:renewwallet:{int(linked_id)}:{pid}",
                    style_name="success",
                )
            )

    C.BOT.send_message(
        user_id,
        "♻️ <b>تمدید سرویس قبلی</b>\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🔗 سرویس: <code>{escape(service['email'])}</code>\n"
        f"👛 موجودی کیف پول: <b>{balance:,} تومان</b>\n\n"
        "پلن تمدید را انتخاب کنید. مدت، حجم و IP Limit مطابق پلن انتخابی روی همین سرویس اعمال می‌شود.",
        parse_mode="HTML",
        reply_markup=markup,
    )


def view_linked(call):
    uid = int(call.from_user.id)
    try:
        linked_id = int((call.data or "").split(":")[2])
    except Exception:
        C.BOT.answer_callback_query(call.id, "شناسه سرویس نامعتبر است.", show_alert=True)
        return

    service = _owned_linked_service(uid, linked_id)
    if not service:
        C.BOT.answer_callback_query(call.id, "سرویس پیدا نشد.", show_alert=True)
        return

    C.BOT.answer_callback_query(call.id, "در حال استعلام وضعیت...")
    C.CORE.send_xui_status(uid, service["email"])

    markup = C.CORE.types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        C.inline(
            "♻️ تمدید همین سرویس",
            callback_data=f"linked:renew:{linked_id}",
            style_name="success",
        )
    )
    C.BOT.send_message(
        uid,
        f"🔗 <b>سرویس متصل‌شده:</b> <code>{escape(service['email'])}</code>\n"
        "برای تمدید این سرویس از دکمه زیر استفاده کنید.",
        parse_mode="HTML",
        reply_markup=markup,
    )


def callback(call):
    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    uid = int(call.from_user.id)

    if action == "renew" and len(parts) > 2:
        C.BOT.answer_callback_query(call.id)
        _renew_menu(uid, int(parts[2]))
        return

    if action in {"renewcard", "renewwallet"} and len(parts) > 3:
        try:
            linked_id = int(parts[2])
            plan_id = int(parts[3])
        except Exception:
            C.BOT.answer_callback_query(call.id, "اطلاعات تمدید نامعتبر است.", show_alert=True)
            return

        service = _owned_linked_service(uid, linked_id)
        plan = C.CORE.get_plan(plan_id, include_inactive=False)
        if not service or not plan:
            C.BOT.answer_callback_query(call.id, "سرویس یا پلن نامعتبر است.", show_alert=True)
            return
        if not C.CORE.purchase_gate(uid):
            return

        if action == "renewcard":
            C.BOT.answer_callback_query(call.id)
            C.CORE._start_card_checkout(uid, uid, plan, "RENEWAL", service["email"])
        else:
            C.CORE._start_wallet_checkout(call, plan, "RENEWAL", service["email"])
        return


def register():
    C.BOT.callback_query_handler(func=lambda call: (call.data or "").startswith("view:linked:"))(view_linked)
    C.promote_callback()
    C.BOT.callback_query_handler(func=lambda call: (call.data or "").startswith("linked:"))(callback)
    C.promote_callback()
