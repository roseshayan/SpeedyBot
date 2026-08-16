# SpeedyBot v4.0.0

<p align="center">
  <strong>ربات متن‌باز فروش، مدیریت اشتراک و CRM تلگرامی برای پنل 3x-ui / Sanaei</strong><br>
  فروش خودکار • تست رایگان • تمدید • کیف پول • همکاری در فروش • مدیریت Inbound • CRM • راهنمای اتصال • Control Center
</p>

<p align="center">
  <a href="README.md">🇬🇧 English README</a> ·
  <a href="CHANGELOG.md">تغییرات نسخه‌ها</a> ·
  <a href="MIGRATION_NOTES.md">راهنمای مهاجرت</a> ·
  <a href="SECURITY.md">امنیت</a> ·
  <a href="CONTRIBUTING.md">مشارکت</a>
</p>

> **سازنده و نگهدارنده پروژه: SudoShayanNA**  
> Telegram: **@SudoShayanNA** · Email: **namayandeshayan@gmail.com**  
> Official repository: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot یک ربات تلگرام عملی برای فروش و مدیریت سرویس‌های **3x-ui / Sanaei** است. ربات می‌تواند بعد از تأیید پرداخت Client بسازد، تست رایگان بدهد، پلان‌ها را مدیریت کند، سرویس را تمدید کند، لینک Subscription و کانفیگ مستقیم تحویل دهد، QR بسازد، کیف پول و Referral داشته باشد، نزدیک اتمام سرویس هشدار بدهد و بسیاری از عملیات فروش و پشتیبانی را از داخل تلگرام انجام دهد.

نسخه v4 علاوه بر امکانات v3.1 یک **Control Center** مرتب‌تر، دسته‌بندی پلان‌ها، Blacklist، حالت تعمیرات/توقف فروش، Trial اختصاصی، Feedback مشتری، Broadcast هدفمند، Audit Log، Snapshot اضطراری پنل و پشتیبانی از Styleهای جدید دکمه‌های تلگرام و Custom/Premium Emoji را اضافه می‌کند.

هسته پایدار قبلی در `main.py` باقی مانده و نسخه v4 از `app.py` و ماژول‌های `speedybot_v4/` استفاده می‌کند. Runtime اصلی روی Ubuntu با `systemd` اجرا می‌شود و داده‌های کسب‌وکار در SQLite ذخیره می‌شوند.

---

## فهرست

