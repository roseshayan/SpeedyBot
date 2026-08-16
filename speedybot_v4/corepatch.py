from html import escape
from . import context as C
from . import trial, ui

def apply():
    core=C.CORE
    C.ORIGINALS.update({"purchase_gate":core.purchase_gate,"checkout":core._create_checkout_transaction,"trial_enabled":core.trial_enabled,"trial_generator":core.generate_trial_xui_config,"notify_admins":core.notify_admins})
    def purchase_gate(uid):
        b,reason=C.blocked(uid)
        if b: C.BOT.send_message(int(uid),"🚫 دسترسی خرید این حساب محدود شده است."+(f"\nدلیل: {reason}" if reason else "")+"\nبرای بررسی با پشتیبانی تماس بگیرید.",reply_markup=ui.main_menu()); return False
        if C.mode()=="MAINTENANCE": C.BOT.send_message(int(uid),C.setting("maintenance_message"),reply_markup=ui.main_menu()); return False
        return C.ORIGINALS["purchase_gate"](uid)
    def checkout(uid,plan,payment_method,kind='NEW',target_service_email=None,extra_volume_gb=0):
        b,reason=C.blocked(uid)
        if b: return None,"دسترسی خرید این حساب محدود شده است."+(f" دلیل: {reason}" if reason else "")
        if C.mode()=="MAINTENANCE": return None,C.setting("maintenance_message")
        if C.mode()=="SALES_PAUSED": return None,"فروش و تمدید موقتاً توسط مدیریت متوقف شده است."
        return C.ORIGINALS["checkout"](uid,plan,payment_method,kind,target_service_email,extra_volume_gb)
    def trial_enabled(): return False if C.mode()=="MAINTENANCE" else bool(C.ORIGINALS["trial_enabled"]())
    def notify(text,parse_mode=None,reply_markup=None):
        out=C.ORIGINALS["notify_admins"](text,parse_mode=parse_mode,reply_markup=reply_markup)
        cid=C.setting("audit_chat_id","").strip()
        if C.setting("audit_enabled","1")=="1" and cid:
            try: C.BOT.send_message(int(cid),"🧾 <b>SpeedyBot event</b>\n<pre>"+escape(str(text)[:3200])+"</pre>",parse_mode="HTML")
            except Exception: pass
        return out
    core.purchase_gate=purchase_gate; core._create_checkout_transaction=checkout; core.trial_enabled=trial_enabled; core.generate_trial_xui_config=trial.generate; core.notify_admins=notify; core.main_menu=ui.main_menu; core.admin_main_menu=ui.admin_menu
