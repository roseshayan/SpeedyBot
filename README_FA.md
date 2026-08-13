# SpeedyBot v3.0.0

> ربات تلگرام فروش و مدیریت سرویس برای **3x-ui / Sanaei**
>
> **سازنده:** [SudoShayanNA](https://github.com/roseshayan) · [Telegram](https://t.me/SudoShayanNA) · `namayandeshayan@gmail.com`

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](VERSION.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420.svg)](https://ubuntu.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English documentation](README.md)

---

## معرفی

SpeedyBot برای اتصال Telegram به پنل **3x-ui / Sanaei** ساخته شده و کارهای اصلی فروش و مدیریت سرویس را خودکار می‌کند. اطلاعات کاربران و تراکنش‌ها در SQLite ذخیره می‌شود، ارتباط با پنل از API رسمی `/panel/api/*` و Bearer Token انجام می‌شود و ربات روی Ubuntu به‌صورت systemd service اجرا می‌شود.

پرداخت نسخه عمومی فعلی بر پایه **کارت‌به‌کارت با ارسال فیش و تأیید ادمین + کیف پول** است.

## امکانات

- ساخت خودکار Client روی Inboundهای فعال پنل.
- تست رایگان ۱ گیگابایت / ۱ روز، فقط یک بار برای هر Telegram ID.
- مدیریت داینامیک پلن‌ها از `/sudoadmin`.
- تنظیم `limitIp` مطابق تعداد کاربر انتخابی.
- سه پلن اولیه:
  - ۱ کاربر، ۳۰ روز نامحدود، ۲۵۰٬۰۰۰ تومان، `limitIp=1`
  - ۲ کاربر، ۳۰ روز نامحدود، ۳۰۰٬۰۰۰ تومان، `limitIp=2`
  - ۳ کاربر، ۳۰ روز نامحدود، ۳۵۰٬۰۰۰ تومان، `limitIp=3`
- تمدید همان Client و حفظ Subscription فعلی.
- بسته حجم اضافه برای پلن‌های حجمی.
- Subscription Link، لینک‌های کانفیگ و QR Code.
- سرویس پولی در Group `Customers` و تست در Group `Trial`.
- ساخت و Reconcile گروه‌های لازم در Sanaei.
- حساب کاربری، تاریخچه خرید و وضعیت سرویس.
- کیف پول و تاریخچه تراکنش‌ها.
- Affiliate / Referral یک‌سطحی.
- Cashback، Discount Code و Gift Code.
- احراز شماره موبایل اختیاری.
- عضویت اجباری کانال به‌صورت اختیاری.
- چند ادمین.
- FAQ و Welcome قابل ویرایش.
- بکاپ دستی و خودکار SQLite.
- هشدار نزدیک اتمام حجم/زمان و اعلان پایان سرویس.
- Updater مستقیم GitHub همراه با Backup، Health Check و Rollback.

---

# پیش‌نیازها

برای نصب پیشنهاد می‌شود داشته باشی:

- Ubuntu 24.04 LTS
- دسترسی `root`
- Python 3.10 یا جدیدتر
- پنل 3x-ui / Sanaei با API جدید
- Telegram Bot Token
- Telegram Numeric ID ادمین اصلی
- Bearer API Token پنل
- آدرس Subscription Server

ربات و پنل می‌توانند روی یک سرور یا دو سرور جدا باشند؛ فقط سرور ربات باید بتواند به API پنل متصل شود.

---

# آماده‌سازی قبل از نصب

## ۱. ساخت Telegram Bot

داخل Telegram به `@BotFather` برو:

```text
/newbot
```

نام و Username ربات را انتخاب کن و Token را ذخیره کن.

نمونه فرمت Token:

```text
123456789:AAExampleTelegramBotToken
```

Token واقعی را داخل GitHub، Issue، Screenshot یا پیام عمومی منتشر نکن.

## ۲. پیدا کردن Telegram ID

Numeric ID اکانت اصلی خودت را پیدا کن. این عدد در Installer به‌عنوان `ADMIN_ID` استفاده می‌شود.

نمونه:

```text
123456789
```

Username مثل `@username` قابل استفاده نیست.

## ۳. ساخت API Token در Sanaei

داخل پنل:

```text
Settings → Security → API Token
```

Token جدید بساز و مقدار **plaintext** آن را همان لحظه ذخیره کن.

مهم: نام Token، رمز پنل و Web Base Path جای API Token قابل استفاده نیستند.

## ۴. مشخص کردن API URL و Base Path

اگر URL پنل این باشد:

```text
https://panel.example.com:2053/my-secret-path/
```

مقادیر Installer باید این باشند:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /my-secret-path
```

اگر Base Path نداری:

```text
/
```

## ۵. مشخص کردن Subscription

اگر لینک Subscription نهایی به شکل زیر است:

```text
https://sub.example.com:2096/sub/XXXXXXXX
```

مقادیر Installer:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

اگر URI را در پنل عوض کرده‌ای همان مقدار جدید را وارد کن.

---

# نصب مرحله‌به‌مرحله

وارد Ubuntu شو:

```bash
ssh root@SERVER_IP
```

Git را نصب کن:

```bash
apt update
apt install -y git
```

پروژه را دریافت کن:

```bash
git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

Installer این موارد را می‌پرسد:

1. Telegram Bot Token
2. Telegram Admin Numeric ID
3. X-UI API Base URL
4. X-UI Security Base Path
5. Panel Bearer API Token
6. Subscription Server Base URL
7. Subscription URI Path

سپس Python environment، وابستگی‌ها، `.env` و systemd service را می‌سازد و قبل از پایان، API پنل را به‌صورت Read-only تست می‌کند.

نام سرویس:

```text
xui-bot.service
```

---

# معنی سؤال‌های Installer

### Telegram bot token
Token دقیق BotFather.

### Telegram admin numeric ID
Numeric ID مالک ربات، نه Username.

### X-UI API base URL
درست:

```text
https://panel.example.com:2053
```

Path را اینجا اضافه نکن.

### X-UI security base path
مثلاً:

```text
/secret-path
```

یا اگر نداری:

```text
/
```

### Panel Bearer API Token
مقدار plaintext API Token پنل.

### Subscription server base URL
مثلاً:

```text
https://sub.example.com:2096
```

### Subscription URI path
معمولاً:

```text
/sub/
```

---

# اولین تست بعد از نصب

وضعیت سرویس:

```bash
systemctl status xui-bot.service --no-pager -l
```

باید ببینی:

```text
Active: active (running)
```

لاگ زنده:

```bash
journalctl -u xui-bot.service -f
```

داخل Telegram:

```text
/start
```

و از اکانت Owner:

```text
/xuidiag
/groupsdiag
/notifydiag
/sudoadmin
```

پیشنهاد می‌شود قبل از فروش واقعی:

- مشخصات کارت/بانک را تنظیم کنی.
- پلن‌ها را بازبینی کنی.
- درصد Referral و Cashback را چک کنی.
- یک خرید تستی انجام بدهی.
- Free Trial را با یک اکانت دیگر تست کنی.

---

# دستورات اصلی ادمین

| دستور | کاربرد |
|---|---|
| `/sudoadmin` | پنل اصلی مدیریت |
| `/xuidiag` | تست اتصال و Authentication پنل |
| `/groupsdiag` | نمایش Groupهای Sanaei و تعداد اعضا |
| `/notifydiag` | تست مانیتور سرویس |

بیشتر تنظیمات از دکمه‌های داخل `/sudoadmin` انجام می‌شوند.

---

# Groups در Sanaei

SpeedyBot برای نظم پنل از دو Group اصلی استفاده می‌کند:

```text
Customers
Trial
```

- خرید موفق → `Customers`
- تست رایگان → `Trial`

اگر Group لازم وجود نداشته باشد، ربات می‌تواند آن را ایجاد کند. برای دیدن Groupهای واقعی پنل خودت:

```text
/groupsdiag
```

---

# تمدید سرویس

کاربر از حساب کاربری می‌تواند همان سرویس فعلی را تمدید کند. تمدید می‌تواند تاریخ انقضا، حجم و `limitIp` را مطابق پلن جدید تغییر دهد و لازم نیست برای هر تمدید یک Subscription بی‌ربط جدید ایجاد شود.

اگر کاربر قبل از پایان زمان فعلی تمدید کند، سیستم برای حفظ اعتبار باقی‌مانده طراحی شده است.

---

# کیف پول و بازاریابی

## Wallet
تمام افزایش/کاهش‌های موجودی در Ledger ذخیره می‌شود و ادمین می‌تواند موجودی کاربر را مدیریت کند.

## Referral
هر کاربر می‌تواند لینک دعوت اختصاصی بگیرد. Self-referral رد می‌شود و پورسانت واجد شرایط بعد از خرید موفق فقط یک‌بار ثبت می‌شود.

## Cashback
از پنل ادمین قابل فعال‌سازی و تنظیم است.

## Discount Code
کد تخفیف درصدی یا مبلغ ثابت با محدودیت‌هایی مثل تاریخ انقضا، حداقل خرید و تعداد مصرف.

## Gift Code
برای شارژ کیف پول کاربران.

---

# اعلان سرویس

مانیتور به‌صورت دوره‌ای سرویس‌ها را بررسی می‌کند. پیش‌فرض‌های معمول:

- هشدار در ۹۰٪ مصرف حجم.
- هشدار ۲۴ ساعت مانده به پایان سرویس پولی.
- هشدار ۳ ساعت مانده به پایان تست.
- اعلان اتمام حجم.
- اعلان اتمام زمان.

اعلان‌های ارسال‌شده ثبت می‌شوند تا با Restart تکرار نشوند.

---

# تنظیمات و `.env`

Secretها در این فایل ذخیره می‌شوند:

```text
/root/SpeedyBot/.env
```

نمونه امن در [.env.example](.env.example) قرار دارد.

متغیرهای اصلی:

```bash
BOT_TOKEN='...'
ADMIN_ID='123456789'
XUI_API_URL='https://panel.example.com:2053'
XUI_BASE_PATH='/secret-path'
XUI_BEARER_TOKEN='...'
XUI_SUB_SERVER_URL='https://sub.example.com:2096'
XUI_SUB_PATH='/sub/'
```

بعد از تغییر دستی `.env`:

```bash
systemctl restart xui-bot.service
```

---

# آپدیت مستقیم از GitHub

فقط بررسی آخرین نسخه:

```bash
cd /root/SpeedyBot
./update.sh --check
```

آپدیت:

```bash
./update.sh
```

Deploy اجباری آخرین Commit:

```bash
./update.sh --force
```

Updater قبل از Deploy فایل‌ها را Validate می‌کند، از `.env`، دیتابیس و سورس فعلی Backup می‌گیرد، سرویس را Restart و Health Check می‌کند و در صورت شکست Rollback انجام می‌دهد.

---

# بکاپ

فایل‌های مهم:

```text
/root/SpeedyBot/speedping.db
/root/SpeedyBot/.env
/root/SpeedyBot/backups/
```

برای بکاپ دستی:

```bash
systemctl stop xui-bot.service
cp -a /root/SpeedyBot/speedping.db /root/speedping.db.backup
cp -a /root/SpeedyBot/.env /root/speedybot.env.backup
systemctl start xui-bot.service
```

بکاپ‌ها را عمومی نکن.

---

# دستورات کاربردی سرور

وضعیت:

```bash
systemctl status xui-bot.service --no-pager -l
```

لاگ زنده:

```bash
journalctl -u xui-bot.service -f
```

آخرین 150 خط:

```bash
journalctl -u xui-bot.service -n 150 --no-pager
```

Restart:

```bash
systemctl restart xui-bot.service
```

ویرایش `.env`:

```bash
nano /root/SpeedyBot/.env
```

---

# عیب‌یابی

## ربات جواب نمی‌دهد

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

موارد رایج: Token تلگرام اشتباه، اجرای همزمان دو Bot Process، خطای Runtime یا مشکل شبکه.

## خطای 401 / 403 از 3x-ui

Bearer Token را بررسی کن. باید **مقدار plaintext API Token** باشد، نه اسم Token، رمز پنل یا Base Path.

```text
/xuidiag
```

## خطای 404

`XUI_BASE_PATH`، نسخه پنل و Reverse Proxy را بررسی کن.

تقسیم درست:

```text
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

## Subscription کار نمی‌کند

Subscription Server، Port، Domain/TLS، `XUI_SUB_SERVER_URL` و `XUI_SUB_PATH` را بررسی کن.

## Group assignment مشکل دارد

```text
/groupsdiag
/xuidiag
```

را اجرا کن.

---

# امنیت

حتماً [SECURITY.md](SECURITY.md) را بخوان.

- `.env` را Commit نکن.
- Bot Token و API Token را عمومی نکن.
- اگر Secret لو رفت، فوراً Rotate کن.
- از HTTPS برای Endpointهای عمومی استفاده کن.
- Backupها را داخل Web Root قرار نده.
- Subscription Link و QR را مثل رمز عبور نگه دار.
- فقط روی زیرساختی استفاده کن که مالک آن هستی یا اجازه مدیریت آن را داری.

---

# ساختار پروژه

```text
SpeedyBot/
├── main.py
├── install.sh
├── update.sh
├── requirements.txt
├── VERSION.txt
├── .env.example
├── README.md
├── README_FA.md
├── CHANGELOG.md
├── MIGRATION_NOTES.md
├── SECURITY.md
├── CONTRIBUTING.md
├── AUTHOR.md
├── CITATION.cff
└── LICENSE
```

فایل‌های Runtime مثل `.env`، `speedping.db`، `.venv/` و `backups/` نباید داخل GitHub Commit شوند.

---

# مشارکت

Bug Report و Pull Request خوش‌آمد است. ابتدا [CONTRIBUTING.md](CONTRIBUTING.md) را بخوان.

قبل از ارسال Log یا Screenshot حتماً Tokenها، اطلاعات کاربران و Subscription URLها را حذف کن.

---

# سازنده

**SpeedyBot توسط SudoShayanNA ساخته و نگهداری می‌شود.**

- GitHub: [github.com/roseshayan](https://github.com/roseshayan)
- Repository: [github.com/roseshayan/SpeedyBot](https://github.com/roseshayan/SpeedyBot)
- Telegram: [@SudoShayanNA](https://t.me/SudoShayanNA)
- Email: `namayandeshayan@gmail.com`

هنگام Fork یا انتشار نسخه مشتق‌شده، Attribution سازنده و Noticeهای Copyright/License را حفظ کن.

---

# لایسنس

پروژه تحت [MIT License](LICENSE) منتشر می‌شود.

Copyright © 2026 **SudoShayanNA**.

> **SpeedyBot · SudoShayanNA** — GitHub: `roseshayan/SpeedyBot` · Telegram: `@SudoShayanNA` · Email: `namayandeshayan@gmail.com`
