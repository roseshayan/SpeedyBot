from __future__ import annotations
import time, threading
from html import escape
from . import context as C
from . import storage, ui, ops


def _cancel(message): return (message.text or '').strip() == '🔙 بازگشت به منوی اصلی'
def _back(message):
    if _cancel(message): C.CORE.go_to_main_menu(message); return True
    return False
def _admin_send(chat_id,text,markup=None): C.BOT.send_message(chat_id,text,parse_mode='HTML',reply_markup=markup)
def _mode_text(): return {'NORMAL':'🟢 عادی — همه سرویس‌ها فعال','SALES_PAUSED':'🟠 فروش متوقف — حساب/راهنما/پشتیبانی فعال','MAINTENANCE':'🔴 تعمیرات — خرید و تست متوقف'}[C.mode()]
def _rating_markup(prefix='plus:rate'):
    m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for n in range(5,0,-1): m.add(C.inline('⭐'*n,callback_data=f'{prefix}:{n}',style_name='success' if n>=4 else ('danger' if n<=2 else 'primary')))
    return m
def _admin_guard(call):
    if not C.is_admin(call.from_user.id): C.BOT.answer_callback_query(call.id,'دسترسی ندارید.',show_alert=True); return False
    return True


def _register_admin_home():
    @C.BOT.message_handler(commands=['sudoadmin'])
    def plus_admin_home(message):
        if not C.is_admin(message.from_user.id): C.BOT.send_message(message.chat.id,'❌ شما به این بخش دسترسی ندارید.'); return
        C.audit('ADMIN_PANEL_OPEN',message.from_user.id,send=False); _admin_send(message.chat.id,ui.admin_home(),ui.admin_menu())
    C.promote_message()


