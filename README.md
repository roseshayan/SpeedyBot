# SpeedyBot v3.0.0

> A production-oriented Telegram sales and service-management bot for **3x-ui / Sanaei**.
>
> **Author:** [SudoShayanNA](https://github.com/roseshayan) · [Telegram](https://t.me/SudoShayanNA) · `namayandeshayan@gmail.com`

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](VERSION.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420.svg)](https://ubuntu.com/)
[![3x-ui](https://img.shields.io/badge/3x--ui-Sanaei-2ea44f.svg)](https://github.com/MHSanaei/3x-ui)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Persian documentation:** [README_FA.md](README_FA.md)

---

## What is SpeedyBot?

SpeedyBot connects a Telegram bot to a **3x-ui / Sanaei** panel and automates the routine work involved in selling and managing VPN subscriptions. Customers can buy plans, receive a trial, view their services, renew existing subscriptions, use a wallet, apply discount/gift codes, participate in referrals, and receive expiry/traffic notifications.

The bot stores its own business data in **SQLite**, talks to 3x-ui through the official `/panel/api/*` REST API using a **Bearer API Token**, and runs as a **systemd** service on Ubuntu.

This repository is designed for self-hosting. Payment in the current public version is based on **manual card-to-card receipt approval and wallet balance**; it does not pretend to include an online payment gateway that is not configured.

---

## Table of contents

- [Features](#features)
- [Default plans](#default-plans)
- [How the sales flow works](#how-the-sales-flow-works)
- [Requirements](#requirements)
- [Before installation](#before-installation)
- [Installation](#installation)
- [Installer questions explained](#installer-questions-explained)
- [First run checklist](#first-run-checklist)
- [Admin commands](#admin-commands)
- [Sanaei groups](#sanaei-groups)
- [Service renewal](#service-renewal)
- [Wallet, referral and marketing tools](#wallet-referral-and-marketing-tools)
- [Notifications](#notifications)
- [Configuration](#configuration)
- [Updating](#updating)
- [Backups](#backups)
- [Useful server commands](#useful-server-commands)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [Author](#author)
- [License](#license)

---

## Features

### Sales and service provisioning

- Automated paid-client creation on active 3x-ui inbounds.
- One-time **1 GB / 1 day** free trial per Telegram user ID.
- Dynamic plans stored in SQLite and editable from the Telegram admin panel.
- Dynamic `limitIp` based on the selected user/device count.
- Existing-service renewal without replacing the subscription identity.
- Optional extra-volume packages for metered plans.
- Subscription links, direct configuration links and QR code delivery.
- Retry/recovery handling for partially completed service issuance.
- Service history and live service-status display.

### Sanaei / 3x-ui integration

- Bearer Token authentication against `/panel/api/*` endpoints.
- Paid clients are assigned to the `Customers` group.
- Trial clients are assigned to the `Trial` group.
- Missing required groups can be created automatically.
- Existing bot-created services can be reconciled with the expected groups.
- Read-only API diagnostics with `/xuidiag`.
- Live group diagnostics with `/groupsdiag`.

### User experience

- Telegram-native menus; no external dashboard is required for basic operation.
- Account page with purchased services.
- Renew service.
- Retrieve subscription and configuration links again.
- Wallet and wallet history.
- Purchase/renewal history.
- Referral link and affiliate statistics.
- Discount code and gift code support.
- Editable welcome text and FAQ.
- Optional phone-number verification.
- Optional mandatory Telegram-channel membership for purchases.

### Growth and marketing

- One-level affiliate/referral system.
- Configurable referral commission percentage.
- Cashback.
- Percentage or fixed-amount discount codes.
- Discount restrictions such as expiry, minimum order, total usage and per-user usage.
- Gift codes for wallet credit.

### Administration

- Telegram admin dashboard through `/sudoadmin`.
- Dynamic plan management.
- Extra-volume package management.
- User wallet adjustments.
- Referral statistics and settings.
- Cashback, discount and gift-code management.
- Multiple bot administrators; the configured `ADMIN_ID` remains the owner.
- Editable welcome/FAQ content.
- Configurable service username generation.
- Sales analytics.
- Manual and automatic SQLite backups.
- Service expiry/quota monitoring.
- GitHub updater with validation, backup, health check and rollback.

---

## Default plans

On a fresh database, SpeedyBot creates these starter plans:

| Plan | Duration | Traffic | IP / user limit | Price |
|---|---:|---:|---:|---:|
| Unlimited monthly · 1 user | 30 days | Unlimited | `1` | 250,000 Toman |
| Unlimited monthly · 2 users | 30 days | Unlimited | `2` | 300,000 Toman |
| Unlimited monthly · 3 users | 30 days | Unlimited | `3` | 350,000 Toman |

These are only defaults. You can add, edit, reorder, enable or disable plans from the admin panel.

---

## How the sales flow works

1. The customer opens the bot and chooses a plan.
2. SpeedyBot calculates the plan price and any applicable discount/wallet amount.
3. For manual card payment, the customer submits a payment receipt.
4. An administrator reviews and approves the transaction.
5. SpeedyBot creates the client in 3x-ui using the selected plan's traffic, expiry and `limitIp` values.
6. The client is added to the `Customers` group.
7. The customer receives subscription/configuration links and a QR code when available.
8. If the customer was referred by another user, eligible referral commission is credited exactly once after a successful cash-backed purchase.
9. The service monitor later warns about approaching quota/expiry and notifies the customer when the service expires.

Free trials follow a separate flow and are assigned to the `Trial` group. Trial issuance does not generate referral commission.

---

# Requirements

## Server

Recommended:

- Ubuntu **24.04 LTS**
- Root access
- Internet access to Telegram and GitHub
- Python 3.10+ (Ubuntu 24.04 provides Python 3.12)
- A working Sanaei / 3x-ui installation with the current `/panel/api/*` API

The bot server and the 3x-ui server may be the same machine or different machines. The bot only needs network access to the panel API URL.

## Telegram

You need:

- A Telegram bot token from **@BotFather**.
- Your numeric Telegram user ID to become the owner/admin.

## 3x-ui / Sanaei

You need:

- Panel base URL, for example `https://panel.example.com:2053`.
- Web/security base path, for example `/my-secret-path`, or `/` when no base path is configured.
- A **plaintext Bearer API Token** created in the panel.
- Subscription server base URL, for example `https://sub.example.com:2096`.
- Subscription URI path, normally `/sub/` unless you changed it in 3x-ui.

> **Important:** the API token value is not the same thing as the token name, panel password, or web base path. Save the plaintext token when you create it.

---

# Before installation

## Step 1 — Create the Telegram bot

1. Open Telegram and start **@BotFather**.
2. Send `/newbot`.
3. Choose a display name.
4. Choose a username ending in `bot`.
5. Copy the API token BotFather gives you.
6. Keep this token private.

Example token format:

```text
123456789:AAExampleTelegramBotToken
```

Do **not** put your real token in GitHub issues, screenshots, README files or public chat messages.

## Step 2 — Find your Telegram numeric ID

Use a trusted Telegram ID bot or another method to obtain your numeric user ID. It looks like:

```text
123456789
```

This value becomes `ADMIN_ID`. The initial `ADMIN_ID` is the owner and can manage additional bot admins later.

## Step 3 — Create a 3x-ui API Token

In a recent Sanaei / 3x-ui panel:

1. Open **Settings**.
2. Go to **Security**.
3. Open **API Token** management.
4. Create a new token.
5. Copy the **plaintext token value** immediately.
6. Store it securely.

The installer uses this value as:

```text
XUI_BEARER_TOKEN
```

If you only copied the token's name, API requests will fail with `401` or `403`.

## Step 4 — Determine the panel URL and base path

If the browser URL is:

```text
https://panel.example.com:2053/my-secret-path/
```

then enter:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /my-secret-path
```

Do not include the path in the API base URL.

If there is no web base path, use:

```text
/
```

## Step 5 — Check subscription settings

In 3x-ui, verify the Subscription service is enabled and note:

- Subscription host/domain and port.
- Subscription URI/path.

For a final subscription link like:

```text
https://sub.example.com:2096/sub/XXXXXXXX
```

the installer values are:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

---

# Installation

## Method A — Git clone (recommended)

Login to the Ubuntu server as root:

```bash
ssh root@YOUR_SERVER_IP
```

Install Git if necessary:

```bash
apt update
apt install -y git
```

Clone SpeedyBot:

```bash
git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

The installer will ask you for the Telegram and 3x-ui settings, install Python dependencies, create `/root/SpeedyBot/.env`, validate the 3x-ui API, create a Python virtual environment and install a systemd service named:

```text
xui-bot.service
```

## Method B — GitHub ZIP

If you downloaded the source archive instead:

```bash
apt update
apt install -y unzip git
cd /root
unzip SpeedyBot-*.zip
```

Move/rename the extracted directory to `/root/SpeedyBot`, then:

```bash
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

Git is still recommended because the built-in updater downloads future versions from the public GitHub repository.

---

# Installer questions explained

The installer prompts are intentionally strict to catch common configuration mistakes.

### `Telegram bot token`

Paste the exact BotFather token.

### `Telegram admin numeric ID`

Paste the owner's numeric Telegram ID, not a username such as `@example`.

### `X-UI API base URL`

Correct:

```text
https://panel.example.com:2053
```

Incorrect:

```text
https://panel.example.com:2053/secret-path
```

### `X-UI security base path`

Examples:

```text
/
```

or:

```text
/secret-path
```

The value must begin with `/`.

### `Panel Bearer API Token`

Paste the plaintext API token generated in 3x-ui. Do not enter the API token name or the web base path.

### `Subscription server base URL`

Example:

```text
https://sub.example.com:2096
```

Do not append `/sub` here.

### `Subscription URI path`

Usually:

```text
/sub/
```

If you changed the subscription URI in Sanaei, enter the same value here.

---

# First run checklist

After installation:

```bash
systemctl status xui-bot.service --no-pager -l
```

You want to see:

```text
Active: active (running)
```

Follow logs:

```bash
journalctl -u xui-bot.service -f
```

Then open your Telegram bot and send:

```text
/start
```

From the owner account, verify:

```text
/xuidiag
/groupsdiag
/notifydiag
/sudoadmin
```

Recommended first checks:

1. `/xuidiag` returns HTTP 200 / success.
2. `/groupsdiag` can read Sanaei groups.
3. `Customers` and `Trial` exist or can be reconciled.
4. Open `/sudoadmin` and review the default plan catalog.
5. Set your real bank/card details before accepting orders.
6. Review referral/cashback settings.
7. Test a purchase with a controlled account.
8. Test a free trial with another Telegram account.

---

# Admin commands

| Command | Purpose |
|---|---|
| `/sudoadmin` | Main administration menu |
| `/xuidiag` | Read-only 3x-ui API connectivity/authentication diagnostic |
| `/groupsdiag` | Show live Sanaei group information and counts |
| `/notifydiag` | Run service-notification monitor diagnostics |

Most day-to-day management is performed using buttons inside `/sudoadmin` rather than raw commands.

---

# Sanaei groups

SpeedyBot uses 3x-ui client groups to keep the panel organized:

- `Customers` — paid services.
- `Trial` — free-trial services.

The bot can create missing required groups and reconcile known bot-created services. This keeps trial users separate from paying customers without requiring you to manually move every client in the panel.

Use:

```text
/groupsdiag
```

to inspect the live group list and client counts returned by your own panel.

---

# Service renewal

Renewal updates the existing client instead of creating an unrelated second subscription.

The customer can select a renewal plan from the account/service page. Depending on the selected plan, SpeedyBot can update:

- Expiry.
- Traffic quota.
- `limitIp` / user count.
- Enabled state.
- Traffic counters for the new period where applicable.

When renewing before the current expiry, the system is designed to preserve remaining validity rather than intentionally discarding paid time.

---

# Wallet, referral and marketing tools

## Wallet

Users have an internal balance stored in SQLite. Every wallet adjustment is written to a ledger so balance changes can be audited.

The admin can credit/debit balances from the management panel. Eligible purchases can also be paid using wallet balance.

## Referral / affiliate

Each user can obtain a permanent referral link. A referrer is bound only under the configured referral rules and self-referral is rejected.

Commission is credited after an eligible **successful cash-backed purchase** and duplicate commission on the same transaction is prevented.

## Cashback

Cashback can be enabled and configured from the admin panel.

## Discount codes

Discount codes can support percentage or fixed discounts with controls such as minimum order, expiry, usage limit and per-user restrictions.

## Gift codes

Gift codes credit user wallet balances and can be enabled/disabled by admins.

---

# Notifications

By default the service monitor checks services periodically and can send one-time notifications for important events.

Typical defaults include:

- Warning at **90%** quota consumption.
- Paid-service expiry warning **24 hours** before expiry.
- Trial expiry warning **3 hours** before expiry.
- Notification when quota is exhausted.
- Notification when time validity expires.

Notification events are stored so restarting the bot does not repeatedly send the same alert.

Use `/notifydiag` to run diagnostics.

---

# Configuration

Runtime secrets are stored in:

```text
/root/SpeedyBot/.env
```

A non-secret example is available in [.env.example](.env.example).

Main environment variables:

```bash
BOT_TOKEN='...'
ADMIN_ID='123456789'
XUI_API_URL='https://panel.example.com:2053'
XUI_BASE_PATH='/secret-path'
XUI_BEARER_TOKEN='...'
XUI_SUB_SERVER_URL='https://sub.example.com:2096'
XUI_SUB_PATH='/sub/'
```

After manually changing `.env`:

```bash
systemctl restart xui-bot.service
```

Business settings such as plans, bank/card information, referral settings, cashback, notification thresholds and many admin options are stored in SQLite and managed from `/sudoadmin`.

---

# Updating

SpeedyBot includes a GitHub-based updater.

Check whether GitHub has a different commit:

```bash
cd /root/SpeedyBot
./update.sh --check
```

Install the latest `main` version:

```bash
cd /root/SpeedyBot
./update.sh
```

Force redeployment of the latest commit:

```bash
./update.sh --force
```

The updater is designed to:

1. Download the latest public GitHub source.
2. Validate Python and shell syntax before touching the running bot.
3. Install/update dependencies before downtime where possible.
4. Stop the service for a consistent SQLite backup.
5. Backup runtime state and the currently deployed source.
6. Deploy the new source.
7. Restart the service.
8. Perform a health check.
9. Roll back to the previous source/database if deployment fails.

Do not edit or delete `.env` during an update.

---

# Backups

SpeedyBot supports application-level SQLite backups and the updater also creates deployment backups.

Important runtime files:

```text
/root/SpeedyBot/speedping.db
/root/SpeedyBot/.env
/root/SpeedyBot/backups/
```

For an external/manual server backup, stop the service first for maximum consistency:

```bash
systemctl stop xui-bot.service
cp -a /root/SpeedyBot/speedping.db /root/speedping.db.backup
cp -a /root/SpeedyBot/.env /root/speedybot.env.backup
systemctl start xui-bot.service
```

Keep backups private because `.env` contains secrets and the database contains customer/business data.

---

# Useful server commands

Status:

```bash
systemctl status xui-bot.service --no-pager -l
```

Live logs:

```bash
journalctl -u xui-bot.service -f
```

Last 150 log lines:

```bash
journalctl -u xui-bot.service -n 150 --no-pager
```

Restart:

```bash
systemctl restart xui-bot.service
```

Stop/start:

```bash
systemctl stop xui-bot.service
systemctl start xui-bot.service
```

Check restart count:

```bash
systemctl show xui-bot.service -p NRestarts
```

Edit environment:

```bash
nano /root/SpeedyBot/.env
```

---

# Troubleshooting

## Bot does not respond

Check service state:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

Common causes:

- Invalid/revoked Telegram Bot Token.
- Two copies of the same Telegram bot polling at the same time.
- Python runtime error after a manual edit.
- Network/DNS connectivity problem.

## `401` or `403` from 3x-ui

Usually means the Bearer Token is wrong or not accepted.

Make sure you used the **plaintext API Token value**, not:

- The token name.
- The panel password.
- The web base path.

Then run:

```text
/xuidiag
```

## `404` from `/panel/api/...`

Usually check:

- `XUI_BASE_PATH`.
- Panel version/API support.
- Reverse proxy routing.
- Whether you accidentally included the web path inside `XUI_API_URL`.

Correct split:

```text
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

## Subscription link does not work

Check:

- Subscription service is enabled in 3x-ui.
- Subscription port is reachable by customers.
- Domain/TLS configuration.
- `XUI_SUB_SERVER_URL`.
- `XUI_SUB_PATH` matches the panel's configured subscription URI.

## Group assignment fails

Run:

```text
/groupsdiag
/xuidiag
```

Verify the API Token has access to the relevant API and your installed 3x-ui version supports the group endpoints used by the bot.

## Update stopped the bot

Use:

```bash
systemctl restart xui-bot.service
systemctl status xui-bot.service --no-pager -l
```

Then inspect:

```bash
journalctl -u xui-bot.service -n 150 --no-pager
```

The current updater includes self-safe execution, validation, backup and rollback logic specifically to reduce this risk.

---

# Security

Read [SECURITY.md](SECURITY.md) before deploying publicly.

Minimum rules:

- Never commit `.env`.
- Never publish BotFather tokens.
- Never publish 3x-ui API tokens.
- Rotate a secret immediately if it appears in a public chat, screenshot, log or commit.
- Restrict access to the panel port whenever possible.
- Use HTTPS for public panel/subscription endpoints.
- Keep Ubuntu and 3x-ui updated.
- Keep backups outside the public web root.
- Treat subscription URLs and QR codes like passwords.
- Only use this software on infrastructure you own or are authorized to manage.

The `.gitignore` intentionally excludes secrets, SQLite databases, virtual environments and backups.

---

# Project structure

```text
SpeedyBot/
├── main.py              # Telegram bot, business logic and 3x-ui integration
├── install.sh           # First-time Ubuntu installer
├── update.sh            # GitHub updater with backup/rollback
├── requirements.txt     # Python dependencies
├── VERSION.txt          # Project version
├── .env.example         # Safe environment example
├── README.md            # English documentation
├── README_FA.md         # Persian documentation
├── CHANGELOG.md         # Release/change history
├── MIGRATION_NOTES.md   # Upgrade notes
├── SECURITY.md          # Security policy
├── CONTRIBUTING.md      # Contribution guide
├── AUTHOR.md            # Author/project attribution
├── CITATION.cff         # Citation metadata
└── LICENSE              # MIT license
```

Runtime files such as `.env`, `speedping.db`, `.venv/` and `backups/` are intentionally not committed.

---

# Contributing

Bug reports, documentation improvements and code contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) first.

When reporting a bug, **remove all tokens, subscription URLs, customer information and sensitive panel details** from logs/screenshots.

---

# Author

**SpeedyBot is created and maintained by SudoShayanNA.**

- GitHub: [github.com/roseshayan](https://github.com/roseshayan)
- Project: [github.com/roseshayan/SpeedyBot](https://github.com/roseshayan/SpeedyBot)
- Telegram: [@SudoShayanNA](https://t.me/SudoShayanNA)
- Email: `namayandeshayan@gmail.com`

If you publish a fork or derivative, keeping the original author/project attribution is appreciated and required where applicable by copyright/license notices.

---

# License

Released under the [MIT License](LICENSE).

Copyright © 2026 **SudoShayanNA**.

---

> **SpeedyBot · SudoShayanNA**  
> GitHub: `roseshayan/SpeedyBot` · Telegram: `@SudoShayanNA` · Email: `namayandeshayan@gmail.com`
