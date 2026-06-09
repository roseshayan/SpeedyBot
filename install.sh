#!/bin/bash

# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then
  echo "❌ لطفاً این اسکریپت را با دسترسی روت (root) اجرا کنید."
  exit
fi

echo "🚀 به نصب‌کننده خودکار ربات فروش کلاینت X-UI (سنائی v3.3.0) خوش آمدید"
echo "------------------------------------------------------------------"

# دریافت اطلاعات از کاربر
read -p "🎯 توکن ربات تلگرام را وارد کنید: " BOT_TOKEN
read -p "👤 آیدی عددی ادمین تلگرام را وارد کنید: " ADMIN_ID
read -p "🌐 آدرس کامل وب پنل (مثال: http://127.0.0.1:2053): " XUI_API_URL
read -p "🔐 بیس‌پث امنیتی پنل (مثال: /pKPl2UQ2sKTDnSWXb0 یا اگر ندارید کاراکتر /): " XUI_BASE_PATH
read -p "🔑 توکن Bearer ادمین پنل (از تنظیمات امنیت پنل): " XUI_BEARER_TOKEN
read -p "🛰 آدرس کامل سابسکریپشن همراه پورت (مثال: https://sub.domain.com:2096): " XUI_SUB_SERVER_URL

echo "📦 در حال نصب پکیج‌های سیستم..."
apt update && apt install python3 python3-pip python3-venv -y

echo "📂 در حال آماده‌سازی دایرکتوری /root/xui-shop-bot ..."
mkdir -p /root/xui-shop-bot
cp main.py /root/xui-shop-bot/main.py
cd /root/xui-shop-bot

echo "🌐 در حال ساخت محیط مجازی پایتون..."
python3 -m venv .venv
./.venv/bin/pip install pyTelegramBotAPI requests

echo "⚙️ در حال ساخت و پیکربندی سرویس سیستمی لینوکس..."
cat << SERVICE_EOF > /etc/systemd/system/xui-bot.service
[Unit]
Description=X-UI Telegram Shop Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/xui-shop-bot
ExecStart=/root/xui-shop-bot/.venv/bin/python3 /root/xui-shop-bot/main.py
Restart=always
RestartSec=5
Environment=BOT_TOKEN=$BOT_TOKEN
Environment=ADMIN_ID=$ADMIN_ID
Environment=XUI_API_URL=$XUI_API_URL
Environment=XUI_BASE_PATH=$XUI_BASE_PATH
Environment=XUI_BEARER_TOKEN=$XUI_BEARER_TOKEN
Environment=XUI_SUB_SERVER_URL=$XUI_SUB_SERVER_URL

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "🔄 در حال استارت سرویس ربات..."
systemctl daemon-reload
systemctl enable xui-bot.service
systemctl start xui-bot.service

echo "------------------------------------------------------------------"
echo "🎉 ربات با موفقیت نصب شد و هم‌اکنون در پس‌زمینه سرور فعال است!"
echo "💡 وضعیت سرویس: $(systemctl is-active xui-bot.service)"
echo "------------------------------------------------------------------"