def _register_shop():
    @C.BOT.message_handler(func=lambda m:m.text=='🛍 مشاهده و خرید پلان‌ها')
    def plus_shop(message):
        blocked,reason=C.blocked(message.from_user.id)
        if blocked: C.BOT.send_message(message.chat.id,'🚫 امکان خرید برای حساب شما غیرفعال است.'+(f'\nدلیل: {reason}' if reason else ''),reply_markup=ui.main_menu()); return
        if C.mode() in {'SALES_PAUSED','MAINTENANCE'}: C.BOT.send_message(message.chat.id,C.setting('maintenance_message','🛠 فروش موقتاً متوقف است.'),reply_markup=ui.main_menu()); return
        if C.setting('plan_categories_enabled','1')!='1': return C.CORE.show_plans(message)
        m,rows=ui.categories_markup()
        if not rows: return C.CORE.show_plans(message)
        C.BOT.send_message(message.chat.id,'🛍 <b>فروشگاه SpeedPing</b>\n━━━━━━━━━━━━━━━━\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m)
    C.promote_message()


def _register_account():
    @C.BOT.message_handler(func=lambda m:m.text=='👤 حساب کاربری')
    def plus_account(message):
        uid=int(message.from_user.id); c=C.db(); user=c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone(); paid=c.execute("SELECT id,service_email,plan_name_snapshot FROM transactions WHERE user_id=? AND status='APPROVED' AND kind='NEW' ORDER BY id DESC",(uid,)).fetchall(); trial=c.execute("SELECT email,status FROM trial_services WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(uid,)).fetchone(); linked=c.execute('SELECT id,email FROM linked_services WHERE user_id=? ORDER BY id DESC',(uid,)).fetchall(); c.close(); bal=int(user['balance'] or 0) if user else 0
        lines=['👤 <b>حساب کاربری</b>','━━━━━━━━━━━━━━━━',f'🆔 <code>{uid}</code>',f'👛 موجودی: <b>{bal:,} تومان</b>',f'📦 سرویس‌های خریداری‌شده: <b>{len(paid)}</b>',f'🔗 سرویس‌های متصل‌شده: <b>{len(linked)}</b>']
        if trial: lines.append(f"🎁 وضعیت تست: <b>{escape(str(trial['status']))}</b>")
        blocked,reason=C.blocked(uid)
        if blocked: lines += ['','🚫 <b>خرید برای این حساب محدود شده است.</b>'+(f'\n{escape(reason)}' if reason else '')]
        lines += ['','👇 برای مدیریت هر سرویس، دکمه مربوط به آن را انتخاب کنید.']; m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
        if trial and trial['status']=='ACTIVE': m.add(C.inline('🎁 وضعیت تست رایگان',callback_data='view:trial',style_name='primary'))
        for r in paid: m.add(C.inline(f"📦 {(r['plan_name_snapshot'] or r['service_email'] or f'Service #{r['id']}')[:42]}",callback_data=f"view:status:{r['id']}",style_name='primary'))
        for r in linked: m.add(C.inline(f"🔗 {r['email'][:42]}",callback_data=f"view:linked:{r['id']}"))
        m.row(C.inline('🧾 تاریخچه خرید',callback_data='account:purchases'),C.inline('📜 کیف پول',callback_data='ref:wallet_history'))
        if C.CORE.existing_service_link_enabled(): m.add(C.inline('➕ افزودن سرویس قبلی',callback_data='account:link_existing',style_name='success'))
        if C.CORE.connection_guides_enabled(): m.add(C.inline('📲 راهنمای اتصال',callback_data='guide:menu',style_name='primary',emoji_key='guide'))
        if C.setting('feedback_enabled','1')=='1': m.add(C.inline('⭐ ثبت نظر و امتیاز',callback_data='plus:feedback:user',style_name='primary'))
        C.BOT.send_message(uid,'\n'.join(lines),parse_mode='HTML',reply_markup=m)
    C.promote_message()


def _register_feedback_message():
    @C.BOT.message_handler(func=lambda m:m.text=='⭐ نظر و امتیاز')
    def feedback_entry(message):
        if C.setting('feedback_enabled','1')!='1': C.BOT.send_message(message.chat.id,'این بخش در حال حاضر غیرفعال است.',reply_markup=ui.main_menu()); return
        C.BOT.send_message(message.chat.id,'⭐ <b>تجربه شما چطور بود؟</b>\n\nاز ۱ تا ۵ امتیاز بدهید. بعدش اگر خواستید یک توضیح کوتاه هم می‌توانید بنویسید.',parse_mode='HTML',reply_markup=_rating_markup())
    C.promote_message()


def _save_feedback_comment(message,feedback_id):
    if _back(message): return
    text=(message.text or message.caption or '').strip(); text='' if text in {'-','ندارم','بدون توضیح'} else text
    c=C.db(); c.execute('UPDATE customer_feedback SET comment=? WHERE id=? AND user_id=?',(text[:1000] or None,int(feedback_id),int(message.from_user.id))); c.commit(); c.close(); C.BOT.send_message(message.chat.id,'🙏 ممنون! نظر شما ثبت شد.',reply_markup=ui.main_menu())


def _register_emoji_command():
    @C.BOT.message_handler(commands=['emojiid'])
    def emoji_id_help(message):
        if not C.is_admin(message.from_user.id): return
        msg=C.BOT.send_message(message.chat.id,'✨ یک Custom Emoji تلگرام را در پیام بعدی ارسال کنید تا ID آن را استخراج کنم.\n\nاگر پیام فقط ایموجی معمولی باشد، ID قابل استخراج نیست.',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_emoji_id_process)
    C.promote_message()

def _emoji_id_process(message):
    if _back(message): return
    entities=list(message.entities or [])+list(message.caption_entities or []); ids=[str(e.custom_emoji_id) for e in entities if getattr(e,'type',None)=='custom_emoji' and getattr(e,'custom_emoji_id',None)]
    if not ids: C.BOT.send_message(message.chat.id,'❌ Custom Emoji ID پیدا نشد. خود Custom Emoji پریمیوم را ارسال کنید.',reply_markup=ui.main_menu()); return
    C.BOT.send_message(message.chat.id,'✅ ID پیدا شد:\n'+'\n'.join(f'<code>{escape(x)}</code>' for x in ids),parse_mode='HTML',reply_markup=ui.main_menu())


def _register_plus_callback():
    @C.BOT.callback_query_handler(func=lambda call:(call.data or '').startswith('plus:'))
    def plus_router(call):
        data=call.data or ''; parts=data.split(':'); action=parts[1] if len(parts)>1 else ''
        if action=='shop': C.BOT.answer_callback_query(call.id); m,_=ui.categories_markup(); C.BOT.send_message(call.from_user.id,'🛍 <b>دسته‌بندی پلان‌ها</b>\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m); return
        if action=='shopcat': C.BOT.answer_callback_query(call.id); ui.send_category(call.from_user.id,call.from_user.id,int(parts[2])); return
        if action=='feedback' and len(parts)>2 and parts[2]=='user': C.BOT.answer_callback_query(call.id); C.BOT.send_message(call.from_user.id,'⭐ <b>از ۱ تا ۵ امتیاز بدهید:</b>',parse_mode='HTML',reply_markup=_rating_markup()); return
        if action=='rate':
            if C.setting('feedback_enabled','1')!='1': C.BOT.answer_callback_query(call.id,'غیرفعال است.',show_alert=True); return
            rating=max(1,min(5,int(parts[2]))); c=C.db(); cur=c.execute('INSERT INTO customer_feedback(user_id,rating,created_at) VALUES (?,?,?)',(int(call.from_user.id),rating,int(time.time()))); fid=int(cur.lastrowid); c.commit(); c.close(); C.BOT.answer_callback_query(call.id,'ثبت شد ✅'); msg=C.BOT.send_message(call.from_user.id,f'🙏 امتیاز <b>{rating}/5</b> ثبت شد.\nاگر توضیحی دارید بنویسید؛ برای رد کردن فقط <code>-</code> بفرستید.',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_save_feedback_comment,fid); C.audit('CUSTOMER_FEEDBACK',call.from_user.id,rating,send=False); return
        if not _admin_guard(call): return
        uid=int(call.from_user.id); chat=call.message.chat.id
        if action=='home': C.BOT.answer_callback_query(call.id); _admin_send(chat,ui.admin_home(),ui.admin_menu()); return
        if action=='mode':
            C.BOT.answer_callback_query(call.id); m=C.CORE.types.InlineKeyboardMarkup(row_width=1); m.add(C.inline('🟢 حالت عادی',callback_data='plus:modeset:NORMAL',style_name='success'),C.inline('🟠 توقف فروش',callback_data='plus:modeset:SALES_PAUSED',style_name='primary'),C.inline('🔴 حالت تعمیرات',callback_data='plus:modeset:MAINTENANCE',style_name='danger')); _admin_send(chat,f'⚙️ <b>وضعیت عملیاتی</b>\n━━━━━━━━━━━━━━━━\nوضعیت فعلی: <b>{_mode_text()}</b>\n\n• توقف فروش: خرید/تمدید/حجم بسته می‌شود.\n• تعمیرات: خرید و تست بسته می‌شود؛ حساب، آموزش و پشتیبانی در دسترس می‌مانند.',m); return
        if action=='modeset':
            val=parts[2] if len(parts)>2 else 'NORMAL'; C.set_setting('operating_mode',val); C.audit('OPERATING_MODE_CHANGED',uid,val); C.BOT.answer_callback_query(call.id,'ذخیره شد ✅'); _admin_send(chat,f'✅ حالت سیستم تغییر کرد:\n<b>{_mode_text()}</b>',ui.admin_menu()); return
        if action=='blacklist':
            C.BOT.answer_callback_query(call.id); c=C.db(); rows=c.execute('SELECT user_id,reason FROM user_blocks WHERE active=1 ORDER BY updated_at DESC LIMIT 15').fetchall(); c.close(); text=['🚫 <b>مدیریت محدودیت کاربران</b>','━━━━━━━━━━━━━━━━',f'کاربران محدودشده: <b>{len(rows)}</b> (۱۵ مورد آخر)']+[f"• <code>{r['user_id']}</code> — {escape((r['reason'] or '-')[:70])}" for r in rows]; m=C.CORE.types.InlineKeyboardMarkup(row_width=2); m.row(C.inline('➕ مسدود کردن',callback_data='plus:blockadd',style_name='danger'),C.inline('✅ رفع محدودیت',callback_data='plus:blockremove',style_name='success')); _admin_send(chat,'\n'.join(text),m); return
        if action=='blockadd': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'🚫 فرمت: <code>TelegramID | دلیل</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_block_add,uid); return
        if action=='blockremove': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'✅ Telegram ID کاربر را بفرستید.',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_block_remove,uid); return
        if action=='categories':
            C.BOT.answer_callback_query(call.id); storage.backfill_categories(); c=C.db(); rows=c.execute('SELECT c.id,c.name,c.active,COUNT(p.id) n FROM plan_categories c LEFT JOIN plans p ON p.category_id=c.id GROUP BY c.id ORDER BY c.sort_order,c.id').fetchall(); c.close(); text=['🗂 <b>دسته‌بندی پلان‌ها</b>','━━━━━━━━━━━━━━━━']+[f"• <code>#{r['id']}</code> {'🟢' if r['active'] else '🔴'} <b>{escape(r['name'])}</b> — {r['n']} پلان" for r in rows]; m=C.CORE.types.InlineKeyboardMarkup(row_width=2); m.row(C.inline('➕ دسته جدید',callback_data='plus:catadd',style_name='success'),C.inline('✏️ تغییر نام',callback_data='plus:catrename')); m.row(C.inline('📦 انتقال پلان',callback_data='plus:catassign',style_name='primary'),C.inline('⏯ فعال/غیرفعال',callback_data='plus:cattoggle')); _admin_send(chat,'\n'.join(text),m); return
        if action=='catadd': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'➕ نام دسته جدید را بفرستید.',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_cat_add,uid); return
        if action=='catrename': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'✏️ فرمت: <code>CategoryID | نام جدید</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_cat_rename,uid); return
        if action=='catassign': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'📦 فرمت: <code>PlanID | CategoryID</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_cat_assign,uid); return
        if action=='cattoggle': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'⏯ ID دسته را بفرستید.',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_cat_toggle,uid); return
        if action=='trialoverrides':
            C.BOT.answer_callback_query(call.id); c=C.db(); rows=c.execute('SELECT * FROM trial_overrides ORDER BY updated_at DESC LIMIT 15').fetchall(); c.close(); text=['🎯 <b>تست اختصاصی کاربر</b>','━━━━━━━━━━━━━━━━','برای کاربر خاص می‌توان حجم/روز/IP را قبل از اولین دریافت تست تغییر داد.']+[f"• <code>{r['user_id']}</code> — {r['volume_gb']:g}GB / {r['days']} روز / IP {r['ip_limit']}" for r in rows]; m=C.CORE.types.InlineKeyboardMarkup(row_width=2); m.row(C.inline('➕ ثبت/ویرایش',callback_data='plus:trialset',style_name='success'),C.inline('🗑 حذف Override',callback_data='plus:trialdel',style_name='danger')); _admin_send(chat,'\n'.join(text),m); return
        if action=='trialset': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'🎯 فرمت:\n<code>TelegramID | حجمGB | روز | IP | یادداشت اختیاری</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_trial_set,uid); return
        if action=='trialdel': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'🗑 Telegram ID را بفرستید.',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_trial_del,uid); return
        if action=='feedback': C.BOT.answer_callback_query(call.id); m=C.CORE.types.InlineKeyboardMarkup(row_width=1); m.add(C.inline(f"{'🟢' if C.setting('feedback_enabled','1')=='1' else '🔴'} روشن/خاموش بازخورد",callback_data='plus:feedbacktoggle',style_name='primary')); _admin_send(chat,storage.feedback_text(),m); return
        if action=='feedbacktoggle':
            new='0' if C.setting('feedback_enabled','1')=='1' else '1'; C.set_setting('feedback_enabled',new); C.audit('FEEDBACK_TOGGLE',uid,new); C.BOT.answer_callback_query(call.id,'ذخیره شد ✅'); _admin_send(chat,storage.feedback_text()); return
        if action=='broadcast':
            C.BOT.answer_callback_query(call.id); m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
            for code,title in [('all','👥 همه کاربران فعال'),('customers','💳 مشتریان خریدار'),('trial','🎁 تست‌گرفته و نخریده'),('expired_trial','⌛ تست منقضی و نخریده'),('never_bought','🧲 هنوز خرید نکرده')]: m.add(C.inline(title,callback_data=f'plus:bcaud:{code}',style_name='primary'))
            _admin_send(chat,'📣 <b>ارسال پیام هدفمند</b>\n━━━━━━━━━━━━━━━━\nابتدا مخاطب را انتخاب کنید. پیام بعدی شما با Copy Message ارسال می‌شود؛ متن، عکس، ویدئو یا فایل قابل ارسال است.',m); return
        if action=='bcaud':
            code=parts[2]; users=storage.audiences(code); C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,f'📣 مخاطب: <b>{len(users):,}</b> کاربر\nپیام موردنظر را بفرستید.',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_broadcast_message,uid,code); return
        if action=='audit':
            C.BOT.answer_callback_query(call.id); c=C.db(); rows=c.execute('SELECT event_type,actor_id,target_id FROM audit_events ORDER BY id DESC LIMIT 12').fetchall(); c.close(); text=['🧾 <b>Audit Log</b>','━━━━━━━━━━━━━━━━',f"ارسال به چت: <code>{escape(C.setting('audit_chat_id','') or 'تنظیم نشده')}</code>",f"وضعیت: <b>{'فعال' if C.setting('audit_enabled','1')=='1' else 'غیرفعال'}</b>",'']+[f"• <b>{escape(r['event_type'])}</b> — <code>{r['actor_id'] or '-'}</code> → <code>{escape(str(r['target_id'] or '-'))}</code>" for r in rows]; m=C.CORE.types.InlineKeyboardMarkup(row_width=2); m.row(C.inline('⏯ روشن/خاموش',callback_data='plus:audittoggle'),C.inline('💬 تنظیم Chat ID',callback_data='plus:auditchat',style_name='primary')); _admin_send(chat,'\n'.join(text),m); return
        if action=='audittoggle': new='0' if C.setting('audit_enabled','1')=='1' else '1'; C.set_setting('audit_enabled',new); C.BOT.answer_callback_query(call.id,'ذخیره شد ✅'); _admin_send(chat,f"✅ Audit Log {'فعال' if new=='1' else 'غیرفعال'} شد."); return
        if action=='auditchat': C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,'💬 Chat ID کانال/گروه لاگ را بفرستید. برای غیرفعال‌کردن: <code>0</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_audit_chat,uid); return
        if action=='snapshot': C.BOT.answer_callback_query(call.id,'در حال ساخت Snapshot...'); threading.Thread(target=ops.send_panel_snapshot,args=(chat,uid),daemon=True).start(); return
        if action=='ui': C.BOT.answer_callback_query(call.id); _send_ui_panel(chat); return
        if action=='uistyle':
            key=parts[2]; cur=C.setting('ui_style_'+key,'default'); seq=['default','primary','success','danger']; nxt=seq[(seq.index(cur)+1)%len(seq)] if cur in seq else 'primary'; C.set_setting('ui_style_'+key,nxt); C.audit('UI_STYLE_CHANGED',uid,key,nxt,send=False); C.BOT.answer_callback_query(call.id,f'{key}: {nxt}'); _send_ui_panel(chat); return
        if action=='premiumtoggle':
            new='0' if C.setting('ui_premium_emoji_enabled','0')=='1' else '1'
            if new=='1':
                configured=[C.setting('ui_emoji_'+k,'').strip() for k in C.EMOJI_KEYS if C.setting('ui_emoji_'+k,'').strip()]
                if configured:
                    try:
                        test=C.CORE.types.InlineKeyboardMarkup(); test.add(C.CORE.types.InlineKeyboardButton('✨ تست Custom Emoji',callback_data='plus:noop',style='primary',icon_custom_emoji_id=configured[0])); C.BOT.send_message(chat,'✨ تست Custom Emoji',reply_markup=test)
                    except Exception as e: C.BOT.answer_callback_query(call.id,'تلگرام اجازه این Custom Emoji را نداد.',show_alert=True); _admin_send(chat,f'❌ قابلیت فعال نشد.\n<code>{escape(str(e)[:300])}</code>'); return
            C.set_setting('ui_premium_emoji_enabled',new); C.BOT.answer_callback_query(call.id,'ذخیره شد ✅'); _send_ui_panel(chat); return
        if action=='emojiset': key=parts[2]; C.BOT.answer_callback_query(call.id); msg=C.BOT.send_message(chat,f'✨ یک Custom Emoji برای <b>{escape(C.EMOJI_KEYS.get(key,key))}</b> ارسال کنید. برای پاک‌کردن: <code>0</code>',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_emoji_set,key,uid); return
        if action=='uipreset':
            for k,v in {'buy':'success','account':'primary','trial':'success','guide':'primary','support':'primary','admin':'primary'}.items(): C.set_setting('ui_style_'+k,v)
            C.audit('UI_PRESET_APPLIED',uid,'professional',send=False); C.BOT.answer_callback_query(call.id,'Preset اعمال شد ✅'); _send_ui_panel(chat); return
        if action=='noop': C.BOT.answer_callback_query(call.id,'تست موفق بود ✅'); return
    C.promote_callback()


