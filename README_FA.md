# SpeedyBot v4.0.0

<p align="center"><strong>ربات متن‌باز فروش، مدیریت اشتراک و CRM تلگرامی برای 3x-ui / Sanaei</strong></p>

<p align="center"><a href="README.md">🇬🇧 English</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="SECURITY.md">Security</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

> **سازنده و نگهدارنده:** **SudoShayanNA**  
> تلگرام: **@SudoShayanNA** · ایمیل: **namayandeshayan@gmail.com**  
> سورس رسمی: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot تلگرام را به یک فروشگاه و مرکز کنترل برای پنل **3x-ui / Sanaei** تبدیل می‌کند. صدور خودکار سرویس، تست رایگان، تمدید، کیف پول، همکاری در فروش، مدیریت Inbound، CRM، آموزش اتصال و عملیات مدیریتی بدون نیاز به پنل وب جدا انجام می‌شوند.

## مهم‌ترین تغییرات v4

- معماری ماژولار جدید: هسته پایدار v3 در `main.py` باقی مانده و قابلیت‌های جدید از `speedybot_v4/` توسط `app.py` بارگذاری می‌شوند.
- پنل مدیریت مرتب‌تر و خواناتر با عنوان **SpeedyBot Control Center**.
- صفحه حساب کاربری و فروشگاه پلان‌ها مرتب‌تر و دسته‌بندی‌شده.
- پشتیبانی از رنگ‌های رسمی جدید دکمه‌های تلگرام: آبی، سبز و قرمز.
- پشتیبانی اختیاری از Custom/Premium Emoji روی دکمه‌ها به همراه تست و fallback.
- سه حالت عملیاتی: **عادی، توقف فروش، تعمیرات**.
- Blacklist / محدودیت خرید کاربر همراه دلیل و Audit Log.
- دسته‌بندی پلان‌ها.
- تست اختصاصی برای یک کاربر با حجم، تعداد روز و IP Limit متفاوت.
- سیستم امتیاز ۱ تا ۵ ستاره + نظر متنی و گزارش ادمین.
- Broadcast هدفمند بر اساس نوع مخاطب.
- Audit Log دیتابیسی + امکان ارسال رویدادها به کانال/گروه تلگرام.
- Snapshot اضطراری Read-only از Clientهای پنل 3x-ui.
- تمام امکانات v3.1 مثل CRM، Follow-up تست، راهنمای اتصال، Inbound هر پلان، Groups، کیف پول، Referral، Cashback و کدها حفظ شده‌اند.

## پیش‌نیازها

پیشنهاد برای نصب Production:

- Ubuntu 24.04 LTS
- Python 3.12 یا جدیدتر
- پنل به‌روز 3x-ui/Sanaei با API مسیر `/panel/api/*`
- API Token از نوع Bearer
- Bot Token از `@BotFather`
- Telegram ID عددی ادمین اصلی
- Subscription Server فعال در صورت استفاده از لینک ساب

ربات با Long Polling کار می‌کند و نیازی به باز کردن پورت Webhook تلگرام ندارد.

## نصب از صفر

```bash
apt update
apt install -y git

git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

Installer به ترتیب این اطلاعات را می‌پرسد:

1. Telegram Bot Token
2. Telegram ID عددی Owner
3. آدرس API پنل، مثل `https://panel.example.com:2053`
4. Base Path امنیتی پنل، مثل `/secret` یا `/`
5. مقدار واقعی Bearer API Token از **Settings → Security → API Token**
6. Base URL سرور Subscription
7. مسیر Subscription، معمولاً `/sub/`

قبل از ساخت سرویس systemd، Installer یک تست Read-only روی API پنل انجام می‌دهد.

فایل‌های Runtime مهم:

```text
/root/SpeedyBot/.env          اطلاعات حساس
/root/SpeedyBot/speedping.db  دیتابیس SQLite
/root/SpeedyBot/run.sh        Runner سرویس
```

