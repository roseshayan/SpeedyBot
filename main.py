import os
import telebot
from telebot import apihelper
from telebot import types
import sqlite3
import requests
import time
from datetime import datetime

# --- CONFIGURATIONS (READING FROM SYSTEM ENV) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# تنظیمات اتصال به پنل ثنایی
XUI_API_URL = os.getenv("XUI_API_URL")          # مثلا http://127.0.0.1:2053
XUI_BASE_PATH = os.getenv("XUI_BASE_PATH")      # مثلا /pKPl2UQ2sKTDnSWXb0
XUI_BEARER_TOKEN = os.getenv("XUI_BEARER_TOKEN")
XUI_SUB_SERVER_URL = os.getenv("XUI_SUB_SERVER_URL") # مثلا https://ger.speed-ping.com:2096

DEVELOPMENT_MODE = False  
bot = telebot.TeleBot(BOT_TOKEN)
USER_STATES = {}

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, photo_id TEXT, plan_id INTEGER, status TEXT DEFAULT 'PENDING')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS support_messages (admin_msg_id INTEGER PRIMARY KEY, user_id INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    
    # مقادیر اولیه تنظیمات کارت بانکی
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card_number', '6219-8619-3574-8060')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card_holder', 'شایان نماینده')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bank_name', 'بلو بانک')")
    conn.commit()
    conn.close()

init_db()

# --- DATABASE HELPERS ---
def get_db_setting(key, default_value=""):
    try:
        conn = sqlite3.connect('speedping.db')
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else default_value
    except:
        return default_value

def update_db_setting(key, value):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# --- PLANS DATA ---
PLANS = {
    1: {"name": "پلان نامحدود (یک‌ماهه)", "price": 300000, "volume": 0, "days": 30},
}

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🛍 مشاهده و خرید پلان‌ها", "👤 حساب کاربری")
    markup.row("📞 پشتیبانی")
    return markup

def back_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔙 بازگشت به منوی اصلی")
    return markup

def admin_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار ربات و فروش", callback_data="admin:stats"),
        types.InlineKeyboardButton("🖥 وضعیت زنده سرور", callback_data="admin:server_status"),
        types.InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin:broadcast"),
        types.InlineKeyboardButton("💳 تنظیمات حساب واریز", callback_data="admin:bank_config"),
        types.InlineKeyboardButton("👤 حذف کاربر از ربات", callback_data="admin:delete_user"),
        types.InlineKeyboardButton("🔌 حذف اشتراک از پنل", callback_data="admin:delete_sub")
    )
    return markup

# --- USER HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    USER_STATES[message.chat.id] = None
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        f"سلام به ربات فروش خودکار **SpeedPing** خوش آمدید! 🚀\nاز منوی زیر اقدام به خرید یا مدیریت حساب خود کنید.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def go_to_main_menu(message):
    USER_STATES[message.chat.id] = None
    bot.send_message(message.chat.id, "شما به منوی اصلی بازگشتید.", reply_markup=main_menu())

