# SpeedyBot

ربات متن‌باز فروش و مدیریت اشتراک **3x-ui (سنایی)** در تلگرام. از دریافت رسید و ساخت سرویس تا تحویل لینک، تمدید و پشتیبانی را در تلگرام مدیریت کن.

[وب‌سایت و راهنمای کامل](https://roseshayan.github.io/SpeedyBot/) · [English](README.md) · [تغییرات نسخه‌ها](CHANGELOG.md) · [مجوز MIT](LICENSE)

## نصب سریع

**پیش‌نیازها** شامل یک VPS لینوکسی با systemd و Python 3.11 یا بالاتر (Ubuntu 24.04 LTS پیشنهاد می‌شود)، پنل 3x-ui راه‌اندازی‌شده با یک Inbound فعال، توکن ربات از [BotFather](https://t.me/BotFather)، شناسهٔ عددی حساب مدیر و توکن API از **3x-ui ← Settings ← Security ← API Token** هستند. سرور باید بتواند به تلگرام و پنل وصل شود.

برای نصب تازه ابتدا با `sudo -i` وارد حساب root شو و دستورهای زیر را اجرا کن.

```bash
apt update
apt install -y git
git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
bash install.sh
```

| ورودی نصب‌کننده | مقدار |
| --- | --- |
| توکن ربات و Admin ID | توکن BotFather و شناسهٔ عددی حساب مدیر |
| آدرس API و Base Path | برای `https://panel.example.com:2053/private/` به‌ترتیب `https://panel.example.com:2053` و `/private` را وارد کن. اگر مسیر مخفی نداری از `/` استفاده کن. |
| Bearer Token پنل | خودِ مقدار توکن API که در 3x-ui ساخته‌ای |
| آدرس و مسیر Subscription | برای `https://sub.example.com:2096/sub/abc` به‌ترتیب `https://sub.example.com:2096` و `/sub/` را جدا وارد کن. مقادیر واقعی پنل خودت را جایگزین کن. |

نصب‌کننده API پنل را بررسی می‌کند و سرویس `xui-bot.service` را بالا می‌آورد. وضعیت را با `systemctl status xui-bot.service --no-pager` ببین. در تلگرام با حساب مالک `/start` و سپس `/sudoadmin` را بزن. اطلاعات واریز، پلان‌ها و Inboundها را تنظیم کن و قبل از دریافت وجه، یک تست و یک خرید آزمایشی انجام بده.

[آموزش کامل نصب](https://roseshayan.github.io/SpeedyBot/#install) · [راهنمای پنل ادمین](https://roseshayan.github.io/SpeedyBot/#admin) · [رفع خطا](https://roseshayan.github.io/SpeedyBot/#troubleshooting)

## امکانات

| بخش | امکانات |
| --- | --- |
| فروش | ساخت و تمدید سرویس، تأیید رسید، خرید از کیف پول و فروش حجم اضافه |
| حساب مشتری | مشاهدهٔ مصرف، لینک سابسکریپشن و کانفیگ مستقیم، QR و راهنمای اتصال |
| پنل مدیریت | تنظیم تست و Inbound، احراز و عضویت، کدهای پاداش، CRM، اعلان و بکاپ |

## به‌روزرسانی نصب فعلی

دستورهای زیر را با حساب root اجرا کن.

```bash
cd /root/SpeedyBot
bash update.sh --check
bash update.sh
```

به‌روزرسان نسخهٔ تازه را قبل از جایگزینی تست می‌کند، هنگام همگام‌سازی کد از `.env` و دیتابیس فعلی محافظت می‌کند و اگر سرویس بالا نیاید برای بازگردانی نسخهٔ قبلی تلاش می‌کند. [یادداشت‌های مهاجرت](MIGRATION_NOTES.md) · [بکاپ و بازیابی](https://roseshayan.github.io/SpeedyBot/#operations)

توکن‌ها، کانفیگ مشتریان و بکاپ دیتابیس را خصوصی نگه دار. [امنیت](SECURITY.md) · [پشتیبانی](SUPPORT.md) · [مشارکت](CONTRIBUTING.md)

نگه‌دارندهٔ پروژه [SudoShayanNA](AUTHOR.md) است.
