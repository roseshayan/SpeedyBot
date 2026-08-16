import json, os, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
from . import context as C
from .storage import audiences


def send_panel_snapshot(admin_id, actor_id=None):
    """Create a read-only 3x-ui export snapshot and send it to the admin."""
    try:
        r=C.CORE.requests.get(C.CORE._xui_url('panel/api/clients/export'),headers=C.CORE._xui_headers(),proxies=C.CORE._xui_proxies(),timeout=30,verify=not C.CORE.DEVELOPMENT_MODE)
        data=C.CORE._safe_json(r)
        if r.status_code!=200 or not data.get('success'): raise RuntimeError(C.CORE._xui_response_error(r,'Panel export failed'))
        payload={'speedybot_version':'4.0.0','created_at':datetime.now(timezone.utc).isoformat(),'source':'3x-ui clients/export (read-only)','clients':data.get('obj') or []}
        fd,path=tempfile.mkstemp(prefix='speedybot-panel-snapshot-',suffix='.json'); os.close(fd); Path(path).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            with open(path,'rb') as f: C.BOT.send_document(admin_id,f,caption=f"🛟 Snapshot پنل 3x-ui\nClients: {len(payload['clients'])}\n⚠️ این فایل شامل اطلاعات حساس سرویس‌هاست؛ عمومی منتشر نکنید.\nℹ️ Snapshot فقط Read-only است و چیزی را روی پنل تغییر نمی‌دهد.")
        finally:
            try: os.unlink(path)
            except OSError: pass
        C.audit('PANEL_SNAPSHOT',actor_id or admin_id,None,f"clients={len(payload['clients'])}")
    except Exception as e: C.BOT.send_message(admin_id,f"❌ Snapshot خطا داد:\n<code>{str(e)[:700]}</code>",parse_mode='HTML')


def broadcast(source_chat_id, source_message_id, admin_id, audience, ids=None):
    ids=list(ids if ids is not None else audiences(audience)); sent=failed=0
    for uid in ids:
        try: C.BOT.copy_message(int(uid),int(source_chat_id),int(source_message_id)); sent+=1
        except Exception: failed+=1
        time.sleep(.06)
    c=C.db(); c.execute('INSERT INTO broadcast_history(admin_id,audience,total,sent,failed,created_at) VALUES (?,?,?,?,?,?)',(int(admin_id),str(audience),len(ids),sent,failed,int(time.time()))); c.commit(); c.close()
    C.BOT.send_message(source_chat_id,f"✅ <b>ارسال هدفمند تمام شد</b>\n\n👥 کل: <b>{len(ids):,}</b>\n✅ موفق: <b>{sent:,}</b>\n❌ ناموفق: <b>{failed:,}</b>",parse_mode='HTML')
    C.audit('TARGETED_BROADCAST',admin_id,audience,f'sent={sent} failed={failed}')
