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
> تلگرام: **@SudoShayanNA** · ایمیل: **namayandeshayan@gmail.com**  
> سورس رسمی: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot یک ربات تلگرام عملی برای فروش و مدیریت سرویس‌های **3x-ui / Sanaei** است. ربات می‌تواند بعد از تأیید پرداخت Client بسازد، تست رایگان بدهد، پلان بفروشد و تمدید کند، لینک Subscription و کانفیگ مستقیم تحویل دهد، QR بسازد، کیف پول و Referral داشته باشد، پایان حجم/زمان را پیگیری کند، راهنمای اتصال بسازد و بیشتر عملیات روزمره فروش و مدیریت را از داخل Telegram انجام دهد.

## مهم: نسخه v4 خودِ پروژه است

نسخه نهایی v4 دیگر یک پوشه یا Add-on جدا روی نسخه قدیمی نیست.

Entry Point رسمی و Production پروژه فقط این فایل است:

```text
/root/SpeedyBot/main.py
```

کد اصلی برنامه در پکیج دائمی زیر قرار دارد:

```text
/root/SpeedyBot/speedybot/
```

پوشه‌های نسخه‌دار مثل `speedybot_v4/` و Entry Point جدا مثل `app.py` در ساختار نهایی وجود ندارند. Installer، Updater، systemd و اجرای دستی همگی از همان `main.py` استفاده می‌کنند.

---

## فهرست

