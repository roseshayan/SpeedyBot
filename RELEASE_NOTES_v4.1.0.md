# SpeedyBot v4.1.0 — White-label, Linked Renewals & Operator Improvements

This release makes customer-facing deployments easier to white-label, gives operators control over the customer menu, and improves day-to-day operation of installed bots.

## Added

- White-label brand name setting, managed directly from the Telegram admin panel.
- New **Brand & Customer Menu** admin section.
- Independent visibility controls for buy, account, free trial, affiliate, connection guide, FAQ/help, gift/discount code, feedback/rating and support.
- One-click reset to show all customer menu buttons again.
- Customer menu rows are rebuilt dynamically so hidden buttons do not leave empty gaps.
- Existing/claimed services can now be renewed from the customer account using the same card and wallet renewal pipeline as bot-created services.
- Linked-service renewal applies the selected plan duration, volume and IP limit directly to the claimed 3x-ui client.
- Automatic GitHub update checks. When `VERSION.txt` on the main repository is newer than the installed version, bot admins receive a one-time Telegram notification for that version with the normal `./update.sh` upgrade command.
- New **Hourly VPS** admin entry with the developer's disclosed Doprax referral link for operators who need a VPS in different locations, including the advertised Rial-payment option.

## Changed

- The admin Control Center title now uses the configured brand instead of a hard-coded SpeedyBot title.
- The categorized storefront title now uses the configured brand instead of `SpeedPing`.
- Hiding the feedback/rating entry also removes it from the account screen and blocks stale feedback callbacks.
- Untouched legacy `SpeedPing` welcome/FAQ defaults are migrated to neutral white-label copy during upgrade.
- Admin-customized welcome and FAQ text is preserved by the migration.
- Service-monitor connectivity alerts are debounced. A transient DNS/network failure no longer alerts on the first failed check; the monitor waits for consecutive failures and applies a cooldown before repeating the alert.
- DNS resolution failures are summarized with an actionable message instead of forwarding a large Requests exception every time.
- After an alerted panel outage recovers, admins receive one recovery notification.

## Default operational settings

- Monitor alert threshold: `3` consecutive failures.
- Monitor alert cooldown: `21600` seconds (6 hours).
- Recovery notifications: enabled.
- GitHub update notifications: enabled.
- GitHub update check interval: `21600` seconds (6 hours, minimum runtime clamp: 1 hour).

## Upgrade notes

After updating, open:

`/sudoadmin → 🏷 برند و منوی مشتری`

To renew a claimed service, users can open:

`حساب کاربری → سرویس متصل‌شده → ♻️ تمدید همین سرویس`

The existing full feedback feature switch remains available under **Customer Feedback**. Menu visibility and feature enablement are intentionally separate controls.

Update notifications are advisory only. If GitHub is temporarily unreachable, the background check fails silently and never affects the bot runtime.
