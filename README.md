# SpeedyBot v4.0.0

<p align="center">
  <strong>Open-source Telegram sales, subscription and CRM bot for 3x-ui / Sanaei</strong><br>
  Provisioning • Free Trial • Renewals • Wallet • Affiliate • Inbound routing • CRM • Connection guides • Control Center
</p>

<p align="center">
  <a href="README_FA.md">🇮🇷 راهنمای فارسی</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="MIGRATION_NOTES.md">Migration Guide</a> ·
  <a href="SECURITY.md">Security</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

> **Author / Maintainer:** **SudoShayanNA**  
> Telegram: **@SudoShayanNA** · Email: **namayandeshayan@gmail.com**  
> Official repository: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot turns Telegram into a practical storefront, self-service area and operations console for a **3x-ui / Sanaei** panel. It can provision clients after payment approval, issue free trials, renew services, deliver Subscription/direct links and QR codes, manage wallet/referral rewards, warn users about expiry, provide platform-specific connection guides, and give administrators a Telegram-first control center.

## Important: v4 is one integrated application

The final v4 release is **not** an add-on folder layered over an older release.

There is one production entrypoint:

```text
/root/SpeedyBot/main.py
```

The permanent Python package is:

```text
/root/SpeedyBot/speedybot/
```

The old development-only paths `app.py` and `speedybot_v4/` are not part of the final integrated layout. Installer, updater, systemd and manual runs all execute the same `main.py` entrypoint.

---

## Table of contents

