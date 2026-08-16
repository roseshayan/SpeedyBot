import html, time
from . import context as C

def override(uid):
    if C.setting("trial_overrides_enabled","1")!="1": return None
    c=C.db(); r=c.execute("SELECT * FROM trial_overrides WHERE user_id=?",(int(uid),)).fetchone(); c.close(); return r

def generate(uid,email):
    ov=override(uid)
    if not ov: return C.ORIGINALS["trial_generator"](uid,email)
    gb=max(.1,float(ov['volume_gb'])); days=max(1,int(ov['days'])); ip=max(0,int(ov['ip_limit'])); headers=C.CORE._xui_headers(); proxies=C.CORE._xui_proxies()
    try:
        desired=C.CORE._selected_inbound_ids_for('trial',None,headers,proxies); client=C.CORE._get_client_data(email,headers,proxies)
        if not client:
            payload={"client":{"email":email,"totalGB":int(gb*1024**3),"expiryTime":int((time.time()+days*86400)*1000),"tgId":int(uid),"limitIp":ip,"enable":True},"inboundIds":desired}
            r=C.CORE.requests.post(C.CORE._xui_url("panel/api/clients/add"),json=payload,headers=headers,proxies=proxies,timeout=15,verify=not C.CORE.DEVELOPMENT_MODE); data=C.CORE._safe_json(r)
            if r.status_code!=200 or not data.get('success'): raise RuntimeError(C.CORE._xui_response_error(r,"پنل ساخت تست اختصاصی را رد کرد"))
            time.sleep(1); client=C.CORE._get_client_data(email,headers,proxies)
        if client: C.CORE._sync_client_inbounds(email,desired); client=C.CORE._get_client_data(email,headers,proxies) or client
        sub=C.CORE._get_client_subscription_id(email,headers,proxies,client); links=C.CORE._get_delivery_links(email,sub,headers,proxies)
        if not sub and not links: raise RuntimeError("هیچ لینک تحویلی برنگشت.")
        try: C.CORE._xui_assign_group(email,C.setting('xui_trial_group','Trial') or 'Trial')
        except Exception: pass
        C.CORE._mark_trial(uid,'ACTIVE')
    except Exception as e:
        C.CORE._mark_trial(uid,'FAILED',e); C.BOT.send_message(uid,"❌ صدور تست اختصاصی خطا داد؛ درخواست مصرف‌شده حساب نشد.",reply_markup=C.CORE.main_menu()); C.CORE.notify_admins(f"🚨 تست اختصاصی {uid}: {str(e)[:700]}"); return
    text=f"🎁 <b>تست اختصاصی فعال شد</b>\n━━━━━━━━━━━━━━━━\n📦 <b>{gb:g} GB</b>\n⏱ <b>{days} روز</b>\n👥 IP Limit: <b>{ip if ip else 'بدون محدودیت'}</b>\n"
    if sub: text+=f"\n🌐 <b>Subscription</b>\n<code>{html.escape(C.CORE._subscription_url(sub))}</code>\n"
    if links: text+="\n🔑 <b>Direct configs</b>\n"+"\n".join(f"<code>{html.escape(x)}</code>" for x in links)
    C.BOT.send_message(uid,text,parse_mode="HTML",reply_markup=C.CORE.main_menu()); C.CORE._send_guide_cta(uid); C.audit("CUSTOM_TRIAL_ISSUED",uid,email,f"{gb:g}GB/{days}d/ip={ip}")
