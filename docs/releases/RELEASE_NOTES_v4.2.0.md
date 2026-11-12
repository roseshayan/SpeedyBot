# SpeedyBot v4.2.0 — Linked Renewals & Operator Reliability

This release focuses on installed-bot operations: renewal of claimed services, quieter panel monitoring, an admin VPS referral surface, and automatic update notifications.

## Added

- Existing/claimed services can now be renewed from the customer account using the same card and wallet `RENEWAL` pipeline as bot-created services.
- Linked-service renewal applies the selected plan duration, traffic and IP limit directly to the claimed 3x-ui client.
- Automatic GitHub update checks against `main/VERSION.txt`.
- Bot admins receive one Telegram notification per newer published version, including the normal `./update.sh` upgrade command.
- New `☁️ سرور مجازی ساعتی` entry in the admin panel with the developer's disclosed Doprax referral link.
- Doprax referral copy mentions hourly VPS locations and the advertised Rial-payment option.

## Improved

- Service-monitor DNS/network alerts no longer fire on the first transient failure.
- Panel connectivity alerts require 3 consecutive failures by default.
- Repeated connectivity alerts use a 6-hour cooldown by default.
- DNS resolution failures are converted into a concise actionable message instead of repeatedly forwarding the full Requests exception.
- After an alerted outage recovers, admins receive one recovery notification.
- GitHub update-check failures are silent and never affect the bot runtime.

## Default settings

- `monitor_alert_after_failures=3`
- `monitor_alert_cooldown_seconds=21600`
- `monitor_recovery_notifications=1`
- `update_notifications_enabled=1`
- `update_check_interval_seconds=21600`

## Customer path

`حساب کاربری → سرویس متصل‌شده → ♻️ تمدید همین سرویس`

## Admin path

`/sudoadmin → ☁️ سرور مجازی ساعتی`

## Update

From the project directory:

```bash
./update.sh
```