- [Features](#features)
- [What v4 adds](#what-v4-adds)
- [Default plans](#default-plans)
- [Requirements](#requirements)
- [Before installation](#before-installation)
- [Step-by-step installation](#step-by-step-installation)
- [First-run checklist](#first-run-checklist)
- [Admin Control Center](#admin-control-center)
- [Operating modes](#operating-modes)
- [Plan categories](#plan-categories)
- [Free Trial and inbound routing](#free-trial-and-inbound-routing)
- [Per-user Trial overrides](#per-user-trial-overrides)
- [Connection guides](#connection-guides)
- [CRM and Trial follow-up](#crm-and-trial-follow-up)
- [Existing services and custom names](#existing-services-and-custom-names)
- [Payments, wallet and marketing](#payments-wallet-and-marketing)
- [Renewals](#renewals)
- [Groups](#groups)
- [Customer feedback](#customer-feedback)
- [Targeted broadcasts](#targeted-broadcasts)
- [Audit log](#audit-log)
- [Panel snapshot](#panel-snapshot)
- [Button styles and Custom Emoji](#button-styles-and-custom-emoji)
- [Notifications](#notifications)
- [Diagnostics](#diagnostics)
- [Updating](#updating)
- [Migrating from v3.x](#migrating-from-v3x)
- [Backups and rollback](#backups-and-rollback)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)
- [Security](#security)
- [License and author](#license-and-author)

---

## Features

### Sales and provisioning

- Automatic 3x-ui Client creation after payment approval.
- Free Trial by default: **1 GB / 1 day / 1 IP**.
- Dynamic SQLite-backed plans.
- Independent IP limit per plan.
- Manual card-transfer / receipt approval flow.
- Wallet checkout.
- Safe retry and idempotent provisioning behavior.
- Subscription URL delivery.
- Direct protocol-link delivery.
- Subscription QR code.
- Service renewal while preserving Client identity.
- Optional extra-volume packs for metered plans.

### Customer account

- Live service status.
- Remaining traffic / expiry visibility.
- Subscription and direct links.
- QR code.
- Renewal.
- Extra-volume purchase where supported.
- Purchase history.
- Wallet history.
- Gift and discount codes.
- Referral / affiliate link.
- Platform-specific connection guides.
- Secure linking of previously purchased 3x-ui services.
- Optional custom Client name.
- Customer rating / feedback.
- Optional phone verification.
- Optional mandatory Telegram-channel membership.

### Sales / CRM

- One-level referral program.
- Configurable cashback.
- Percentage or fixed discount codes.
- Gift-wallet codes.
- Acquisition survey after the first successful paid purchase.
- Automated follow-up after Trial expiry.
- Structured reasons for not purchasing.
- Purchase/support CTA after follow-up.
- Targeted broadcast audiences.
- Customer feedback analytics.

### Administration

From `/sudoadmin` you can manage:

- Plans and prices.
- Plan categories.
- Volume packs.
- Trial enable/disable.
- Trial and per-plan inbounds.
- Per-user Trial overrides.
- Sanaei Client Groups.
- CRM and Trial follow-up.
- Wallet and referrals.
- Cashback, gift and discount codes.
- Payment/card information.
- Welcome and FAQ text.
- Phone verification and channel membership.
- Multiple admins.
- Notifications.
- Backups.
- User restrictions / blacklist.
- Operating mode.
- Customer feedback.
- Targeted broadcasts.
- Audit Log.
- Read-only panel snapshot.
- Telegram button styles and Custom Emoji IDs.

---

## What v4 adds

### Cleaner Control Center

The admin UI is reorganized into clearer sections with shorter, more readable messages and less crowded menus.

### Operating modes

- `NORMAL` — normal operation.
- `SALES_PAUSED` — new purchases, renewals and volume add-ons are blocked; account, guides and support remain available.
- `MAINTENANCE` — purchases and new Trials are blocked; account, guides and support remain available.

### Blacklist / purchase restriction

Admins can restrict a Telegram user from purchase/Trial actions and store a reason. Support and account visibility remain available so the user is not silently locked out of help.

### Plan categories

Plans can be grouped into categories such as:

```text
Germany
Gaming
Anti-Sanction
Static IP
Business
```

Existing uncategorized plans are migrated into a default `عمومی` category.

### Per-user Trial override

Before the first Trial, an admin can define custom Trial traffic, days and IP limit for a specific Telegram ID.

### Feedback

Users can submit 1–5 stars plus an optional comment. Admin analytics show total responses, average rating, distribution and recent comments.

### Targeted broadcast

Broadcast can target:

- All active users.
- Paying customers.
- Trial users who did not purchase.
- Expired-Trial users who did not purchase.
- Users who never purchased.

### Audit Log

Important admin events are stored in SQLite and can optionally be mirrored to a private Telegram group/channel.

### Panel Snapshot

Admin can export a read-only JSON snapshot of 3x-ui clients for investigation/disaster-recovery preparation. Automatic destructive restore is intentionally not included.

### Telegram button styles / Custom Emoji

SpeedyBot supports Telegram's official button styles:

```text
default
primary
success
danger
```

Telegram does not expose arbitrary HEX/RGB button colors to bots.

Custom/Premium Emoji IDs are optional and fall back safely when Telegram does not allow them.

---

## Default plans

Fresh databases receive these seed plans:

| Plan | Duration | Traffic | IP limit | Default price |
|---|---:|---:|---:|---:|
| Unlimited - 1 user | 30 days | Unlimited | 1 | 250,000 Toman |
| Unlimited - 2 users | 30 days | Unlimited | 2 | 300,000 Toman |
| Unlimited - 3 users | 30 days | Unlimited | 3 | 350,000 Toman |

These are examples/default seeds. Review them from `/sudoadmin` before production sales.

---

## Requirements

Recommended production setup:

- Ubuntu **24.04 LTS**.
- Python 3.12.
- Current 3x-ui / Sanaei with `/panel/api/*` API.
- Bearer API Token from 3x-ui.
- Telegram Bot Token from `@BotFather`.
- Numeric Telegram ID for the Owner.
- Working Subscription service if Subscription URLs are used.
- Outbound connectivity from the VPS to Telegram and the panel.

SpeedyBot uses Long Polling, so no Telegram webhook port is required.

---

## Before installation

### 1. Create the Telegram bot

In `@BotFather`:

1. Send `/newbot`.
2. Choose a display name.
3. Choose a username ending in `bot`.
4. Copy and securely store the Bot Token.

Never publish the token in a GitHub Issue, screenshot, README, log or commit.

### 2. Find the Owner Telegram ID

You need the **numeric Telegram user ID**, not the username. This becomes the initial `ADMIN_ID` and Owner account.

### 3. Create a 3x-ui Bearer API token

Inside 3x-ui:

```text
Settings → Security → API Token
```

Create a token and save the **plaintext Token value**.

The following are not the Bearer Token:

- Token display name.
- Panel password.
- Hidden web path.

### 4. API URL vs Base Path

If the panel opens at:

```text
https://panel.example.com:2053/secret-panel/
```

Installer values should normally be:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

If there is no hidden path:

```text
X-UI security base path: /
```

Do not duplicate the hidden path inside the base URL.

### 5. Subscription settings

If a real user Subscription URL looks like:

```text
https://sub.example.com:2096/sub/ABC123
```

enter:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

Use the actual path configured in your 3x-ui installation.

---

## Step-by-step installation

Log in as `root`:

```bash
apt update
apt install -y git

git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

The Installer asks for:

1. Telegram Bot Token.
2. Telegram Admin numeric ID.
3. X-UI API base URL.
4. X-UI security base path.
5. Panel Bearer API Token.
6. Subscription server base URL.
7. Subscription URI path.

Before systemd is enabled, Installer performs a **read-only 3x-ui API preflight**. Authentication/base-path mistakes are caught before the bot is considered installed.

### Runtime files

Important mutable runtime state:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/.venv/
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/run.sh
/root/SpeedyBot/backups/
```

The systemd service is:

```text
xui-bot.service
```

The runner executes:

```text
/root/SpeedyBot/main.py
```

### Service status

```bash
systemctl status xui-bot.service --no-pager -l
```

### Live logs

```bash
journalctl -u xui-bot.service -f
```

### Restart

```bash
systemctl restart xui-bot.service
```

---

## First-run checklist

From the Owner account:

```text
/start
/sudoadmin
```

Before accepting real customers:

1. Replace example payment/card data.
2. Verify plan prices, duration, traffic and IP limits.
3. Create/review plan categories.
4. Review Trial & Inbounds.
5. Enable/disable Trial as required.
6. Select inbounds for Trial and each plan.
7. Reconcile `Customers` and `Trial` groups.
8. Create Android/iOS/Windows/macOS/Linux/TV connection guides.
9. Review CRM and Trial follow-up.
10. Configure verification/channel membership if required.
11. Confirm operating mode is `NORMAL`.
12. Review button styles.
13. Configure Audit Chat only if needed.
14. Run `/xuidiag`.
15. Run `/groupsdiag`.
16. Run `/notifydiag`.
17. Test one real Trial.
18. Test one complete purchase flow before heavy production use.

---

## Admin Control Center

Main command:

```text
/sudoadmin
```

Useful diagnostics:

```text
/xuidiag
/groupsdiag
/notifydiag
```

- `/xuidiag` — read-only panel API diagnostics.
- `/groupsdiag` — live Client Group counts.
- `/notifydiag` — run the service monitor once.

---

## Operating modes

### NORMAL

All configured functions are available.

### SALES_PAUSED

New purchase, renewal and volume-add actions are blocked while Account, Guide and Support remain available.

### MAINTENANCE

New purchase and Trial issuance are blocked while existing-account visibility, Guide and Support remain available.

---

## Plan categories

Create categories from `/sudoadmin`, then move Plan IDs to the appropriate category. Existing uncategorized plans are assigned to `عمومی` during migration.

---

## Free Trial and inbound routing

From:

```text
/sudoadmin → Trial & Inbounds
```

admins can:

- Enable/disable Trial.
- Select exact Trial inbounds.
- Select exact inbounds independently for each plan.
- Reset a scope to all active inbounds.

If a scope has no explicit inbound rows, SpeedyBot uses **all active inbounds** for backward compatibility.

### Direct config vs Subscription

Direct proxy links are kept separate from Subscription URLs.

Direct-link schemes can include:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

HTTP/HTTPS Subscription URLs are shown only as Subscription links.

If a Direct Address is wrong, compare it with 3x-ui **Copy URL**. If both contain the same wrong host, fix the Inbound Share Address/Public Host in 3x-ui.

---

## Per-user Trial overrides

Before a user's first Trial, an admin can enter:

```text
TelegramID | VolumeGB | Days | IPLimit | Optional note
```

Example:

```text
123456789 | 5 | 3 | 2 | VIP lead
```

The normal Trial Inbound selection still applies.

---

## Connection guides

Admins can create platform-specific guides for:

- Android.
- iPhone / iOS.
- Windows.
- macOS.
- Linux.
- Android TV / TV Box.

Guide items can be:

- Text.
- Photo + caption.
- Video + caption.

Telegram `file_id` values are stored instead of copying media binaries into SQLite.

---

## CRM and Trial follow-up

### Acquisition survey

After the first successful paid purchase, SpeedyBot can ask how the user found the service. Default choices include friend recommendation, Telegram search, channel ads, Instagram, web/search, returning customer and other.

### Trial follow-up

After Trial expiry/exhaustion, the bot can wait for the configured delay, check whether the user already purchased, and only follow up non-buyers.

Reasons can include quality, price, setup difficulty, buying later, no current need, ready to buy, or other. Responses can lead to purchase/support CTAs.

This CRM path can operate independently from normal expiry-warning messages.

---

## Existing services and custom names

### Custom Client name

When enabled, buyers can choose a custom Client name.

Rules:

- 3–40 characters.
- ASCII letters/numbers plus `.`, `_`, `-`.
- Checked against local SpeedyBot data.
- Checked against the connected 3x-ui panel before checkout.

### Link a previously purchased service

A user can enter an existing 3x-ui Client email/name from Account.

Ownership rules:

- Matching panel `tgId` → automatic claim.
- Non-matching `tgId` → admin approval required.
- One panel Client can be linked to only one SpeedyBot account.

---

## Payments, wallet and marketing

### Manual/card payment

The bot shows configured payment data, receives a receipt and waits for admin approval before provisioning.

### Wallet

- Balance.
- Ledger/history.
- Admin credit/debit.
- Wallet checkout.

### Affiliate

- Permanent Telegram referral link.
- Referrer stored on first registration.
- Commission after qualifying approved/provisioned purchase.
- Exactly-once commission protection.

### Cashback / Discount / Gift

Admins can configure cashback, percentage/fixed discount codes, minimum purchase, expiry/usage limits and wallet-credit Gift Codes.

---

## Renewals

Renewal keeps the same service identity and:

- Preserves remaining time on early renewal.
- Updates quota/IP limit for the selected plan.
- Re-enables the Client.
- Resets traffic for the new period.
- Synchronizes the Client to the renewal plan's configured inbounds.

---

## Groups

Default mapping:

```text
Paid service → Customers
Free Trial   → Trial
```

Live check:

```text
/groupsdiag
```

---

## Customer feedback

Users can submit 1–5 stars plus an optional comment. Admin sees total feedback, average rating, distribution and recent comments. The feature can be disabled.

---

## Targeted broadcasts

Available audiences include all active users, paying customers, Trial leads, expired-Trial leads and never-purchased users.

Telegram `copy_message` is used so text/photo/video/document messages can be reused. Always test a small audience before sending to everyone.

---

## Audit log

Important operations are stored in SQLite. An optional private Telegram Chat ID can receive mirrored events if the bot has permission to post there.

---

## Panel snapshot

A read-only JSON export can be generated from the connected 3x-ui panel. Snapshot files contain sensitive service data and must not be posted publicly.

---

## Button styles and Custom Emoji

Supported styles:

```text
default
primary
success
danger
```

For Custom Emoji, use `/emojiid` to obtain the ID, configure it from Admin, then run the built-in eligibility test before enabling it broadly.

---

## Notifications

The service monitor can send one-time events for:

- Traffic warning near 90%.
- Paid-service expiry warning.
- Trial expiry warning.
- Traffic exhausted.
- Time expired.

Notification claims are stored in SQLite so restarts do not intentionally duplicate the same event.

---

## Diagnostics

### Bot does not respond

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 200 --no-pager
```

### 401 / 403

Verify the **plaintext Bearer API Token**. Do not use the Token name or panel password.

### 404

Verify:

- API Base URL.
- Hidden Base Path.
- Reverse-proxy routing.
- Panel API availability/version.

Example:

```text
Panel: https://panel.example.com:2053/secret/
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Duplicate bot processes

```bash
systemctl show xui-bot.service -p NRestarts
pgrep -af 'python.*main.py'
```

Only the systemd-managed process should normally use the production Bot Token.

---

## Updating

The updater synchronizes the **complete repository**, not a hand-maintained list of files.

### Check

```bash
cd /root/SpeedyBot
./update.sh --check
```

### Update

```bash
./update.sh
```

### Force redeploy

```bash
./update.sh --force
```

### What the updater does

1. Re-executes itself from `/tmp` so it can safely replace its own file.
2. Resolves the current GitHub branch commit.
3. Clones the complete repository into a temporary directory.
4. Validates `main.py`, every `speedybot/*.py`, `install.sh` and `update.sh`.
5. Installs dependencies before downtime.
6. Stops the systemd service.
7. Creates a complete rollback copy of the deployed application.
8. Backs up `.env` and SQLite DB/WAL/SHM.
9. Uses `rsync --delete` to make `/root/SpeedyBot` match the published repository.
10. Preserves `.env`, `.venv/`, SQLite runtime files, `backups/`, `run.sh` and `.deployed_commit`.
11. Rewrites `run.sh` to execute `main.py`.
12. Restarts systemd and checks service health / immediate restart loops.
13. Restores the previous complete application if deployment fails.

Because `--delete` is used for source synchronization, old version-specific files are removed automatically when they no longer exist in GitHub.

---

## Migrating from v3.x

Do **not** delete `.env` or `speedping.db`.

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

After upgrade:

```bash
cat VERSION.txt
cat run.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

Expected version:

```text
4.0.0
```

Expected runner target:

```text
/root/SpeedyBot/main.py
```

The v4 database migration is additive and preserves existing business data.

Read [MIGRATION_NOTES.md](MIGRATION_NOTES.md) before a major production upgrade.

---

## Backups and rollback

Deployment backups are stored under:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

Important runtime state:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

For real production, periodically copy backups to another machine/storage provider.

---

## Project layout

```text
SpeedyBot/
├── main.py                    # single production entrypoint
├── speedybot/                 # integrated application package
│   ├── __init__.py
│   ├── core.py                # sales/provisioning business core
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

No release-numbered application folder is used.

---

## Security

- Never commit `.env`.
- Never publish Telegram Bot Tokens or 3x-ui API Tokens.
- Treat Subscription URLs, Direct Configs and QR codes as credentials.
- Treat Panel Snapshot files as sensitive.
- Keep Ubuntu, SSH and 3x-ui updated.
- Use TLS for externally exposed panel/subscription endpoints.
- Existing-service claims require matching `tgId` or explicit admin approval.
- Redact secrets before posting logs in Issues.

See [SECURITY.md](SECURITY.md).

---

## License and author

Licensed under the **MIT License**.

Created and maintained by **SudoShayanNA**.

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- Repository: **https://github.com/roseshayan/SpeedyBot**

If you redistribute or build on SpeedyBot, keeping a link to the original repository helps users find maintained documentation, security updates and future releases.