def _send_ui_panel(chat):
    names={'default':'پیش‌فرض','primary':'آبی','success':'سبز','danger':'قرمز'}; lines=['🎨 <b>ظاهر و دکمه‌ها</b>','━━━━━━━━━━━━━━━━','Telegram رنگ دلخواه RGB نمی‌دهد؛ از Styleهای رسمی استفاده می‌کنیم.','']; m=C.CORE.types.InlineKeyboardMarkup(row_width=2)
    for key in C.EMOJI_KEYS:
        cur=C.setting('ui_style_'+key,'default'); lines.append(f"• {C.EMOJI_KEYS[key]}: <b>{names.get(cur,cur)}</b>"); m.add(C.inline(f"🎨 {C.EMOJI_KEYS[key]}",callback_data=f'plus:uistyle:{key}',style_name=C.style(key) or None))
    prem=C.setting('ui_premium_emoji_enabled','0')=='1'; lines += ['',f"✨ Custom Emoji: <b>{'فعال' if prem else 'غیرفعال'}</b>"]; m.row(C.inline('✨ Premium Emoji ON/OFF',callback_data='plus:premiumtoggle',style_name='primary'),C.inline('🎯 Preset حرفه‌ای',callback_data='plus:uipreset',style_name='success'))
    for key in C.EMOJI_KEYS: m.add(C.inline(f"✨ ایموجی {C.EMOJI_KEYS[key]}",callback_data=f'plus:emojiset:{key}'))
    _admin_send(chat,'\n'.join(lines),m)