- [امکانات](#امکانات)
- [قابلیت‌های جدید v4](#قابلیتهای-جدید-v4)
- [پلان‌های پیش‌فرض](#پلانهای-پیشفرض)
- [پیش‌نیازها](#پیشنیازها)
- [قبل از نصب](#قبل-از-نصب)
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
- [مهاجرت از v3.x](#مهاجرت-از-v3x-به-v4)
- [بکاپ و Rollback](#بکاپ-و-rollback)
- [عیب‌یابی](#عیبیابی)
- [ساختار پروژه](#ساختار-پروژه)
- [امنیت](#امنیت)
- [سازنده و لایسنس](#سازنده-و-لایسنس)

---

## امکانات

### فروش و ساخت خودکار سرویس

- ساخت Client در 3x-ui بعد از تأیید پرداخت.
- تست رایگان پیش‌فرض: **1 GB / 1 day / 1 IP**.
- پلان‌های داینامیک داخل SQLite.
- `limitIp` مستقل برای هر پلان.
- پرداخت کارت‌به‌کارت/ارسال رسید و تأیید ادمین.
- خرید مستقیم با Wallet.
- Retry و Idempotency برای جلوگیری از Client تکراری در خطا یا Restart.
- تحویل Subscription URL.
- تحویل Direct Config واقعی.
- QR سابسکریپشن.
- تمدید همان Client با حفظ هویت سرویس.
- بسته حجم اضافه برای پلان‌های حجمی.

### امکانات کاربر

- حساب کاربری.
- وضعیت زنده سرویس.
- نمایش حجم و زمان باقی‌مانده.
- Subscription و Direct Config.
- QR.
- تمدید.
- حجم اضافه در صورت پشتیبانی پلان.
- تاریخچه خرید و کیف پول.
- کد هدیه و تخفیف.
- Referral/Affiliate.
- راهنمای اتصال بر اساس Platform.
- افزودن سرویس خریداری‌شده قبلی.
- نام دلخواه هنگام خرید.
- ثبت امتیاز و Feedback.
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
- CTA خرید یا پشتیبانی.
- Broadcast هدفمند.
- آمار Feedback و رضایت مشتری.

### امکانات ادمین

از `/sudoadmin` می‌توانید مدیریت کنید:

- پلان‌ها و قیمت‌ها.
- دسته‌بندی پلان‌ها.
- Volume Packها.
- روشن/خاموش کردن Trial.
- Inboundهای Trial و هر Plan.
- Trial اختصاصی برای User مشخص.
- Groups پنل Sanaei.
- CRM و Follow-up.
- Wallet و Referral.
- Cashback، Gift و Discount Code.
- اطلاعات پرداخت.
- Welcome و FAQ.
- احراز شماره و عضویت کانال.
- چند ادمین.
- اعلان‌های سرویس.
- بکاپ.
- Blacklist.
- Operating Mode.
- Feedback.
- Broadcast هدفمند.
- Audit Log.
- Snapshot خواندنی پنل.
- Style دکمه و Custom/Premium Emoji.

---

## قابلیت‌های جدید v4

### Control Center مرتب‌تر

پنل مدیریت بازطراحی شده تا متن‌ها خواناتر، منوها دسته‌بندی‌شده‌تر و عملیات پرتکرار سریع‌تر در دسترس باشند.

### حالت‌های عملیاتی

- `NORMAL` — همه قابلیت‌های تنظیم‌شده فعال هستند.
- `SALES_PAUSED` — خرید جدید، تمدید و حجم اضافه بسته می‌شوند؛ حساب، راهنما و Support فعال می‌مانند.
- `MAINTENANCE` — خرید و Trial جدید بسته می‌شوند؛ حساب، راهنما و Support فعال می‌مانند.

### Blacklist / محدودیت خرید

ادمین می‌تواند User را همراه دلیل از خرید/Trial محدود کند و بعداً محدودیت را بردارد. کاربر همچنان به Account و Support دسترسی دارد.

### دسته‌بندی پلان‌ها

مثلاً:

```text
🇩🇪 آلمان
🎮 گیمینگ
🌐 رفع تحریم
📌 IP ثابت
🏢 سازمانی
```

پلان‌های قدیمی که Category ندارند هنگام Migration وارد دسته `عمومی` می‌شوند.

### Trial اختصاصی

برای یک Telegram ID می‌توانید قبل از اولین Trial حجم، تعداد روز و IP Limit متفاوت تعریف کنید.

### Feedback

امتیاز 1 تا 5 ستاره + Comment اختیاری + میانگین + توزیع امتیاز + آخرین نظرات در Admin.

### Broadcast هدفمند

ارسال پیام به Audience مشخص به‌جای همه کاربران.

### Audit Log

عملیات مدیریتی مهم در SQLite ذخیره می‌شوند و در صورت تمایل می‌توانند به یک Group/Channel خصوصی Telegram هم ارسال شوند.

### Panel Snapshot

یک Export خواندنی JSON از Clientهای پنل برای بررسی و Disaster Recovery. Restore مخرب یک‌کلیکی عمداً اضافه نشده است.

### Style دکمه و Premium Emoji

Styleهای رسمی Telegram:

```text
default
primary
success
danger
```

رنگ HEX/RGB آزاد توسط Telegram Bot API در اختیار Bot نیست.

Custom/Premium Emoji اختیاری است و اگر Telegram اجازه ندهد ربات با Emoji معمولی ادامه می‌دهد.

---

## پلان‌های پیش‌فرض

در دیتابیس تازه:

| پلان | مدت | حجم | IP Limit | قیمت پیش‌فرض |
|---|---:|---:|---:|---:|
| نامحدود 1 کاربر | 30 روز | نامحدود | 1 | 250,000 تومان |
| نامحدود 2 کاربر | 30 روز | نامحدود | 2 | 300,000 تومان |
| نامحدود 3 کاربر | 30 روز | نامحدود | 3 | 350,000 تومان |

این‌ها Seed اولیه هستند. قبل از فروش واقعی قیمت‌ها و پلان‌ها را از `/sudoadmin` بررسی و اصلاح کنید.

---

## پیش‌نیازها

پیشنهاد برای Production:

- Ubuntu **24.04 LTS**.
- Python 3.12.
- پنل به‌روز 3x-ui / Sanaei با API مسیر `/panel/api/*`.
- Bearer API Token پنل.
- Bot Token از `@BotFather`.
- Telegram ID عددی Owner.
- Subscription Server فعال در صورت استفاده از لینک ساب.
- دسترسی خروجی VPS به Telegram و پنل.

ربات از Long Polling استفاده می‌کند و برای Telegram نیازی به باز کردن Webhook Port ندارد.

---

## قبل از نصب

### 1) ساخت ربات Telegram

در `@BotFather`:

1. `/newbot` را ارسال کنید.
2. نام نمایشی انتخاب کنید.
3. Username تمام‌شونده به `bot` انتخاب کنید.
4. Bot Token را ذخیره کنید.

Token را در Issue، Screenshot، README، Log یا Commit عمومی قرار ندهید.

### 2) Telegram ID ادمین

Telegram ID **عددی** حساب Owner را پیدا کنید. Username با Numeric ID فرق دارد.

این مقدار به‌عنوان `ADMIN_ID` اولیه استفاده می‌شود.

### 3) ساخت API Token در 3x-ui

داخل پنل:

```text
Settings → Security → API Token
```

Token بسازید و **مقدار plaintext واقعی Token** را ذخیره کنید.

موارد زیر Bearer Token نیستند:

- اسم Token.
- Password ورود پنل.
- مسیر مخفی پنل.

### 4) تفاوت Base URL و Base Path

اگر پنل شما:

```text
https://panel.example.com:2053/secret-panel/
```

است، معمولاً باید وارد کنید:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

اگر مسیر مخفی ندارید:

```text
X-UI security base path: /
```

### 5) Subscription

اگر لینک واقعی کاربر:

```text
https://sub.example.com:2096/sub/ABC123
```

است:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

اگر مسیر Subscription پنل شما متفاوت است مقدار واقعی خودتان را وارد کنید.

---

## نصب مرحله‌ای

با Root وارد VPS شوید:

```bash
apt update
apt install -y git

git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

Installer این موارد را می‌پرسد:

1. Telegram Bot Token.
2. Telegram Admin numeric ID.
3. X-UI API base URL.
4. X-UI security base path.
5. Panel Bearer API Token.
6. Subscription server base URL.
7. Subscription URI path.

قبل از ساخت سرویس systemd، Installer یک تست Read-only روی API پنل انجام می‌دهد تا Token یا Base Path اشتباه همان ابتدا مشخص شود.

### فایل‌های Runtime مهم

```text
/root/SpeedyBot/.env
/root/SpeedyBot/.venv/
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/run.sh
/root/SpeedyBot/backups/
```

سرویس:

```text
xui-bot.service
```

Runner فقط فایل زیر را اجرا می‌کند:

```text
/root/SpeedyBot/main.py
```

### وضعیت سرویس

```bash
systemctl status xui-bot.service --no-pager -l
```

### لاگ زنده

```bash
journalctl -u xui-bot.service -f
```

### Restart

```bash
systemctl restart xui-bot.service
```

---

## کارهای ضروری بعد از نصب

با حساب Owner:

```text
/start
/sudoadmin
```

قبل از فروش واقعی:

1. اطلاعات پرداخت نمونه را عوض کنید.
2. قیمت، روز، حجم و IP Limit پلان‌ها را بررسی کنید.
3. Categoryهای پلان را تنظیم کنید.
4. وارد بخش Trial & Inbounds شوید.
5. Trial را روشن/خاموش کنید.
6. برای Trial و هر Plan Inbound مناسب انتخاب کنید.
7. Groups `Customers` و `Trial` را بررسی/Reconcile کنید.
8. برای Android/iOS/Windows/macOS/Linux/TV راهنما بسازید.
9. CRM و Follow-up را بررسی کنید.
10. در صورت نیاز Phone Verification/Channel Membership را فعال کنید.
11. Operating Mode را روی `NORMAL` بررسی کنید.
12. Button Styleها را بررسی کنید.
13. در صورت نیاز Audit Chat تنظیم کنید.
14. `/xuidiag` را اجرا کنید.
15. `/groupsdiag` را اجرا کنید.
16. `/notifydiag` را اجرا کنید.
17. یک Trial واقعی تست کنید.
18. قبل از فروش گسترده یک خرید کامل End-to-End تست کنید.

---

## پنل مدیریت

دستور اصلی:

```text
/sudoadmin
```

دستورات تشخیصی:

```text
/xuidiag
/groupsdiag
/notifydiag
```

- `/xuidiag`: تست Read-only ارتباط API پنل.
- `/groupsdiag`: وضعیت زنده Client Groupها.
- `/notifydiag`: اجرای دستی مانیتور سرویس.

---

## حالت‌های عملیاتی

### NORMAL

همه قابلیت‌های تنظیم‌شده فعال‌اند.

### SALES_PAUSED

خرید جدید، تمدید و حجم اضافه غیرفعال می‌شوند؛ Account، Guide و Support فعال می‌مانند.

### MAINTENANCE

خرید و Trial جدید غیرفعال می‌شوند؛ کاربر همچنان سرویس‌های قبلی، Guide و Support را دارد.

---

## دسته‌بندی پلان‌ها

از `/sudoadmin` Category بسازید و Plan IDها را به Category مناسب منتقل کنید. پلان‌های بدون Category هنگام Migration وارد `عمومی` می‌شوند.

---

## تست رایگان و انتخاب Inbound

مسیر:

```text
/sudoadmin → Trial & Inbounds
```

امکانات:

- روشن/خاموش کردن Trial.
- انتخاب Inboundهای Trial.
- انتخاب مستقل Inbound برای هر Plan.
- Reset یک Scope روی تمام Inboundهای فعال.

اگر برای Scope خاصی انتخاب ذخیره نشده باشد، SpeedyBot برای سازگاری با نسخه قدیمی از **تمام Inboundهای فعال** استفاده می‌کند.

### Direct Config با Subscription فرق دارد

Direct Link فقط Schemeهای واقعی Proxy را شامل می‌شود، مثل:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

URLهای `http://` و `https://` در بخش Subscription نگه داشته می‌شوند و به‌عنوان Direct Config نمایش داده نمی‌شوند.

اگر Address اشتباه بود، خروجی ربات را با **Copy URL** خود 3x-ui مقایسه کنید. اگر هر دو Host اشتباه داشتند، Share Address/Public Host همان Inbound را در پنل اصلاح کنید.

---

## تست اختصاصی برای یک کاربر

قبل از اولین Trial کاربر:

```text
TelegramID | حجم GB | روز | IP Limit | یادداشت اختیاری
```

مثال:

```text
123456789 | 5 | 3 | 2 | مشتری VIP
```

Inboundهای اصلی Trial همچنان اعمال می‌شوند.

---

## راهنمای اتصال کاربران

ادمین می‌تواند برای این Platformها Guide بسازد:

- Android.
- iPhone / iOS.
- Windows.
- macOS.
- Linux.
- Android TV / TV Box.

هر Guide می‌تواند شامل:

- Text.
- Photo + Caption.
- Video + Caption.

باشد.

به‌جای ذخیره فایل Media داخل SQLite، `file_id` تلگرام نگه‌داری می‌شود.

---

## CRM و پیگیری بعد از تست

### از کجا با ما آشنا شدید؟

بعد از اولین خرید موفق، در صورت فعال بودن قابلیت، ربات می‌تواند منبع آشنایی کاربر را بپرسد؛ مثل معرفی دوستان، Telegram Search، تبلیغات کانال‌ها، Instagram، Web/Search، مشتری قبلی یا سایر.

### Follow-up Trial

بعد از پایان حجم یا زمان Trial، ربات می‌تواند بعد از Delay تنظیم‌شده بررسی کند کاربر خرید کرده یا نه.

اگر خرید کرده باشد Follow-up ارسال نمی‌شود.

اگر نخریده باشد علت را می‌پرسد، مثل:

- سرعت/کیفیت.
- قیمت.
- مشکل راه‌اندازی.
- بعداً می‌خرم.
- فعلاً نیاز ندارم.
- آماده خرید هستم.
- سایر.

بر اساس پاسخ CTA خرید یا Support نمایش داده می‌شود.

---

## نام دلخواه و سرویس قدیمی

### نام دلخواه Client

قوانین:

- 3 تا 40 کاراکتر.
- حروف انگلیسی، عدد و `.`, `_`, `-`.
- بررسی Duplicate داخل DB ربات.
- بررسی Duplicate داخل خود 3x-ui قبل از Checkout.

### اتصال سرویس خریداری‌شده قبلی

کاربر از Account نام Client موجود در 3x-ui را وارد می‌کند.

برای امنیت:

- اگر `tgId` پنل با Telegram ID کاربر یکی باشد → اتصال خودکار.
- اگر یکی نباشد → نیاز به تأیید Admin.
- یک Client فقط به یک حساب SpeedyBot قابل اتصال است.

---

## پرداخت و بازاریابی

### کارت‌به‌کارت / رسید

ربات اطلاعات پرداخت را نشان می‌دهد، تصویر رسید می‌گیرد و بعد از تأیید Admin سرویس ساخته می‌شود.

### Wallet

- موجودی.
- Ledger.
- افزایش/کاهش توسط Admin.
- خرید مستقیم با موجودی کافی.

### Referral

- لینک دعوت دائمی.
- ثبت معرف در اولین Registration.
- پورسانت بعد از خرید واجد شرایط و Provision موفق.
- جلوگیری از پرداخت دوباره Commission برای یک Transaction.

### Cashback / Discount / Gift

ادمین می‌تواند Cashback، Discount درصدی/ثابت، حداقل خرید، Expiry/Usage Limit و Gift Code برای Wallet تنظیم کند.

---

## تمدید

Renewal:

- همان Client را حفظ می‌کند.
- زمان باقی‌مانده را در تمدید زودهنگام از بین نمی‌برد.
- Quota/IP Limit را با Plan جدید هماهنگ می‌کند.
- Client را Enable می‌کند.
- Traffic دوره جدید را Reset می‌کند.
- Inboundها را با Plan تمدید Sync می‌کند.

---

## Groups

پیش‌فرض:

```text
سرویس پولی → Customers
تست رایگان → Trial
```

بررسی:

```text
/groupsdiag
```

---

## سیستم نظر و امتیاز

کاربر می‌تواند 1 تا 5 ستاره + Comment اختیاری ثبت کند.

Admin می‌بیند:

- تعداد کل Feedback.
- میانگین امتیاز.
- توزیع ستاره‌ها.
- آخرین Commentها.

این قابلیت قابل خاموش/روشن شدن است.

---

## ارسال پیام هدفمند

Audienceها شامل:

- همه کاربران فعال.
- مشتریان خریدار.
- Trial گرفته ولی نخریده.
- Trial منقضی ولی نخریده.
- هیچ‌وقت خرید نکرده.

ارسال با Telegram `copy_message` انجام می‌شود و Text/Photo/Video/Document قابل استفاده است.

قبل از Broadcast سراسری حتماً روی Audience کوچک تست کنید.

---

## Audit Log

عملیات مهم Admin در SQLite ذخیره می‌شوند. در صورت تنظیم Chat ID، رویدادها می‌توانند به Group/Channel خصوصی Telegram هم ارسال شوند.

---

## Snapshot اضطراری پنل

Admin می‌تواند JSON خواندنی از Clientهای 3x-ui Export کند.

این فایل شامل اطلاعات حساس سرویس است و نباید در GitHub Issue یا Group عمومی منتشر شود.

---

## رنگ دکمه‌ها و Premium Emoji

Styleهای رسمی:

```text
default
primary
success
danger
```

برای Custom Emoji از `/emojiid` استفاده کنید، ID را در Admin ثبت کنید و قبل از فعال‌سازی عمومی Test Eligibility را اجرا کنید.

---

## اعلان‌ها

مانیتور سرویس می‌تواند رویدادهای یک‌باره برای این موارد بفرستد:

- هشدار مصرف نزدیک 90٪.
- نزدیک پایان سرویس پولی.
- نزدیک پایان Trial.
- پایان حجم.
- پایان زمان.

رویدادهای ارسال‌شده در SQLite ثبت می‌شوند تا Restart باعث Duplicate Message بی‌دلیل نشود.

---

## دستورات تشخیصی

### ربات جواب نمی‌دهد

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 200 --no-pager
```

### خطای 401 / 403

Bearer Token **plaintext** را بررسی کنید. اسم Token یا Password پنل را جای آن نگذارید.

### خطای 404

بررسی کنید:

- API Base URL.
- Base Path.
- Reverse Proxy.
- API/Version پنل.

مثال:

```text
Panel: https://panel.example.com:2053/secret/
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Process تکراری

```bash
systemctl show xui-bot.service -p NRestarts
pgrep -af 'python.*main.py'
```

به‌طور معمول فقط Process مدیریت‌شده توسط systemd باید Bot Token اصلی را استفاده کند.

---

## آپدیت

Updater جدید **کل Repository** را Sync می‌کند؛ نه فقط یک لیست دستی از چند فایل.

### بررسی آپدیت

```bash
cd /root/SpeedyBot
./update.sh --check
```

### آپدیت

```bash
./update.sh
```

### Force Redeploy

```bash
./update.sh --force
```

### Updater دقیقاً چه می‌کند؟

1. خودش را از `/tmp` دوباره اجرا می‌کند تا هنگام Replace شدن `update.sh` قطع نشود.
2. Commit فعلی `main` در GitHub را پیدا می‌کند.
3. کل Repository را داخل `/tmp` Clone می‌کند.
4. `main.py`، تمام `speedybot/*.py`، `install.sh` و `update.sh` را Validate می‌کند.
5. Dependencyها را قبل از Downtime نصب می‌کند.
6. systemd را Stop می‌کند.
7. از کل Source فعلی یک Rollback Backup می‌گیرد.
8. `.env` و SQLite DB/WAL/SHM را جدا بکاپ می‌گیرد.
9. با `rsync --delete` کل Source سرور را با Repository هماهنگ می‌کند.
10. `.env`، `.venv/`، SQLite، `backups/`، `run.sh` و `.deployed_commit` را Preserve می‌کند.
11. `run.sh` را طوری می‌سازد که فقط `main.py` را اجرا کند.
12. سرویس را Restart و Health Check می‌کند.
13. Crash Loop اولیه را بررسی می‌کند.
14. اگر Deploy خراب باشد، Source و دیتابیس قبلی را Restore می‌کند.

چون Source با `--delete` Sync می‌شود، فایل‌ها و پوشه‌های قدیمی که دیگر در GitHub وجود ندارند خودکار از Deployment حذف می‌شوند. یعنی سرور واقعاً با نسخه منتشرشده یکی می‌شود.

---

## مهاجرت از v3.x به v4

`.env` و `speedping.db` را حذف نکنید.

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

بعد بررسی کنید:

```bash
cat VERSION.txt
cat run.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

نسخه باید:

```text
4.0.0
```

باشد و `run.sh` باید به:

```text
/root/SpeedyBot/main.py
```

اشاره کند.

Migration دیتابیس v4 افزایشی است و اطلاعات قبلی کسب‌وکار را حفظ می‌کند.

قبل از Major Update فایل [MIGRATION_NOTES.md](MIGRATION_NOTES.md) را بخوانید.

---

## بکاپ و Rollback

Deployment Backupها:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

Runtime حیاتی:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

برای Production واقعی فقط به همان VPS اکتفا نکنید و دوره‌ای Backup را به Storage/سیستم دیگری منتقل کنید.

---

## ساختار پروژه

```text
SpeedyBot/
├── main.py                    # Entry Point اصلی و Production
├── speedybot/                 # پکیج یکپارچه برنامه
│   ├── __init__.py
│   ├── core.py                # هسته فروش و Provisioning
│   ├── context.py
│   ├── storage.py
│   ├── ui.py
│   ├── user_handlers.py
│   ├── admin_handlers.py
│   ├── trial.py
│   ├── corepatch.py
│   ├── ops.py
│   └── handlers.py
├── tests/
│   └── test_storage.py
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

هیچ پوشه نسخه‌داری مثل `speedybot_v4/` در Application وجود ندارد.

---

## امنیت

- `.env` را Commit نکنید.
- Bot Token تلگرام را Public نکنید.
- API Token پنل را Public نکنید.
- Subscription، Direct Config و QR را مثل Password در نظر بگیرید.
- Panel Snapshot حساس است.
- Ubuntu، SSH و 3x-ui را به‌روز نگه دارید.
- برای Endpointهای خارجی TLS استفاده کنید.
- Claim سرویس قدیمی نیاز به `tgId` یکسان یا تأیید Admin دارد.
- قبل از ارسال Log در Issue، Secretها را حذف کنید.

جزئیات: [SECURITY.md](SECURITY.md)

---

## سازنده و لایسنس

پروژه تحت **MIT License** منتشر شده است.

سازنده و Maintainer:

**SudoShayanNA**

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- Repository: **https://github.com/roseshayan/SpeedyBot**

اگر پروژه را Fork یا بازنشر می‌کنید، نگه‌داشتن لینک سورس اصلی باعث می‌شود کاربران به مستندات، آپدیت‌های امنیتی و نسخه Maintained دسترسی داشته باشند.
