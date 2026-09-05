from __future__ import annotations
import sqlite3, time
from html import escape
from typing import Any, Dict, Optional, Tuple

CORE = None
BOT = None
ORIGINALS: Dict[str, Any] = {}
STYLE_VALUES = ("default", "primary", "success", "danger")
EMOJI_KEYS = {
    "buy": "خرید", "account": "حساب کاربری", "trial": "تست رایگان",
    "guide": "راهنمای اتصال", "support": "پشتیبانی", "admin": "پنل مدیریت",
}
CUSTOMER_MENU_KEYS = {
    "buy": "🛍 مشاهده و خرید پلان‌ها",
    "account": "👤 حساب کاربری",
    "trial": "🎁 دریافت تست رایگان",
    "affiliate": "🤝 همکاری در فروش",
    "guide": "📲 راهنمای اتصال",
    "faq": "📚 راهنما و سوالات",
    "rewards": "🎟 کد هدیه / تخفیف",
    "feedback": "⭐ نظر و امتیاز",
    "support": "📞 پشتیبانی",
}

def configure(core):
    global CORE, BOT
    CORE, BOT = core, core.bot

def db():
    c = sqlite3.connect("speedping.db", timeout=15)
    c.row_factory = sqlite3.Row
    return c

def setting(key: str, default: str = "") -> str:
    return str(CORE.get_db_setting(key, default))

def set_setting(key: str, value: Any):
    CORE.update_db_setting(key, str(value))

def brand_name() -> str:
    value = setting("brand_name", "فروشگاه").strip()
    return (value or "فروشگاه")[:64]

def menu_visible(key: str, default: str = "1") -> bool:
    return setting(f"menu_{key}_visible", default).strip() == "1"

def is_admin(uid: int) -> bool:
    try: return bool(CORE.is_admin(int(uid)))
    except Exception: return False

def blocked(uid: int) -> Tuple[bool, str]:
    c=db(); r=c.execute("SELECT reason FROM user_blocks WHERE user_id=? AND active=1",(int(uid),)).fetchone(); c.close()
    return bool(r), (str(r[0] or "") if r else "")

def mode() -> str:
    v=setting("operating_mode","NORMAL").upper().strip()
    return v if v in {"NORMAL","SALES_PAUSED","MAINTENANCE"} else "NORMAL"

def style(key: str, fallback="default") -> Optional[str]:
    v=setting("ui_style_"+key,fallback).lower().strip()
    return None if v=="default" else (v if v in STYLE_VALUES else None)

def emoji(key: str) -> Optional[str]:
    if setting("ui_premium_emoji_enabled","0")!="1": return None
    return setting("ui_emoji_"+key,"").strip() or None

def inline(text: str, callback_data=None, url=None, style_name=None, emoji_key=None):
    kw={"text":text}
    if callback_data is not None: kw["callback_data"]=callback_data
    if url is not None: kw["url"]=url
    st=style_name or (style(emoji_key) if emoji_key else None)
    em=emoji(emoji_key) if emoji_key else None
    if st: kw["style"]=st
    if em: kw["icon_custom_emoji_id"]=em
    try: return CORE.types.InlineKeyboardButton(**kw)
    except TypeError:
        kw.pop("style",None); kw.pop("icon_custom_emoji_id",None)
        return CORE.types.InlineKeyboardButton(**kw)

def reply(text: str, key: str, style_name=None):
    kw={"text":text}; st=style_name or style(key); em=emoji(key)
    if st: kw["style"]=st
    if em: kw["icon_custom_emoji_id"]=em
    try: return CORE.types.KeyboardButton(**kw)
    except TypeError: return text

def audit(event: str, actor=None, target=None, detail="", send=True):
    txt=str(detail or "")[:3000]
    target_text=str(target)[:200] if target is not None else None
    try:
        c=db(); c.execute("INSERT INTO audit_events(event_type,actor_id,target_id,detail,created_at) VALUES (?,?,?,?,?)",
            (str(event)[:80],int(actor) if actor else None,target_text,txt,int(time.time()))); c.commit(); c.close()
    except Exception: pass
    if not send or setting("audit_enabled","1")!="1": return
    cid=setting("audit_chat_id","").strip()
    if not cid: return
    try:
        BOT.send_message(
            int(cid),
            f"🧾 <b>{escape(str(event)[:80])}</b>\nActor: <code>{escape(str(actor or '-'))}</code>\nTarget: <code>{escape(target_text or '-')}</code>\n{escape(txt)}",
            parse_mode="HTML"
        )
    except Exception: pass

def promote_message():
    try: BOT.message_handlers.insert(0,BOT.message_handlers.pop())
    except Exception: pass

def promote_callback():
    try: BOT.callback_query_handlers.insert(0,BOT.callback_query_handlers.pop())
    except Exception: pass