def _block_add(message,actor):
    if _back(message): return
    try:
        p=[x.strip() for x in (message.text or '').split('|',1)]; uid=int(p[0]); reason=p[1] if len(p)>1 else 'محدودیت مدیریتی'; now=int(time.time()); c=C.db(); c.execute('INSERT INTO user_blocks(user_id,reason,active,created_at,created_by,updated_at) VALUES (?,?,1,?,?,?) ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,active=1,created_by=excluded.created_by,updated_at=excluded.updated_at',(uid,reason[:500],now,int(actor),now)); c.commit(); c.close(); C.audit('USER_BLOCKED',actor,uid,reason); C.BOT.send_message(message.chat.id,f'✅ کاربر <code>{uid}</code> محدود شد.',parse_mode='HTML',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ فرمت نامعتبر است.',reply_markup=ui.admin_menu())

def _block_remove(message,actor):
    if _back(message): return
    try: uid=int((message.text or '').strip()); c=C.db(); c.execute('UPDATE user_blocks SET active=0,updated_at=? WHERE user_id=?',(int(time.time()),uid)); c.commit(); c.close(); C.audit('USER_UNBLOCKED',actor,uid); C.BOT.send_message(message.chat.id,f'✅ محدودیت <code>{uid}</code> برداشته شد.',parse_mode='HTML',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ Telegram ID نامعتبر است.',reply_markup=ui.admin_menu())

def _cat_add(message,actor):
    if _back(message): return
    name=(message.text or '').strip()
    if not name or len(name)>60: C.BOT.send_message(message.chat.id,'❌ نام نامعتبر است.',reply_markup=ui.admin_menu()); return
    try: c=C.db(); sort=int(c.execute('SELECT COALESCE(MAX(sort_order),0)+10 FROM plan_categories').fetchone()[0]); now=int(time.time()); c.execute('INSERT INTO plan_categories(name,active,sort_order,created_at,updated_at) VALUES (?,1,?,?,?)',(name,sort,now,now)); c.commit(); c.close(); C.audit('CATEGORY_CREATED',actor,name); C.BOT.send_message(message.chat.id,'✅ دسته ساخته شد.',reply_markup=ui.admin_menu())
    except Exception as e: C.BOT.send_message(message.chat.id,f'❌ ساخت دسته انجام نشد: {str(e)[:150]}',reply_markup=ui.admin_menu())
def _cat_rename(message,actor):
    if _back(message): return
    try: p=[x.strip() for x in (message.text or '').split('|',1)]; cid=int(p[0]); name=p[1]; c=C.db(); c.execute('UPDATE plan_categories SET name=?,updated_at=? WHERE id=?',(name[:60],int(time.time()),cid)); c.commit(); c.close(); C.audit('CATEGORY_RENAMED',actor,cid,name); C.BOT.send_message(message.chat.id,'✅ نام دسته تغییر کرد.',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ فرمت نامعتبر.',reply_markup=ui.admin_menu())
def _cat_assign(message,actor):
    if _back(message): return
    try:
        p=[x.strip() for x in (message.text or '').split('|')]; pid,cid=int(p[0]),int(p[1]); c=C.db(); cat=c.execute('SELECT 1 FROM plan_categories WHERE id=?',(cid,)).fetchone(); plan=c.execute('SELECT 1 FROM plans WHERE id=?',(pid,)).fetchone()
        if not cat or not plan: raise ValueError
        c.execute('UPDATE plans SET category_id=?,updated_at=? WHERE id=?',(cid,int(time.time()),pid)); c.commit(); c.close(); C.audit('PLAN_CATEGORY_CHANGED',actor,pid,cid); C.BOT.send_message(message.chat.id,'✅ پلان منتقل شد.',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ Plan ID یا Category ID نامعتبر است.',reply_markup=ui.admin_menu())
def _cat_toggle(message,actor):
    if _back(message): return
    try:
        cid=int((message.text or '').strip()); c=C.db(); r=c.execute('SELECT active FROM plan_categories WHERE id=?',(cid,)).fetchone()
        if not r: raise ValueError
        new=0 if int(r[0]) else 1; c.execute('UPDATE plan_categories SET active=?,updated_at=? WHERE id=?',(new,int(time.time()),cid)); c.commit(); c.close(); C.audit('CATEGORY_TOGGLED',actor,cid,new); C.BOT.send_message(message.chat.id,f"✅ دسته {'فعال' if new else 'غیرفعال'} شد.",reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ ID نامعتبر.',reply_markup=ui.admin_menu())
def _trial_set(message,actor):
    if _back(message): return
    try:
        p=[x.strip() for x in (message.text or '').split('|')]; uid=int(p[0]); gb=float(p[1]); days=int(p[2]); ip=int(p[3]); note=p[4][:500] if len(p)>4 else ''; assert gb>0 and days>0 and ip>=0; c=C.db(); now=int(time.time()); c.execute('INSERT INTO trial_overrides(user_id,volume_gb,days,ip_limit,note,updated_at,updated_by) VALUES (?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET volume_gb=excluded.volume_gb,days=excluded.days,ip_limit=excluded.ip_limit,note=excluded.note,updated_at=excluded.updated_at,updated_by=excluded.updated_by',(uid,gb,days,ip,note,now,int(actor))); c.commit(); c.close(); C.audit('TRIAL_OVERRIDE_SET',actor,uid,f'{gb}GB/{days}d/ip{ip}'); C.BOT.send_message(message.chat.id,'✅ تست اختصاصی ذخیره شد.',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ فرمت نامعتبر است.',reply_markup=ui.admin_menu())
def _trial_del(message,actor):
    if _back(message): return
    try: uid=int((message.text or '').strip()); c=C.db(); c.execute('DELETE FROM trial_overrides WHERE user_id=?',(uid,)); c.commit(); c.close(); C.audit('TRIAL_OVERRIDE_DELETED',actor,uid); C.BOT.send_message(message.chat.id,'✅ Override حذف شد.',reply_markup=ui.admin_menu())
    except Exception: C.BOT.send_message(message.chat.id,'❌ ID نامعتبر.',reply_markup=ui.admin_menu())
def _broadcast_message(message,actor,audience):
    if _back(message): return
    users=storage.audiences(audience); C.BOT.send_message(message.chat.id,f'📣 ارسال برای {len(users):,} کاربر شروع شد. نتیجه پس از پایان ارسال می‌شود.',reply_markup=ui.admin_menu()); threading.Thread(target=ops.broadcast,args=(message.chat.id,message.message_id,int(actor),audience,users),daemon=True).start()
def _audit_chat(message,actor):
    if _back(message): return
    raw=(message.text or '').strip()
    if raw=='0': C.set_setting('audit_chat_id',''); C.BOT.send_message(message.chat.id,'✅ ارسال تلگرامی Audit غیرفعال شد.',reply_markup=ui.admin_menu()); return
    try: cid=int(raw); C.BOT.send_message(cid,'🧾 SpeedyBot Audit Channel test ✅'); C.set_setting('audit_chat_id',str(cid)); C.audit('AUDIT_CHAT_CHANGED',actor,cid,send=False); C.BOT.send_message(message.chat.id,'✅ Chat ID ذخیره و تست شد.',reply_markup=ui.admin_menu())
    except Exception as e: C.BOT.send_message(message.chat.id,f'❌ امکان ارسال به این Chat ID نبود: {str(e)[:180]}',reply_markup=ui.admin_menu())
def _emoji_set(message,key,actor):
    if _back(message): return
    if (message.text or '').strip()=='0': C.set_setting('ui_emoji_'+key,''); C.BOT.send_message(message.chat.id,'✅ Custom Emoji پاک شد.',reply_markup=ui.admin_menu()); return
    entities=list(message.entities or [])+list(message.caption_entities or []); eid=next((str(e.custom_emoji_id) for e in entities if getattr(e,'type',None)=='custom_emoji' and getattr(e,'custom_emoji_id',None)),None)
    if not eid: C.BOT.send_message(message.chat.id,'❌ Custom Emoji تشخیص داده نشد. از /emojiid هم می‌توانید برای تست استفاده کنید.',reply_markup=ui.admin_menu()); return
    C.set_setting('ui_emoji_'+key,eid); C.audit('UI_EMOJI_CHANGED',actor,key,eid,send=False); C.BOT.send_message(message.chat.id,f'✅ Custom Emoji برای {C.EMOJI_KEYS.get(key,key)} ذخیره شد.\nID: <code>{escape(eid)}</code>',parse_mode='HTML',reply_markup=ui.admin_menu())

def register():
    _register_admin_home(); _register_shop(); _register_account(); _register_feedback_message(); _register_emoji_command(); _register_plus_callback()