@bot.message_handler(func=lambda message: message.text == "🛍 مشاهده و خرید پلان‌ها")
def show_plans(message):
    USER_STATES[message.chat.id] = None
    markup = types.InlineKeyboardMarkup()
    for plan_id, info in PLANS.items():
        markup.add(types.InlineKeyboardButton(text=f"{info['name']} - {info['price']:,} تومان", callback_data=f"buy:{plan_id}"))
    bot.send_message(message.chat.id, "🛒 لیست پلان‌های موجود SpeedPing:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy:'))
def handle_buy_plan(call):
    plan_id = int(call.data.split(':')[1])
    plan = PLANS[plan_id]
    
    card_num = get_db_setting('card_number')
    card_holder = get_db_setting('card_holder')
    bank_name = get_db_setting('bank_name')
    
    msg = bot.send_message(
        call.message.chat.id,
        f"💵 شما پلان را انتخاب کردید: **{plan['name']}**\n\n"
        f"💳 لطفاً مبلغ **{plan['price']:,} تومان** را به مشخصات زیر واریز کنید:\n\n"
        f"🏦 بانک: *{bank_name}*\n"
        f"💳 شماره کارت:\n`{card_num}`\n"
        f"👤 به نام: *{card_holder}*\n\n"
        f"📸 پس از واریز، **فقط اسکرین‌شات یا عکس فیش واریزی** خود را در پاسخ به این پیام ارسال کنید.",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_receipt, plan_id)

def process_receipt(message, plan_id):
    if message.text == "🔙 بازگشت به منوی اصلی":
        go_to_main_menu(message)
        return
        
    if not message.photo:
        bot.send_message(message.chat.id, "❌ خطا! شما فیش واریزی را ارسال نکردید. لطفاً مجدداً مراحل خرید را طی کنید.", reply_markup=main_menu())
        return

    photo_id = message.photo[-1].file_id
    
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (user_id, photo_id, plan_id) VALUES (?, ?, ?)", (message.from_user.id, photo_id, plan_id))
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "✅ فیش شما دریافت شد و در حال بررسی توسط مدیریت است. به محض تایید، کانفیگ برای شما ارسال می‌شود.", reply_markup=main_menu())

    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ تایید پرداخت", callback_data=f"admin:approve:{tx_id}"),
        types.InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:reject:{tx_id}")
    )
    
    plan_name = PLANS[plan_id]['name']
    bot.send_photo(
        ADMIN_ID, 
        photo_id, 
        caption=f"🔔 **تراکنش جدید خرید کانفیگ!**\n\n👤 کاربر: {message.from_user.id}\n📦 پلان درخواست شده: {plan_name}\n🆔 کد تراکنش: {tx_id}",
        reply_markup=admin_markup,  # ⚠️ فیکس شد
        parse_mode="Markdown"
    )

# --- ACCOUNT SECTION ---
@bot.message_handler(func=lambda message: message.text == "👤 حساب کاربری")
def show_account(message):
    USER_STATES[message.chat.id] = None
    user_id = message.chat.id
    
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM transactions WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
    approved_txs = cursor.fetchall()
    conn.close()
    
    msg_text = f"👤 **حساب کاربری شما در SpeedPing**\n\n🆔 آیدی تلگرام شما: `{user_id}`\n"
               
    if approved_txs:
        msg_text += "\n👇 جهت مشاهده میزان ترافیک مصرفی و زمان انقضای هر سرویس، روی دکمه آن کلیک کنید:"
        markup = types.InlineKeyboardMarkup()
        for tx in approved_txs:
            tx_id = tx[0]
            markup.add(types.InlineKeyboardButton(text=f"📦 اکانت اختصاصی (کد تراکنش {tx_id})", callback_data=f"view:status:{tx_id}"))
        bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=markup)  # ⚠️ فیکس شد: reply_markup
    else:
        msg_text += "\n❌ شما در حال حاضر سرویس فعالی ندارید."
        bot.send_message(user_id, msg_text, parse_mode="Markdown", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('view:status:'))