بررسی وضعیت:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -f
```

## آپدیت از v3.x به v4

`.env` و `speedping.db` را حذف نکنید.

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

Updater نسخه v4:

1. خودش را از یک کپی موقت اجرا می‌کند تا وسط آپدیت فایل در حال اجرای خودش را overwrite نکند.
2. قبل از Downtime سورس جدید را Clone و Syntax را بررسی می‌کند.
3. Dependencyها را قبل از Stop کردن ربات نصب می‌کند.
4. از `.env`، SQLite، WAL/SHM، سورس و ماژول‌های v4 بکاپ می‌گیرد.
5. فایل‌های جدید را Deploy می‌کند.
6. Runner را در صورت وجود `app.py` روی نسخه v4 قرار می‌دهد.
7. systemd را Restart و Health Check می‌کند.
8. در صورت شکست، نسخه قبلی را Rollback می‌کند.

Migration دیتابیس v4 فقط افزایشی است؛ اطلاعات کاربران، تراکنش‌ها، کیف پول، تست‌ها و سرویس‌های قبلی حفظ می‌شوند.

## پنل مدیریت v4

ارسال کنید:

```text
/sudoadmin
```

بخش‌های اصلی:

- آمار فروش و مدیریت پلان‌ها
- دسته‌بندی پلان‌ها
- تست رایگان و Inboundها
- تست اختصاصی یک کاربر
- Groups پنل Sanaei
- CRM و پیگیری تست‌ها
- گزارش رضایت مشتری
- پیام هدفمند
- کدها، Cashback و Referral
- وضعیت عملیاتی و Blacklist
- احراز شماره، عضویت اجباری و مدیران
- اعلان‌ها و وضعیت سرور
- Backup و Snapshot پنل
- Audit Log
- ظاهر، رنگ دکمه و Premium Emoji
- حساب واریز، متن‌ها و FAQ

## وضعیت عملیاتی ربات

### 🟢 عادی

تمام قابلیت‌ها فعال هستند.

### 🟠 توقف فروش

خرید جدید، تمدید و خرید حجم اضافه متوقف می‌شوند؛ اما حساب کاربری، آموزش و پشتیبانی کار می‌کنند.

### 🔴 تعمیرات

علاوه بر خرید، صدور تست جدید هم متوقف می‌شود. کاربر همچنان می‌تواند سرویس‌هایش را ببیند، آموزش بخواند و به پشتیبانی پیام بدهد.

این طراحی بهتر از خاموش‌کردن کامل Bot است چون در زمان Maintenance مشتری از پشتیبانی محروم نمی‌شود.

## دسته‌بندی پلان‌ها

از:

```text
/sudoadmin → دسته‌بندی پلان‌ها
```

می‌توانید دسته‌هایی مثل این بسازید:

```text
🇩🇪 آلمان
🎮 گیمینگ
🌐 رفع تحریم
📌 IP ثابت
🏢 سازمانی
```

پلان‌های قدیمی هنگام Migration خودکار وارد دسته `عمومی` می‌شوند و بعداً می‌توانید هر Plan ID را به دسته دلخواه منتقل کنید.

## تست اختصاصی برای یک کاربر

اگر برای یک مشتری خاص می‌خواهید تست متفاوت بدهید، قبل از اولین Trial این فرمت را ثبت کنید:

```text
TelegramID | حجم GB | روز | IP Limit | یادداشت اختیاری
```

مثال:

```text
123456789 | 5 | 3 | 2 | مشتری VIP
```

Inboundهای تست همچنان از تنظیمات اصلی Trial انتخاب می‌شوند. کاربران بدون Override همان تست عمومی را می‌گیرند.

## Blacklist / محدودیت خرید

ادمین می‌تواند کاربر را با دلیل محدود کند. کاربر محدودشده نمی‌تواند خرید یا Trial جدید بگیرد ولی برای حل مشکل همچنان به Account و Support دسترسی دارد.

نمونه دلیل:

```text
سوءاستفاده از تست رایگان
فیش نامعتبر تکراری
درخواست کاربر
```

رفع محدودیت هم از همان Control Center انجام می‌شود.

## سیستم نظر و امتیاز

کاربر از منو یا حسابش می‌تواند بین ۱ تا ۵ ستاره امتیاز بدهد و یک Comment اختیاری بنویسد.

ادمین می‌بیند:

- تعداد کل Feedback
- میانگین امتیاز
- توزیع ۱ تا ۵ ستاره
- آخرین نظرات کاربران

این بخش قابل روشن/خاموش شدن است.

## ارسال پیام هدفمند

به‌جای Broadcast به همه، می‌توانید Audience انتخاب کنید:

- همه کاربران فعال
- فقط مشتریان خریدار
- کاربران تست‌گرفته که نخریده‌اند
- کاربران با تست منقضی که نخریده‌اند
- کسانی که هیچ خریدی نداشته‌اند

پیام با قابلیت Telegram `copy_message` ارسال می‌شود، بنابراین متن، تصویر، ویدئو یا فایل قابل ارسال است. در پایان تعداد موفق/ناموفق ذخیره و نمایش داده می‌شود.

## Audit Log

عملیات مهم v4 در SQLite ثبت می‌شوند؛ مثل:

```text
تغییر حالت فروش
Blacklist / Unblock
ساخت یا تغییر Category
تغییر Trial Override
ارسال Broadcast
ساخت Panel Snapshot
تغییر ظاهر
```

می‌توانید Chat ID یک کانال یا گروه خصوصی را هم تنظیم کنید تا Eventهای مهم به آنجا ارسال شوند. Bot باید اجازه ارسال پیام داشته باشد.

## Snapshot اضطراری پنل

این بخش از API Export کلاینت‌های 3x-ui یک فایل JSON می‌سازد و برای ادمین می‌فرستد.

**Snapshot فقط Read-only است.** عمداً Restore خودکار و مخرب اضافه نشده تا یک کلیک اشتباه اطلاعات پنل را overwrite نکند.

فایل Snapshot شامل اطلاعات حساس سرویس‌هاست و نباید در GitHub یا گروه عمومی منتشر شود.

## رنگ دکمه‌ها

تلگرام امکان انتخاب RGB یا HEX دلخواه برای Bot Button نمی‌دهد. Styleهای رسمی قابل استفاده هستند:

```text
primary  → آبی
success  → سبز
danger   → قرمز
default   → ظاهر پیش‌فرض کلاینت
```

از:

```text
/sudoadmin → ظاهر و دکمه‌ها
```

می‌توانید Style دکمه‌های خرید، حساب کاربری، تست، راهنما، پشتیبانی و مدیریت را تغییر دهید یا Preset حرفه‌ای را اعمال کنید.

## Premium / Custom Emoji روی دکمه

v4 می‌تواند `icon_custom_emoji_id` را برای دکمه‌های مهم ذخیره کند.

برای پیدا کردن ID:

```text
/emojiid
```

را بزنید و بعد یک Custom Emoji تلگرام بفرستید.

Telegram برای استفاده Bot از Custom Emoji روی Button محدودیت/شرایط خودش را دارد. SpeedyBot این قابلیت را اختیاری نگه می‌دارد و قبل از فعال‌سازی، Custom Emoji تنظیم‌شده را Live Test می‌کند. اگر اکانت/Bot شرایط لازم را نداشته باشد، ربات با ایموجی و متن معمولی قابل استفاده می‌ماند.

## امکانات نسخه‌های قبلی که همچنان هستند

- صدور خودکار سرویس پولی و Trial
- انتخاب Inbound جدا برای Trial و هر Plan
- Direct Config + Subscription + QR
- تمدید بدون تغییر هویت Client/Subscription
- بسته حجم اضافه برای پلان‌های حجمی
- اتصال امن سرویس قدیمی با `tgId` یا تأیید Admin
- نام دلخواه کانفیگ با Duplicate Check داخل DB و 3x-ui
- Wallet و تاریخچه immutable
- Referral / Affiliate
- Cashback
- Discount Code و Gift Code
- احراز شماره و عضویت اجباری کانال
- راهنمای اتصال Android / iOS / Windows / macOS / Linux / TV با متن، عکس و ویدئو
- سؤال «از کجا با ما آشنا شدید؟»
- Follow-up خودکار بعد از پایان تست
- اعلان نزدیک اتمام حجم/زمان و پایان سرویس
- Multiple Admin
- Backup خودکار و دستی
- Groups: خریدها → `Customers` و Trial → `Trial`
- `/xuidiag`, `/groupsdiag`, `/notifydiag`

## CI و تست‌ها

هر Pull Request در GitHub Actions این موارد را بررسی می‌کند:

```text
Syntax: main.py + app.py + speedybot_v4/*.py
Unit Tests: Migration, Category, Blacklist, Audience, Feedback, Button payload
Shell syntax: install.sh + update.sh
VERSION.txt == 4.0.0
```

اگر CI قرمز است، PR را Merge نکنید.

## عیب‌یابی

اگر Bot جواب نمی‌دهد:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

خطای `401/403`: Bearer Token واقعی API را بررسی کنید.

خطای `404`: API URL، Base Path و Reverse Proxy را بررسی کنید.

اگر Subscription درست است ولی Address کانفیگ مستقیم غلط است، خروجی Bot را با **Copy URL** خود 3x-ui مقایسه کنید. اگر هر دو اشتباه‌اند، Share Address/Public Host در خود پنل باید اصلاح شود.

## امنیت

- `.env` را هرگز Commit نکنید.
- Bot Token و XUI API Token را در Issue نفرستید.
- Subscription URL، Direct Config، QR و Panel Snapshot را مثل Password در نظر بگیرید.
- برای پنل Public از HTTPS استفاده کنید.
- SSH را محدود و Ubuntu/3x-ui را به‌روز نگه دارید.
- `SECURITY.md` را بخوانید.

## ساختار پروژه

```text
SpeedyBot/
├── main.py             # هسته پایدار v3
├── app.py              # Entry point نسخه v4
├── speedybot_v4/       # قابلیت‌ها و UI ماژولار v4
├── tests/
├── install.sh
├── update.sh
├── requirements.txt
├── VERSION.txt
├── README.md
├── README_FA.md
├── CHANGELOG.md
└── RELEASE_NOTES_v4.0.0.md
```

## سازنده و لایسنس

پروژه تحت MIT License منتشر شده است.

ساخته و نگهداری‌شده توسط **SudoShayanNA**:

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- Repository: **https://github.com/roseshayan/SpeedyBot**

در Forkها و نسخه‌های توسعه‌یافته، حفظ Attribution و لینک سورس اصلی کمک می‌کند کاربران به مستندات، رفع باگ‌ها و آپدیت‌های امنیتی دسترسی داشته باشند.
