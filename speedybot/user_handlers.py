from html import escape
import time
from . import context as C
from . import ui


def _rating_markup():
    m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
    for n in range(5,0,-1):
        m.add(C.inline('⭐'*n,callback_data=f'plus:rate:{n}',style_name='success' if n>=4 else ('danger' if n<=2 else 'primary')))
    return m


def _save_comment(message, feedback_id):
    if (message.text or '').strip()=='🔙 بازگشت به منوی اصلی':
        C.CORE.go_to_main_menu(message); return
    text=(message.text or message.caption or '').strip()
    if text in {'-','ندارم','بدون توضیح'}: text=''
    c=C.db(); c.execute('UPDATE customer_feedback SET comment=? WHERE id=? AND user_id=?',(text[:1000] or None,int(feedback_id),int(message.from_user.id))); c.commit(); c.close()
    C.BOT.send_message(message.chat.id,'🙏 ممنون! نظر شما ثبت شد.',reply_markup=ui.main_menu())


def _shop(message):
    blocked,reason=C.blocked(message.from_user.id)
    if blocked:
        C.BOT.send_message(message.chat.id,'🚫 امکان خرید برای حساب شما غیرفعال است.'+(f'\nدلیل: {reason}' if reason else ''),reply_markup=ui.main_menu()); return
    current_mode=C.mode()
    if current_mode=='SALES_PAUSED':
        C.BOT.send_message(message.chat.id,C.setting('sales_paused_message','🛒 فروش و تمدید موقتاً متوقف شده است.'),reply_markup=ui.main_menu()); return
    if current_mode=='MAINTENANCE':
        C.BOT.send_message(message.chat.id,C.setting('maintenance_message','🛠 سرویس موقتاً در حال نگهداری است.'),reply_markup=ui.main_menu()); return
    if C.setting('plan_categories_enabled','1')!='1': return C.CORE.show_plans(message)
    m,rows=ui.categories_markup()
    if not rows: return C.CORE.show_plans(message)
    C.BOT.send_message(message.chat.id,f'🛍 <b>فروشگاه {escape(C.brand_name())}</b>\n━━━━━━━━━━━━━━━━\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m)


def _account(message):
    uid=int(message.from_user.id); c=C.db()
    user=c.execute('SELECT balance FROM users WHERE id=?',(uid,)).fetchone()
    paid=c.execute("SELECT id,service_email,plan_name_snapshot FROM transactions WHERE user_id=? AND status='APPROVED' AND kind='NEW' ORDER BY id DESC",(uid,)).fetchall()
    trial=c.execute("SELECT email,status FROM trial_services WHERE user_id=? ORDER BY created_at DESC LIMIT 1",(uid,)).fetchone()
    linked=c.execute('SELECT id,email FROM linked_services WHERE user_id=? ORDER BY id DESC',(uid,)).fetchall(); c.close()
    balance=int(user['balance'] or 0) if user else 0
    lines=['👤 <b>حساب کاربری</b>','━━━━━━━━━━━━━━━━',f'🆔 <code>{uid}</code>',f'👛 موجودی: <b>{balance:,} تومان</b>',f'📦 سرویس‌های خریداری‌شده: <b>{len(paid)}</b>',f'🔗 سرویس‌های متصل‌شده: <b>{len(linked)}</b>']
    if trial: lines.append(f"🎁 وضعیت تست: <b>{escape(str(trial['status']))}</b>")
    blocked,reason=C.blocked(uid)
    if blocked: lines += ['','🚫 <b>خرید برای این حساب محدود شده است.</b>'+(f'\n{escape(reason)}' if reason else '')]
    lines += ['','👇 برای مدیریت هر سرویس، دکمه مربوط به آن را انتخاب کنید.']
    m=C.CORE.types.InlineKeyboardMarkup(row_width=1)
    if trial and trial['status']=='ACTIVE': m.add(C.inline('🎁 وضعیت تست رایگان',callback_data='view:trial',style_name='primary'))
    for r in paid:
        label=(r['plan_name_snapshot'] or r['service_email'] or f"سرویس #{r['id']}")[:42]
        m.add(C.inline(f'📦 {label}',callback_data=f"view:status:{r['id']}",style_name='primary'))
    for r in linked: m.add(C.inline(f"🔗 {r['email'][:42]}",callback_data=f"view:linked:{r['id']}"))
    m.row(C.inline('🧾 تاریخچه خرید',callback_data='account:purchases'),C.inline('📜 کیف پول',callback_data='ref:wallet_history'))
    if C.CORE.existing_service_link_enabled(): m.add(C.inline('➕ افزودن سرویس قبلی',callback_data='account:link_existing',style_name='success'))
    if C.CORE.connection_guides_enabled(): m.add(C.inline('📲 راهنمای اتصال',callback_data='guide:menu',style_name='primary',emoji_key='guide'))
    if C.menu_visible('feedback') and C.setting('feedback_enabled','1')=='1': m.add(C.inline('⭐ ثبت نظر و امتیاز',callback_data='plus:feedback:user',style_name='primary'))
    C.BOT.send_message(uid,'\n'.join(lines),parse_mode='HTML',reply_markup=m)


def _feedback(message):
    if not C.menu_visible('feedback') or C.setting('feedback_enabled','1')!='1':
        C.BOT.send_message(message.chat.id,'این بخش در حال حاضر غیرفعال است.',reply_markup=ui.main_menu()); return
    C.BOT.send_message(message.chat.id,'⭐ <b>تجربه شما چطور بود؟</b>\n\nاز ۱ تا ۵ امتیاز بدهید. بعدش اگر خواستید یک توضیح کوتاه هم بنویسید.',parse_mode='HTML',reply_markup=_rating_markup())


def public_callback(call):
    parts=(call.data or '').split(':'); action=parts[1] if len(parts)>1 else ''
    if action=='shop':
        C.BOT.answer_callback_query(call.id); m,_=ui.categories_markup(); C.BOT.send_message(call.from_user.id,'🛍 <b>دسته‌بندی پلان‌ها</b>\nدسته موردنظر را انتخاب کنید:',parse_mode='HTML',reply_markup=m); return True
    if action=='shopcat': C.BOT.answer_callback_query(call.id); ui.send_category(call.from_user.id,call.from_user.id,int(parts[2])); return True
    if action=='feedback' and len(parts)>2 and parts[2]=='user':
        if not C.menu_visible('feedback') or C.setting('feedback_enabled','1')!='1': C.BOT.answer_callback_query(call.id,'غیرفعال است.',show_alert=True); return True
        C.BOT.answer_callback_query(call.id); C.BOT.send_message(call.from_user.id,'⭐ <b>از ۱ تا ۵ امتیاز بدهید:</b>',parse_mode='HTML',reply_markup=_rating_markup()); return True
    if action=='rate':
        if not C.menu_visible('feedback') or C.setting('feedback_enabled','1')!='1': C.BOT.answer_callback_query(call.id,'غیرفعال است.',show_alert=True); return True
        rating=max(1,min(5,int(parts[2]))); c=C.db(); cur=c.execute('INSERT INTO customer_feedback(user_id,rating,created_at) VALUES (?,?,?)',(int(call.from_user.id),rating,int(time.time()))); fid=int(cur.lastrowid); c.commit(); c.close(); C.BOT.answer_callback_query(call.id,'ثبت شد ✅'); msg=C.BOT.send_message(call.from_user.id,f'🙏 امتیاز <b>{rating}/5</b> ثبت شد.\nاگر توضیحی دارید بنویسید؛ برای رد کردن فقط <code>-</code> بفرستید.',parse_mode='HTML',reply_markup=C.CORE.back_menu()); C.BOT.register_next_step_handler(msg,_save_comment,fid); C.audit('CUSTOMER_FEEDBACK',call.from_user.id,rating,send=False); return True
    return False


def register():
    C.BOT.message_handler(func=lambda m:m.text=='🛍 مشاهده و خرید پلان‌ها')(_shop); C.promote_message()
    C.BOT.message_handler(func=lambda m:m.text=='👤 حساب کاربری')(_account); C.promote_message()
    C.BOT.message_handler(func=lambda m:m.text=='⭐ نظر و امتیاز')(_feedback); C.promote_message()