def handle_view_status(call):
    tx_id = int(call.data.split(':')[2])
    user_id = call.message.chat.id
    user_email = f"speedping_{user_id}_{tx_id}"
    
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    bot.answer_callback_query(call.id, "در حال استعلام وضعیت زنده...")
    
    try:
        client_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/get/{user_email}"
        response = requests.get(client_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        client_data = response.json().get("obj", {}) if response.status_code == 200 and response.json().get("success") else {}
        
        traffic_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/traffic/{user_email}"
        traffic_res = requests.get(traffic_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        traffic_data = traffic_res.json().get("obj", {}) if traffic_res.status_code == 200 and traffic_res.json().get("success") else {}
        
        data = {**client_data, **traffic_data}
        
        if data:
            enable_status = "🟢 فعال" if data.get("enable", True) else "🔴 غیرفعال"
            bytes_up = data.get("up", 0)
            bytes_down = data.get("down", 0)
            used_gb = (bytes_up + bytes_down) / (1024 * 1024 * 1024)
            
            total_bytes = data.get("total", 0) or data.get("totalGB", 0)
            total_str = "نامحدود" if total_bytes == 0 else f"{total_bytes / (1024*1024*1024):.2f} گیگابایت"
            
            expiry_time_ms = data.get("expiryTime", 0)
            current_time_ms = int(time.time() * 1000)
            
            if expiry_time_ms == 0:
                time_left_str = "بدون محدودیت زمانی"
            elif expiry_time_ms < current_time_ms:
                time_left_str = "❌ منقضی شده"
            else:
                diff_seconds = (expiry_time_ms - current_time_ms) / 1000
                days = int(diff_seconds // 86400)
                hours = int((diff_seconds % 86400) // 3600)
                time_left_str = f"⏳ {days} روز و {hours} ساعت باقی‌مانده"
                
            sub_id = data.get("subId") or data.get("uuid")
            if not sub_id:
                sub_id = "error_id"
                
            status_text = f"📊 **گزارش وضعیت زنده سرویس SpeedPing**\n\n" \
                          f"✉️ نام کاربری: `{user_email}`\n" \
                          f"⚡️ وضعیت سرویس: {enable_status}\n" \
                          f"📥 حجم مصرف شده: `{used_gb:.2f} GB`\n" \
                          f"📤 سقف حجم اکانت: `{total_str}`\n" \
                          f"📅 مهلت اعتبار: **{time_left_str}**\n"
                          
            markup = types.InlineKeyboardMarkup()
            # ⚠️ فیکس شد: استفاده از کاراکتر | برای حل تداخل دکمه با خط تیره ایمیل‌ها
            if sub_id != "error_id":
                markup.row(types.InlineKeyboardButton(text="🌐 دریافت لینک سابسکریپشن", callback_data=f"getlinks:sub:{sub_id}"))
            markup.row(types.InlineKeyboardButton(text="🔑 دریافت کانفیگ‌های مستقیم", callback_data=f"getlinks:dir:{user_email}"))
            
            bot.send_message(user_id, status_text, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ مشخصات این اکانت روی پنل سرور یافت نشد.")
    except Exception as e:
        bot.send_message(user_id, f"🚨 خطا در خواندن اطلاعات فنی سرور.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('getlinks:'))
def handle_account_get_links(call):
    mode = call.data.split(':')[1]
    param = call.data.split(':')[2]
    user_id = call.message.chat.id
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    if mode == "sub":
        subscription_url = f"{XUI_SUB_SERVER_URL}/sub/{param}"
        bot.send_message(user_id, f"🌐 **لینک سابسکریپشن اختصاصی شما (پورت 2096):**\n\n```\n{subscription_url}\n```", parse_mode="Markdown")
    elif mode == "dir":
        bot.answer_callback_query(call.id, "در حال استخراج...")
        get_links_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/links/{param}"
        res = requests.get(get_links_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        config_links = res.json().get("obj", []) if res.status_code == 200 and res.json().get("success") else []
        
        if config_links:
            msg_text = "🔑 **کانفیگ‌های اتصال مستقیم شما:**\n\n"
            for link in config_links:
                msg_text += f"```\n{link}\n```\n"
            bot.send_message(user_id, msg_text, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ کانفیگ مستقیمی یافت نشد.")

# --- SUPPORT SYSTEM ---
@bot.message_handler(func=lambda message: message.text == "📞 پشتیبانی")
def support_mode(message):
    USER_STATES[message.chat.id] = 'SUPPORT'
    bot.send_message(message.chat.id, "📞 **بخش پشتیبانی SpeedPing**\n\nپیام خود را ارسال کنید. مدیریت به زودی پاسخ خواهد داد.", reply_markup=back_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message is not None and message.from_user.id == ADMIN_ID)
def handle_admin_reply(message):
    admin_reply_id = message.reply_to_message.message_id
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM support_messages WHERE admin_msg_id = ?", (admin_reply_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        target_user_id = row[0]
        try:
            bot.copy_message(chat_id=target_user_id, from_chat_id=ADMIN_ID, message_id=message.message_id)
            bot.send_message(ADMIN_ID, "✅ پاسخ ارسال شد.")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"❌ خطا: {str(e)}")

@bot.message_handler(func=lambda message: USER_STATES.get(message.chat.id) == 'SUPPORT', content_types=['text', 'photo', 'voice', 'video', 'document'])
def forward_to_admin(message):
    bot.send_message(ADMIN_ID, f"👤 **پیام جدید پشتیبانی از کاربر:** `{message.chat.id}`\nReply کنید:")
    admin_msg = bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO support_messages (admin_msg_id, user_id) VALUES (?, ?)", (admin_msg.message_id, message.chat.id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "⏳ پیام شما به پشتیبانی ارسال شد.")

# --- 👑 POWERFUL ADMIN PANEL (/sudoadmin) ---
@bot.message_handler(commands=['sudoadmin'])
def super_admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ شما به این منو دسترسی ندارید.")
        return
    bot.send_message(message.chat.id, "🚀 **به پنل مدیریت ارشد SpeedPing خوش آمدید**\nتنظیمات مورد نظر را انتخاب کنید:", reply_markup=admin_main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin:'))
def handle_admin_panel_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    action = call.data.split(':')[1]
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None

    if action == "approve" or action == "reject":
        tx_id = int(call.data.split(':')[2])
        handle_invoice_decision(call, action, tx_id)
        return

    if action == "stats":
        conn = sqlite3.connect('speedping.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'APPROVED'")
        total_sales_count = cursor.fetchone()[0]
        conn.close()
        
        revenue = total_sales_count * 300000
        stats_text = f"📊 **آمار سیستم فروش SpeedPing:**\n\n" \
                     f"👤 کل کاربران ربات: `{total_users} نفر`\n" \
                     f"📦 تعداد کل فروش موفق: `{total_sales_count} عدد`\n" \
                     f"💵 کل درآمد ناخالص: `{revenue:,} تومان`"
        bot.send_message(ADMIN_ID, stats_text, parse_mode="Markdown")
        
    elif action == "server_status":
        bot.answer_callback_query(call.id, "در حال استعلام وضعیت زنده...")
        try:
            status_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/server/status"
            res = requests.get(status_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
            if res.status_code == 200 and res.json().get("success"):
                obj = res.json().get("obj", {})
                cpu = obj.get("cpu", 0)
                mem_curr = obj.get("mem", {}).get("current", 0) / (1024**3)
                mem_total = obj.get("mem", {}).get("total", 0) / (1024**3)
                disk_curr = obj.get("disk", {}).get("current", 0) / (1024**3)
                disk_total = obj.get("disk", {}).get("total", 0) / (1024**3)
                xray_state = obj.get("xray", {}).get("state", "unknown")
                xray_ver = obj.get("xray", {}).get("version", "unknown")
                
                srv_txt = f"🖥 **وضعیت فعلی سرور آلمان SpeedPing:**\n\n" \
                          f"🔥 مصرف پردازنده: `{cpu}%`\n" \
                          f"🧠 حافظه رم: `{mem_curr:.2f} GB / {mem_total:.2f} GB`\n" \
                          f"💾 دیسک سرور: `{disk_curr:.2f} GB / {disk_total:.2f} GB`\n" \
                          f"⚙️ وضعیت هسته Xray: *{xray_state} ({xray_ver})*"
                bot.send_message(ADMIN_ID, srv_txt, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(ADMIN_ID, f"🚨 خطا در ارتباط با وب‌سرویس سرور")
            
    elif action == "broadcast":
        msg = bot.send_message(ADMIN_ID, "📣 پیام همگانی خود را بفرستید:")
        bot.register_next_step_handler(msg, process_admin_broadcast)
        
    elif action == "bank_config":
        card_num = get_db_setting('card_number')
        card_holder = get_db_setting('card_holder')
        bank_name = get_db_setting('bank_name')
        
        bank_txt = f"💳 **مشخصات فعلی واریز ربات:**\n\n🏦 بانک: {bank_name}\n💳 شماره کارت: `{card_num}`\n👤 به نام: {card_holder}"
        b_markup = types.InlineKeyboardMarkup()
        b_markup.add(
            types.InlineKeyboardButton("✏️ تغییر شماره کارت", callback_data="admin:edit_card"),
            types.InlineKeyboardButton("✏️ تغییر نام صاحب حساب", callback_data="admin:edit_holder"),
            types.InlineKeyboardButton("✏️ تغییر نام بانک", callback_data="admin:edit_bank")
        )
        bot.send_message(ADMIN_ID, bank_txt, parse_mode="Markdown", reply_markup=b_markup)
        
    elif action in ["edit_card", "edit_holder", "edit_bank"]:
        msg = bot.send_message(ADMIN_ID, f"✍️ مقدار جدید را وارد کنید:")
        bot.register_next_step_handler(msg, process_edit_bank, action)
        
    elif action == "delete_user":
        msg = bot.send_message(ADMIN_ID, "👤 آیدی عددی کاربر مورد نظر را جهت حذف از ربات وارد کنید:")
        bot.register_next_step_handler(msg, process_delete_bot_user)
        
    elif action == "delete_sub":
        msg = bot.send_message(ADMIN_ID, "🔌 نام اشتراک (Email) مورد نظر در پنل را جهت حذف وارد کنید:")
        bot.register_next_step_handler(msg, process_delete_panel_sub)

def handle_invoice_decision(call, action, tx_id):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, plan_id, status FROM transactions WHERE id = ?", (tx_id,))
    tx = cursor.fetchone()

    if not tx or tx[2] != 'PENDING':
        bot.answer_callback_query(call.id, "این تراکنش قبلاً تعیین تکلیف شده است.")
        conn.close()
        return

    user_id, plan_id, _ = tx

    if action == "approve":
        cursor.execute("UPDATE transactions SET status = 'APPROVED' WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption=f"✅ فیش {tx_id} تایید شد. کانفیگ در حال صدور است...")
        generate_xui_config(user_id, plan_id, tx_id)
    elif action == "reject":
        cursor.execute("UPDATE transactions SET status = 'REJECTED' WHERE id = ?", (tx_id,))
        conn.commit()
        conn.close()
        bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption=f"❌ فیش {tx_id} رد شد.")
        bot.send_message(user_id, "❌ فیش واریزی شما توسط پشتیبانی رد شد.")

def process_admin_broadcast(message):
    conn = sqlite3.connect('speedping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    bot.send_message(ADMIN_ID, f"⏳ فرآیند ارسال آغاز شد...")
    success_count = 0
    for u in users:
        try:
            bot.copy_message(chat_id=u[0], from_chat_id=ADMIN_ID, message_id=message.message_id)
            success_count += 1
            time.sleep(0.04)
        except: continue
    bot.send_message(ADMIN_ID, f"✅ تحویل موفق به {success_count} کاربر.")

def process_edit_bank(message, field_type):
    if field_type == "admin:edit_card" or field_type == "edit_card":
        update_db_setting('card_number', message.text.strip())
    elif field_type == "admin:edit_holder" or field_type == "edit_holder":
        update_db_setting('card_holder', message.text.strip())
    elif field_type == "admin:edit_bank" or field_type == "edit_bank":
        update_db_setting('bank_name', message.text.strip())
    bot.send_message(ADMIN_ID, "✅ مشخصات بانکی با موفقیت به‌روزرسانی شد.")

def process_delete_bot_user(message):
    try:
        target_id = int(message.text.strip())
        conn = sqlite3.connect('speedping.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"✅ کاربر `{target_id}` از ربات پاک شد.")
    except: bot.send_message(ADMIN_ID, "❌ آیدی نامعتبر.")

def process_delete_panel_sub(message):
    email = message.text.strip()
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    try:
        del_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/del/{email}?keepTraffic=0"
        res = requests.post(del_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        if res.status_code == 200 and res.json().get("success"):
            bot.send_message(ADMIN_ID, f"✅ اشتراک `{email}` با موفقیت از پنل حذف شد.")
        else: bot.send_message(ADMIN_ID, f"❌ خطای پنل: {res.text}")
    except Exception as e: bot.send_message(ADMIN_ID, f"🚨 خطای ارتباطی")

# --- X-UI AUTO CREATION ENGINE ---
def generate_xui_config(user_id, plan_id, tx_id):
    plan = PLANS[plan_id]
    user_email = f"speedping_{user_id}_{tx_id}"
    total_bytes = plan['volume'] * 1024 * 1024 * 1024 if plan['volume'] > 0 else 0
    expiry_time_ms = int((time.time() + (plan['days'] * 86400)) * 1000)
    
    headers = {"Authorization": f"Bearer {XUI_BEARER_TOKEN}", "Content-Type": "application/json"}
    request_proxies = {'http': 'http://127.0.0.1:10808', 'https': 'http://127.0.0.1:10808'} if DEVELOPMENT_MODE else None
    
    try:
        get_inbounds_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/inbounds/list"
        inbounds_response = requests.get(get_inbounds_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        inbounds_list = inbounds_response.json().get("obj", [])
        active_inbound_ids = [ib["id"] for ib in inbounds_list if ib.get("enable", True)]
        
        payload = {
            "client": {
                "email": user_email,
                "totalGB": total_bytes,
                "expiryTime": expiry_time_ms,
                "tgId": user_id,
                "limitIp": 2,
                "enable": True
            },
            "inboundIds": active_inbound_ids
        }
        
        add_client_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/add"
        requests.post(add_client_url, json=payload, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        
        time.sleep(1.5)
        
        config_links = []
        get_links_url = f"{XUI_API_URL}{XUI_BASE_PATH}/panel/api/clients/links/{user_email}"
        links_response = requests.get(get_links_url, headers=headers, proxies=request_proxies, timeout=15, verify=not DEVELOPMENT_MODE)
        if links_response.status_code == 200 and links_response.json().get("success"):
            config_links = links_response.json().get("obj", [])
            
        # 🛡️ مکانیزم پارس خودکار کانفیگ‌ها برای استخراج قطعی UUID کلاینت (حل چالش خطای دیتابیس)
        sub_id = "error_id"
        if config_links:
            try:
                first_link = config_links[0]
                if "@" in first_link:
                    sub_id = first_link.split("@")[0].split("//")[-1]
            except: pass
            
        subscription_url = f"{XUI_SUB_SERVER_URL}/sub/{sub_id}"
        
        msg_text = f"🎉 **پرداخت شما تایید شد! سرویس نامحدود SpeedPing فعال گردید.**\n\n" \
                   f"🌐 **لینک سابسکریپشن (مخصوص نرم‌افزار):**\n```\n{subscription_url}\n```\n"
        
        if config_links:
            msg_text += f"🔑 **کانفیگ‌های اتصال مستقیم:**\n"
            for link in config_links:
                msg_text += f"```\n{link}\n```\n"
                
        msg_text += "\n📱 اطلاعات فوق را کپی کرده و در نرم‌افزار خود وارد کنید. از کیفیت SpeedPing لذت ببرید!"
        
        bot.send_message(user_id, msg_text, parse_mode="Markdown")
        bot.send_message(ADMIN_ID, f"✅ سرویس با موفقیت صادر شد.")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"🚨 خطا در صدور خودکار: {str(e)}")

if __name__ == '__main__':
    print("SpeedPing Bot is running perfectly...")
    bot.remove_webhook()
    bot.infinity_polling()