- [امکانات](#امکانات)
- [قابلیت‌های جدید v4](#قابلیتهای-جدید-v4)
- [پلان‌های پیش‌فرض](#پلانهای-پیشفرض)
- [پیش‌نیازها](#پیشنیازها)
- [قبل از نصب](#قبل-از-نصب)
- [ساخت Bot تلگرام](#۱-ساخت-ربات-تلگرام)
- [پیدا کردن Telegram ID](#۲-telegram-id-ادمین)
- [ساخت Bearer Token در 3x-ui](#۳-ساخت-api-token-در-3x-ui)
- [Base URL و Base Path](#۴-تفاوت-base-url-و-base-path)
- [Subscription](#۵-subscription)
- [نصب مرحله‌به‌مرحله](#نصب-مرحلهای)
- [کارهای ضروری بعد از نصب](#کارهای-ضروری-بعد-از-نصب)
- [پنل مدیریت](#پنل-مدیریت)
- [حالت‌های عملیاتی](#حالتهای-عملیاتی)
- [دسته‌بندی پلان‌ها](#دستهبندی-پلانها)
- [تست رایگان و Inbound](#تست-رایگان-و-انتخاب-inbound)
- [Trial اختصاصی](#تست-اختصاصی-برای-یک-کاربر)
- [راهنمای اتصال](#راهنمای-اتصال-کاربران)
- [CRM و Follow-up](#crm-و-پیگیری-بعد-از-تست)
- [نام دلخواه و سرویس قدیمی](#نام-دلخواه-و-سرویس-قدیمی)
- [پرداخت، کیف پول و بازاریابی](#پرداخت-و-بازاریابی)
- [تمدید](#تمدید)
- [Groups](#groups)
- [Feedback](#سیستم-نظر-و-امتیاز)
- [Broadcast هدفمند](#ارسال-پیام-هدفمند)
- [Audit Log](#audit-log)
- [Snapshot پنل](#snapshot-اضطراری-پنل)
- [رنگ دکمه و Premium Emoji](#رنگ-دکمهها-و-premium-emoji)
- [اعلان‌ها](#اعلانها)
- [دستورات تشخیصی](#دستورات-تشخیصی)
- [آپدیت](#آپدیت)
- [مهاجرت از v3.x به v4](#مهاجرت-از-v3x-به-v4)
- [بکاپ و Rollback](#بکاپ-و-rollback)
- [عیب‌یابی](#عیبیابی)
- [امنیت](#امنیت)
- [ساختار فایل‌ها](#ساختار-فایلها)
- [سازنده و لایسنس](#سازنده-و-لایسنس)

---

## امکانات

### فروش و ساخت خودکار سرویس

- ساخت Client در 3x-ui بعد از تأیید پرداخت.
- تست رایگان پیش‌فرض: **1 GB / 1 day / 1 IP**.
- پلان‌های داینامیک داخل SQLite.
- `limitIp` مستقل برای هر پلان.
- پرداخت کارت‌به‌کارت/ارسال رسید و تأیید ادمین.
- خرید مستقیم از کیف پول.
- Retry و Idempotency برای جلوگیری از Client تکراری در خطا یا Restart.
- لینک Subscription.
- کانفیگ مستقیم واقعی.
- QR سابسکریپشن.
- تمدید همان Client با حفظ هویت و Subscription.
- بسته حجم اضافه برای پلان‌های حجمی.

### انتخاب Inbound برای Trial و هر Plan

می‌توانید تعیین کنید:

- Trial روی کدام Inboundها ساخته شود.
- Plan ID 1 روی کدام Inboundها باشد.
- Plan ID 2 روی کدام Inboundها باشد.
- هر پلان جدید روی چه Inboundهایی قرار بگیرد.

اگر برای یک Scope انتخابی ذخیره نشده باشد، ربات برای سازگاری با نسخه‌های قبلی از **تمام Inboundهای فعال** استفاده می‌کند.

در Retry نیز اگر Client از قبل وجود داشته باشد Inboundهای آن با تنظیم فعلی Sync می‌شوند. هنگام Renewal نیز Inboundهای پلان جدید روی همان Client اعمال می‌شوند.

### امکانات کاربر

- حساب کاربری.
- مشاهده وضعیت زنده سرویس.
- مشاهده حجم و زمان باقی‌مانده.
- دریافت Subscription.
- دریافت کانفیگ‌های مستقیم.
- QR.
- تمدید.
- خرید حجم اضافه برای پلان‌های حجمی.
- تاریخچه خرید/تمدید/حجم.
- Wallet و تاریخچه Wallet.
- کد هدیه و تخفیف.
- Referral/Affiliate.
- راهنمای اتصال بر اساس Platform.
- افزودن سرویس خریداری‌شده قبلی.
- نام دلخواه هنگام خرید.
- ثبت Feedback و امتیاز.
- احراز شماره اختیاری.
- عضویت اجباری کانال اختیاری.

### بازاریابی و CRM

- Referral یک‌سطحی.
- Cashback قابل تنظیم.
- Discount Code درصدی یا مبلغ ثابت.
- Gift Code برای Wallet.
- پرسش «از کجا با ما آشنا شدید؟» بعد از اولین خرید موفق.
- Follow-up خودکار بعد از پایان Trial.
- ثبت علت نخریدن.
- CTA خرید و پشتیبانی.
- Broadcast هدفمند برای Segmentهای مختلف.
- Feedback و رضایت مشتری.

---

## قابلیت‌های جدید v4

### Control Center جدید

`/sudoadmin` در v4 مرتب‌تر شده تا متن‌ها کوتاه‌تر، بخش‌ها دسته‌بندی‌شده‌تر و عملیات مهم سریع‌تر در دسترس باشند.

### حالت‌های عملیاتی

- `NORMAL` — همه‌چیز فعال.
- `SALES_PAUSED` — خرید جدید، تمدید و حجم اضافه متوقف؛ حساب، راهنما و پشتیبانی فعال.
- `MAINTENANCE` — خرید و Trial جدید متوقف؛ حساب، راهنما و پشتیبانی فعال.

### Blacklist

ادمین می‌تواند خرید/Trial یک کاربر را همراه دلیل محدود کند و بعداً Unblock کند. این محدودیت کاربر را از دسترسی به Support محروم نمی‌کند.

### دسته‌بندی پلان‌ها

پلان‌ها می‌توانند در Categoryهایی مثل Gaming، Germany، Static IP یا Business مرتب شوند.

### Trial اختصاصی

برای یک Telegram ID مشخص می‌توانید قبل از اولین Trial حجم، روز و IP Limit متفاوت تعریف کنید.

### Feedback

امتیاز 1 تا 5 ستاره + Comment اختیاری + میانگین و توزیع امتیاز در Admin.

### Broadcast هدفمند

ارسال پیام فقط به یک Audience خاص مثل Customers، Trial Leads، Expired Trial یا Never Bought.

### Audit Log

رویدادهای مدیریتی مهم داخل SQLite ثبت می‌شوند و می‌توان آنها را به یک Channel/Group خصوصی Telegram هم ارسال کرد.

### Panel Snapshot

Export خواندنی از Clientهای 3x-ui برای Disaster Recovery. Snapshot عمداً Read-only است و Restore مخرب یک‌کلیکی ندارد.

### Style دکمه و Custom Emoji

از Styleهای رسمی Telegram مثل `primary`, `success`, `danger` استفاده می‌شود. رنگ HEX/RGB آزاد توسط Telegram Bot API در اختیار Bot نیست.

Custom/Premium Emoji روی دکمه‌ها اختیاری است و اگر Telegram اجازه ندهد ربات باید با Emoji معمولی کار کند.

---

## پلان‌های پیش‌فرض

در دیتابیس تازه:

| پلان | مدت | حجم | IP Limit | قیمت پیش‌فرض |
|---|---:|---:|---:|---:|
| نامحدود 1 کاربر | 30 روز | نامحدود | 1 | 250,000 تومان |
| نامحدود 2 کاربر | 30 روز | نامحدود | 2 | 300,000 تومان |
| نامحدود 3 کاربر | 30 روز | نامحدود | 3 | 350,000 تومان |

این‌ها فقط Seed اولیه‌اند. قبل از فروش واقعی قیمت‌ها را از `/sudoadmin` مطابق کسب‌وکار خودتان تغییر دهید.

---

## پیش‌نیازها

پیشنهاد Production:

- Ubuntu **24.04 LTS**
- Python 3.12
- 3x-ui/Sanaei به‌روز با API `/panel/api/*`
- Bearer API Token پنل
- Telegram Bot Token
- Telegram numeric ID مالک
- Subscription Server در صورت استفاده از لینک Subscription
- دسترسی خروجی VPS به Telegram و پنل

ربات با Long Polling کار می‌کند و برای Telegram نیازی به Webhook Port ندارد.

---

## قبل از نصب

### ۱) ساخت ربات تلگرام

داخل `@BotFather`:

1. `/newbot` را ارسال کنید.
2. Display Name انتخاب کنید.
3. Username تمام‌شونده به `bot` انتخاب کنید.
4. Token را کپی و امن نگه دارید.

Token را هرگز داخل Issue، README، Screenshot یا Commit عمومی نگذارید.

### ۲) Telegram ID ادمین

Telegram ID عددی حسابی که قرار است Owner باشد پیدا کنید. این مقدار `ADMIN_ID` است.

`ADMIN_ID` با Username تلگرام فرق دارد. مقدار باید فقط عدد باشد.

### ۳) ساخت API Token در 3x-ui

در پنل:

```text
Settings → Security → API Token
```

یک Token بسازید و **plaintext token value** را همان لحظه ذخیره کنید.

موارد زیر Bearer Token نیستند:

- اسم Token
- رمز ورود پنل
- Base Path مخفی پنل

### ۴) تفاوت Base URL و Base Path

اگر پنل با این آدرس باز می‌شود:

```text
https://panel.example.com:2053/secret-panel/
```

در Installer:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

اگر مسیر مخفی ندارید:

```text
X-UI security base path: /
```

**Base Path را داخل API Base URL تکرار نکنید.**

### ۵) Subscription

اگر لینک واقعی کاربر به‌شکل زیر است:

```text
https://sub.example.com:2096/sub/ABC123
```

مقادیر Installer:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

اگر 3x-ui شما Subscription Path دیگری دارد همان مقدار را وارد کنید.

---

## نصب مرحله‌ای

با root وارد Ubuntu شوید:

```bash
apt update
apt install -y git

git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

Installer به‌ترتیب می‌پرسد:

1. Telegram Bot Token
2. Telegram Admin numeric ID
3. X-UI API base URL
4. X-UI security base path
5. Panel Bearer API Token
6. Subscription server base URL
7. Subscription URI path

قبل از راه‌اندازی systemd، Installer یک تست **Read-only** روی API پنل می‌زند تا Token/Base Path اشتباه همان ابتدا مشخص شود.

### فایل‌های Runtime

```text
/root/SpeedyBot/.env
/root/SpeedyBot/.venv/
/root/SpeedyBot/speedping.db
/root/SpeedyBot/run.sh
/root/SpeedyBot/backups/
/etc/systemd/system/xui-bot.service
```

در v4، `run.sh` اگر `app.py` موجود باشد آن را اجرا می‌کند و برای نسخه‌های قدیمی fallback به `main.py` دارد.

### وضعیت سرویس

```bash
systemctl status xui-bot.service --no-pager -l
```

### لاگ زنده

```bash
journalctl -u xui-bot.service -f
```

### 150 خط آخر لاگ

```bash
journalctl -u xui-bot.service -n 150 --no-pager
```

### Restart

```bash
systemctl restart xui-bot.service
```

### Stop / Start

```bash
systemctl stop xui-bot.service
systemctl start xui-bot.service
```

---

## کارهای ضروری بعد از نصب

از حساب Owner:

```text
/start
/sudoadmin
```

قبل از فروش واقعی:

1. اطلاعات کارت/بانک پیش‌فرض را عوض کنید.
2. پلان‌ها، قیمت، Days، Volume و IP Limit را بررسی کنید.
3. Categoryهای پلان را تنظیم کنید.
4. وارد **Trial & Inbounds** شوید.
5. Trial را روشن/خاموش کنید.
6. برای Trial و هر Plan Inbound انتخاب کنید.
7. Groupهای `Customers` و `Trial` را بررسی/همگام کنید.
8. راهنمای اتصال Android/iOS/Windows/macOS/Linux/TV را بسازید.
9. CRM و Trial Follow-up را بررسی کنید.
10. Phone Verification/Channel Membership را در صورت نیاز تنظیم کنید.
11. Operating Mode را روی `NORMAL` بگذارید.
12. ظاهر/Style دکمه‌ها را بررسی کنید.
13. در صورت استفاده از Audit Channel، Chat ID را تنظیم و تست کنید.
14. `/xuidiag` را اجرا کنید.
15. `/groupsdiag` را اجرا کنید.
16. `/notifydiag` را اجرا کنید.
17. یک Trial واقعی بگیرید.
18. یک خرید کوچک واقعی/آزمایشی را از ابتدا تا صدور Client بررسی کنید.

---

## پنل مدیریت

دستور:

```text
/sudoadmin
```

بخش‌های اصلی شامل:

- آمار فروش
- مدیریت Plan
- Plan Categories
- Volume Packs
- Trial و Inbounds
- Trial Override
- Sanaei Groups
- CRM و Follow-up
- Feedback
- Targeted Broadcast
- Wallet
- Referral
- Cashback
- Gift / Discount
- Blacklist
- Operating Mode
- Verification / Membership
- Multiple Admins
- Notifications
- Backup
- Panel Snapshot
- Audit Log
- UI / Button Style / Premium Emoji
- Payment information
- Welcome / FAQ

---

## حالت‌های عملیاتی

### 🟢 Normal

تمام قابلیت‌ها فعال هستند.

### 🟠 Sales Paused

خرید، تمدید و Volume Add-on متوقف می‌شوند.

کاربر همچنان می‌تواند:

- حساب را ببیند.
- سرویس را مشاهده کند.
- راهنما را باز کند.
- با پشتیبانی ارتباط بگیرد.

### 🔴 Maintenance

خرید و Trial جدید متوقف می‌شوند. Account، Guide و Support باقی می‌مانند.

این روش بهتر از خاموش‌کردن کل Bot است چون مشتری موجود در زمان Maintenance بدون پشتیبانی نمی‌ماند.

---

## دسته‌بندی پلان‌ها

مسیر:

```text
/sudoadmin → Plan Categories
```

مثال:

```text
🇩🇪 Germany
🎮 Gaming
🌐 Anti-Sanction
📌 Static IP
🏢 Business
```

پلان‌های قدیمی بعد از Migration به Category پیش‌فرض `عمومی` متصل می‌شوند.

---

## تست رایگان و انتخاب Inbound

مسیر:

```text
/sudoadmin → Trial & Inbounds
```

امکانات:

- روشن/خاموش Trial.
- انتخاب Inboundهای Trial.
- انتخاب Inbound مستقل برای هر Plan.
- Reset روی همه Inboundهای فعال.

### Direct Config و Subscription

این دو یکی نیستند.

Direct Config فقط Schemeهای واقعی Proxy را می‌پذیرد:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

URLهای `http://` و `https://` به‌عنوان Direct Config نمایش داده نمی‌شوند و Subscription در بخش جدا تحویل می‌شود.

اگر Direct Address اشتباه است خروجی Bot را با **Copy URL** همان Client در 3x-ui مقایسه کنید. اگر هر دو اشتباه‌اند، Share Address/Public Host مربوط به Inbound را در پنل اصلاح کنید.

---

## تست اختصاصی برای یک کاربر

برای یک کاربر خاص می‌توانید قبل از اولین Trial Override بگذارید:

```text
TelegramID | VolumeGB | Days | IPLimit | Optional note
```

مثال:

```text
123456789 | 5 | 3 | 2 | VIP lead
```

کاربرانی که Override ندارند همان Trial عمومی را می‌گیرند. Inboundها همچنان از تنظیم Trial اصلی استفاده می‌شوند.

---

## راهنمای اتصال کاربران

مسیر:

```text
/sudoadmin → Connection Guides
```

Platformهای آماده:

- Android
- iPhone / iOS
- Windows
- macOS
- Linux
- Android TV / TV Box

برای هر Platform می‌توانید چند Item بسازید:

- Text
- Photo + Caption
- Video + Caption
- Preview
- Sort/Reorder

ربات `file_id` تلگرام را نگه می‌دارد و Binary فایل را داخل SQLite ذخیره نمی‌کند.

بعد از Trial یا Purchase موفق، CTA راهنما برای کاربر نمایش داده می‌شود.

---

## CRM و پیگیری بعد از تست

مسیر:

```text
/sudoadmin → CRM
```

### از کجا با ما آشنا شدید؟

بعد از اولین خرید موفق می‌تواند از کاربر بپرسد:

- معرفی دوستان
- سرچ در تلگرام
- تبلیغات کانال‌ها
- Instagram
- Web/Search
- مشتری قبلی
- سایر

### Follow-up Trial

بعد از پایان Trial و پس از Delay تنظیم‌شده، ربات بررسی می‌کند آیا کاربر خرید کرده یا نه.

اگر خرید کرده باشد Follow-up فروش ارسال نمی‌شود.

اگر نخریده باشد دلیل را می‌پرسد، مثل:

- Speed/Quality
- Price
- Setup مشکل داشت
- Later
- No need
- Ready to buy
- Other

Delay پیش‌فرض 6 ساعت است و از Admin قابل تغییر است.

---

## نام دلخواه و سرویس قدیمی

### نام دلخواه

نام Custom:

- 3 تا 40 کاراکتر
- حروف انگلیسی/عدد و `.`, `_`, `-`
- قبل از Checkout در DB بررسی می‌شود.
- داخل خود 3x-ui نیز Duplicate Check می‌شود.

### افزودن سرویس قدیمی

کاربر نام Client موجود را وارد می‌کند.

برای امنیت:

- اگر `tgId` پنل با Telegram ID کاربر یکی باشد، Claim خودکار است.
- در غیر این صورت Admin Approval لازم است.
- یک Client فقط به یک حساب SpeedyBot قابل Link شدن است.

---

## پرداخت و بازاریابی

### Card / Manual Receipt

کاربر Receipt می‌فرستد و بعد از تأیید ادمین Provisioning انجام می‌شود.

### Wallet

- Balance
- Wallet ledger
- Admin credit/debit
- Purchase from wallet

### Referral

- Permanent invite link
- ثبت Referral فقط در اولین ورود
- Commission فقط بعد از خرید واجد شرایط و Provision موفق
- جلوگیری از Double Commission

### Cashback / Discount / Gift

ادمین می‌تواند:

- Cashback درصدی تنظیم کند.
- Discount درصدی یا ثابت بسازد.
- Minimum purchase بگذارد.
- Expiry/usage limit تعیین کند.
- Gift Code برای Wallet بسازد.

---

## تمدید

Renewal:

- همان Client را نگه می‌دارد.
- Subscription identity حفظ می‌شود.
- زمان باقی‌مانده Early Renewal از بین نمی‌رود.
- Quota/IP Limit با Plan جدید Sync می‌شود.
- Client Enable می‌شود.
- Traffic دوره جدید Reset می‌شود.
- Inboundهای Plan انتخاب‌شده اعمال می‌شوند.

---

## Groups

پیش‌فرض:

```text
Paid → Customers
Trial → Trial
```

بررسی:

```text
/groupsdiag
```

ربات می‌تواند Groupهای لازم را Ensure/Reconcile کند.

---

## سیستم نظر و امتیاز

کاربر می‌تواند 1 تا 5 ستاره بدهد و Comment اختیاری ثبت کند.

ادمین می‌بیند:

- تعداد Feedback
- Average rating
- Distribution ستاره‌ها
- آخرین Commentها

قابل روشن/خاموش کردن است.

---

## ارسال پیام هدفمند

Audienceهای فعلی:

- All active users
- Customers
- Trial users who did not buy
- Expired Trial who did not buy
- Never bought

ارسال با `copy_message` انجام می‌شود؛ بنابراین Text/Photo/Video/File قابل ارسال است.

ابتدا روی Audience کوچک تست کنید تا اشتباه Broadcast به همه مشتری‌ها رخ ندهد.

---

## Audit Log

رویدادهایی مثل:

```text
Operating mode change
User block/unblock
Category change
Trial override
Broadcast
Panel snapshot
UI change
```

داخل SQLite ثبت می‌شوند.

برای ارسال به Telegram Channel/Group، Bot باید اجازه ارسال پیام داشته باشد.

---

## Snapshot اضطراری پنل

از Export API پنل یک JSON برای Admin ساخته می‌شود.

**این Snapshot حساس است.** آن را داخل GitHub یا گروه عمومی منتشر نکنید.

Restore خودکار عمداً وجود ندارد؛ Snapshot برای Disaster Recovery/Manual investigation است.

---

## رنگ دکمه‌ها و Premium Emoji

Styleهای قابل استفاده:

```text
default
primary
success
danger
```

Telegram اجازه تنظیم رنگ دلخواه HEX/RGB برای Keyboardهای Bot را نمی‌دهد.

Custom Emoji:

1. از `/emojiid` استفاده کنید.
2. یک Custom Emoji بفرستید.
3. ID را در بخش UI مربوطه ثبت کنید.
4. Premium/Custom Emoji را فعال کنید.

اگر Telegram اجازه ندهد Feature را غیرفعال نگه دارید؛ ربات با Emoji معمولی قابل استفاده است.

---

## اعلان‌ها

Monitor به‌صورت دوره‌ای می‌تواند Eventهای یک‌باره بفرستد:

- 90% traffic warning
- نزدیک اتمام سرویس پولی
- نزدیک اتمام Trial
- Traffic exhausted
- Time expired

Claim رویدادها در SQLite ذخیره می‌شود تا Restart باعث ارسال دوباره همان Notification نشود.

---

## دستورات تشخیصی

### xuidiag

```text
/xuidiag
```

تست Read-only اتصال API و خطاهای Auth/Base Path/HTTP.

### groupsdiag

```text
/groupsdiag
```

Groupهای پنل و تعداد اعضا.

### notifydiag

```text
/notifydiag
```

اجرای دستی Monitor سرویس.

---

## آپدیت

قبل از Update Major، `MIGRATION_NOTES.md` را بخوانید.

### فقط بررسی وجود Update

```bash
cd /root/SpeedyBot
./update.sh --check
```

### Update عادی

```bash
./update.sh
```

### Force redeploy

```bash
./update.sh --force
```

Updater v4:

1. خودش را از `/tmp` دوباره اجرا می‌کند تا overwrite شدن `update.sh` اجرای جاری را خراب نکند.
2. Branch `main` را از GitHub بررسی می‌کند.
3. سورس جدید را در Temp Clone می‌کند.
4. Python/Shell syntax را قبل از Downtime بررسی می‌کند.
5. Dependencyها را قبل از Stop نصب می‌کند.
6. Bot را Stop می‌کند.
7. از `.env`, SQLite, WAL/SHM, سورس و ماژول‌های v4 Backup می‌گیرد.
8. سورس جدید را Deploy می‌کند.
9. `run.sh` را روی `app.py` قرار می‌دهد؛ اگر `app.py` نباشد fallback به `main.py` است.
10. systemd را Restart می‌کند.
11. Health Check انجام می‌دهد.
12. در Failure تلاش می‌کند Backup را Restore و سرویس قبلی را Restart کند.

---

## مهاجرت از v3.x به v4

**`.env` و `speedping.db` را حذف نکنید.**

روش معمول:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

بعد:

```bash
cat VERSION.txt
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

باید Version:

```text
4.0.0
```

باشد.

Migration v4 افزایشی است و جدول‌ها/ستون‌های جدید را اضافه می‌کند. داده‌های قبلی کاربران، Transactionها، Wallet، Referral، Trial و سرویس‌ها حذف نمی‌شوند.

پس از Upgrade:

```text
/start
/sudoadmin
/xuidiag
/groupsdiag
/notifydiag
```

را تست کنید.

---

## بکاپ و Rollback

Runtime مهم:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

Backupهای Deploy معمولاً در مسیر زیر قرار می‌گیرند:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

اگر Update Fail شود، Updater تلاش می‌کند نسخه قبلی را Restore کند.

برای کسب‌وکار واقعی فقط روی همان VPS Backup نگه ندارید؛ دوره‌ای Backup را به Storage دیگری منتقل کنید.

---

## عیب‌یابی

### ربات جواب نمی‌دهد

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 200 --no-pager
```

### Restart Loop

```bash
systemctl show xui-bot.service -p NRestarts
pgrep -af 'python.*(app.py|main.py)'
```

اگر چند Process Bot با یک Token وجود داشته باشد ممکن است Telegram Conflict بدهد. Production را فقط از systemd اجرا کنید.

### خطای 401 / 403

Bearer Token plaintext واقعی را بررسی کنید.

### خطای 404

بررسی کنید:

- API Base URL
- Base Path
- Reverse Proxy
- Panel API

مثال:

```text
Panel URL: https://panel.example.com:2053/secret/
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Subscription کار می‌کند ولی Direct Address اشتباه است

Direct URLها از Panel گرفته می‌شوند. خروجی را با **Copy URL** خود 3x-ui مقایسه کنید. اگر هر دو اشتباه‌اند Host/Share Address همان Inbound را اصلاح کنید.

### Trial Direct URL ندارد

بعضی Protocolها Share URL قابل استفاده ندارند. Inboundهای مناسب را برای Trial انتخاب کنید.

### ویرایش `.env`

```bash
nano /root/SpeedyBot/.env
systemctl restart xui-bot.service
```

**هیچ‌وقت `.env` را در Issue عمومی Paste نکنید.**

---

## امنیت

- `.env` را Commit نکنید.
- Bot Token را Public نکنید.
- 3x-ui API Token را Public نکنید.
- Subscription و Direct URI را مثل Password در نظر بگیرید.
- Snapshot پنل شامل اطلاعات حساس است.
- SSH را محدود کنید.
- Ubuntu و 3x-ui را Update نگه دارید.
- برای endpointهای عمومی TLS استفاده کنید.
- Claim سرویس قدیمی عمداً نیاز به `tgId` یا Admin Approval دارد.
- قبل از انتشار Log، Token/Domain secret/Base Path حساس را Redact کنید.

جزئیات: [SECURITY.md](SECURITY.md)

---

## ساختار فایل‌ها

```text
SpeedyBot/
├── main.py                    # stable v3 business core
├── app.py                     # v4 production entrypoint
├── speedybot_v4/
│   ├── __init__.py
│   ├── context.py
│   ├── storage.py
│   ├── ui.py
│   ├── user_handlers.py
│   ├── admin_handlers.py
│   ├── trial.py
│   ├── corepatch.py
│   └── ops.py
├── tests/
│   └── test_v4_storage.py
├── install.sh
├── update.sh
├── requirements.txt
├── VERSION.txt
├── README.md
├── README_FA.md
├── CHANGELOG.md
├── MIGRATION_NOTES.md
├── RELEASE_NOTES_v4.0.0.md
├── SECURITY.md
├── SUPPORT.md
├── CONTRIBUTING.md
├── AUTHOR.md
├── LICENSE
├── .env.example
└── .github/
```

Runtime Files مثل `.env`, DB, `.venv`, Backup و Log توسط `.gitignore` از Git خارج می‌شوند.

---

## محدوده پروژه و آینده

مواردی مثل:

- Multi-panel routing
- Batch order / reseller suite
- چند Payment Gateway آنلاین
- Mini App
- Web Admin مستقل
- AI Support
- Restore خودکار پنل با Dry-run و تأیید چندمرحله‌ای

Featureهای بزرگ‌تری هستند و بهتر است با معماری و تست جدا وارد پروژه شوند.

Bug و Feature Request را از GitHub Issues ارسال کنید و قبل از ارسال Log تمام Secretها را حذف کنید.

---

## سازنده و لایسنس

پروژه تحت **MIT License** منتشر شده است.

**SudoShayanNA**

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- Repository: **https://github.com/roseshayan/SpeedyBot**

اگر پروژه را Fork یا بازنشر می‌کنید، نگه‌داشتن لینک سورس اصلی کمک می‌کند کاربران به مستندات، نسخه‌های جدید و Security Updateهای Upstream دسترسی داشته باشند.
