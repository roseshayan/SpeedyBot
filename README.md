# SpeedyBot v3.1.0

<p align="center">
  <strong>Open-source Telegram VPN sales & subscription management for 3x-ui / Sanaei</strong><br>
  Automated provisioning • Trials • Renewals • Wallet • Affiliate • Inbound routing • CRM • Connection guides
</p>

<p align="center">
  <a href="README_FA.md">🇮🇷 راهنمای فارسی</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="SECURITY.md">Security</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

> **Author / Maintainer:** **SudoShayanNA**  
> Telegram: **@SudoShayanNA** · Email: **namayandeshayan@gmail.com**  
> Official source: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot turns a Telegram bot into a practical storefront and self-service layer for a **3x-ui / Sanaei** panel. It can create clients automatically, issue a controlled free trial, sell and renew plans, expose subscription/direct links, manage wallet/referral rewards, notify customers before expiration, and provide an admin workflow without requiring a separate web dashboard.

The project uses the current 3x-ui `/panel/api/*` REST API with Bearer-token authentication. Runtime state is stored in SQLite and the service runs under `systemd` on Ubuntu.

---

## Table of contents

- [What is included](#what-is-included)
- [Default catalog](#default-catalog)
- [Requirements](#requirements)
- [Before installation](#before-installation)
- [Step-by-step installation](#step-by-step-installation)
- [First-run checklist](#first-run-checklist)
- [Admin panel](#admin-panel)
- [Free trials and inbound routing](#free-trials-and-inbound-routing)
- [Connection guides](#connection-guides)
- [CRM and trial follow-up](#crm-and-trial-follow-up)
- [Existing services and custom names](#existing-services-and-custom-names)
- [Payments, wallet and marketing](#payments-wallet-and-marketing)
- [Service renewals](#service-renewals)
- [Groups](#groups)
- [Notifications](#notifications)
- [Diagnostics](#diagnostics)
- [Updating](#updating)
- [Backups](#backups)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Project files](#project-files)
- [Roadmap / scope](#roadmap--scope)
- [License and author](#license-and-author)

---

## What is included

### Automated sales & provisioning

- Automatic 3x-ui client creation after payment approval.
- Free trial: **1 GB / 1 day / 1 IP** by default.
- Dynamic plan catalog stored in SQLite and managed from Telegram admin.
- Per-plan `limitIp`.
- Card-transfer/manual receipt approval and wallet checkout.
- Safe retry/idempotency so a failed Telegram message or restart does not intentionally create duplicate clients.
- Subscription link, direct protocol links and subscription QR.
- Service renewal with the same client identity and subscription ID.
- Optional extra-volume packs for metered plans.

### Inbound routing

Starting in v3.1, you can select which active inbounds are used for:

- Free Trial
- Plan #1
- Plan #2
- Plan #3
- Any plan you add later

If no explicit selection exists for a scope, SpeedyBot uses **all active inbounds**, preserving the old behavior. On retry, an existing client is re-synchronized to the configured inbound set. Renewal to another plan also synchronizes the service to the destination plan's inbound selection.

### Customer experience

- User account and live service status.
- Download/copy direct links and subscription link.
- QR code for the subscription.
- Renew from the account page.
- Purchase history.
- Wallet history.
- Gift and discount code redemption.
- Referral link and affiliate statistics.
- Optional phone verification.
- Optional required Telegram-channel membership.
- Admin-managed platform-specific connection tutorials.

### Growth / CRM

- One-level referral / affiliate rewards.
- Configurable cashback.
- Percentage or fixed discount codes.
- Gift wallet codes.
- Optional acquisition survey after successful purchase.
- Automated trial-expiry follow-up with a configurable delay.
- Structured reasons for not purchasing and admin-side analytics.

### Administration

- `/sudoadmin` Telegram admin dashboard.
- Multiple admins; the original `ADMIN_ID` remains Owner.
- Plan management.
- Volume-pack management.
- Trial on/off switch.
- Inbound routing per Trial and per plan.
- Connection-guide editor (text/photo/video).
- CRM switches and analytics.
- Wallet management.
- Sanaei Groups synchronization.
- Payment/card information editor.
- Editable welcome and FAQ text.
- Configurable service-name strategy.
- Automatic and manual SQLite backups.
- Service expiry/quota notification management.

---

## Default catalog

Fresh databases receive these plans automatically:

| Plan | Duration | Traffic | IP limit | Default price |
|---|---:|---:|---:|---:|
| Unlimited - 1 user | 30 days | Unlimited | 1 | 250,000 Toman |
| Unlimited - 2 users | 30 days | Unlimited | 2 | 300,000 Toman |
| Unlimited - 3 users | 30 days | Unlimited | 3 | 350,000 Toman |

These are only defaults. Use `/sudoadmin` to change/add/disable plans for your business.

---

## Requirements

Recommended production setup:

- Ubuntu **24.04 LTS**
- Python 3.12 (Ubuntu package is fine)
- Public or locally reachable 3x-ui/Sanaei panel using the current `/panel/api/*` API
- 3x-ui Bearer API token
- Telegram bot token from BotFather
- Telegram numeric user ID for the owner/admin
- A working 3x-ui subscription server if you want subscription links
- Outbound access from the VPS to Telegram and your panel

The bot uses polling, so Telegram does **not** require an inbound webhook port for SpeedyBot.

---

## Before installation

### 1. Create a Telegram bot

Open `@BotFather` in Telegram:

1. Send `/newbot`.
2. Choose a display name.
3. Choose a username ending in `bot`.
4. Copy the API token.

Never paste that token into a public Issue, README, screenshot or commit.

### 2. Find your numeric Telegram ID

Use any trusted Telegram ID helper bot or another method to obtain your numeric account ID. This becomes the initial `ADMIN_ID` and Owner of SpeedyBot.

### 3. Create a 3x-ui API token

In 3x-ui open:

`Settings → Security → API Token`

Create a token and copy the **plaintext token value** when shown. The token name, panel password, and hidden web path are not the Bearer token.

### 4. Understand panel URL vs Base Path

If your panel opens at:

```text
https://panel.example.com:2053/secret-panel/
```

enter:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

Do not include `/secret-panel` inside the base URL field.

If you have no hidden web path:

```text
X-UI security base path: /
```

### 5. Find subscription URL and path

In 3x-ui `Settings → Subscription`, note the public subscription host/port and the configured subscription path.

Example public subscription:

```text
https://sub.example.com:2096/sub/ABC123
```

Installer values:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

---

## Step-by-step installation

Log in as `root` (or become root), then:

```bash
apt update
apt install -y git

git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

The installer asks for:

1. Telegram Bot Token
2. Telegram Admin numeric ID
3. X-UI API base URL
4. X-UI security base path
5. Panel Bearer API Token
6. Subscription server base URL
7. Subscription URI path

Before starting the bot, the installer performs a **read-only API preflight** against the panel. Authentication/base-path problems are caught before the service is considered installed.

### What the installer creates

- Application directory: `/root/SpeedyBot`
- Virtualenv: `/root/SpeedyBot/.venv`
- Runtime secrets: `/root/SpeedyBot/.env` (`chmod 600`)
- Database: `/root/SpeedyBot/speedping.db`
- Runner: `/root/SpeedyBot/run.sh`
- systemd service: `xui-bot.service`

### Check service

```bash
systemctl status xui-bot.service --no-pager -l
```

Live logs:

```bash
journalctl -u xui-bot.service -f
```

Restart:

```bash
systemctl restart xui-bot.service
```

---

## First-run checklist

After `/start`, log in using your Owner Telegram account and send:

```text
/sudoadmin
```

Before accepting real customers, review:

1. **Payment settings** — replace the example bank/card data.
2. **Plans** — confirm price, days, traffic and IP limit.
3. **🧪 Trial & Inbounds** — enable/disable Trial and define inbound routing.
4. **👥 Sanaei Groups** — reconcile/create `Customers` and `Trial`.
5. **📲 Connection Guides** — add platform tutorials.
6. **📈 CRM & Follow-up** — choose survey/follow-up behavior.
7. **Security** — decide whether phone verification or channel membership is required.
8. Run `/xuidiag`, `/groupsdiag`, `/notifydiag`.
9. Use a separate Telegram account to test a free trial and a test purchase before production.

---

## Admin panel

Send:

```text
/sudoadmin
```

The admin interface contains business configuration, plans, groups, rewards, notifications, guides, CRM and operations.

Useful admin-only commands:

```text
/xuidiag      Read-only 3x-ui API diagnostics
/groupsdiag   Live 3x-ui client-group counts
/notifydiag   Run service monitoring once and show a summary
```

---

## Free trials and inbound routing

Open:

`/sudoadmin → 🧪 تست و Inboundها`

You can:

- Turn free Trial on/off.
- Select exact inbounds for Trial.
- Select exact inbounds independently for every active plan.
- Reset a scope to all active inbounds.

The picker shows inbound ID, remark/protocol/port from the live panel.

### Why v3.1 changed trial delivery

Direct configuration URLs and a subscription URL are different things. v3.1 gets direct protocol URLs from 3x-ui's client link APIs and filters the result to actual proxy schemes such as:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

HTTP/HTTPS subscription URLs are kept in the separate **Subscription** section and are not labeled as direct configs.

For best results, configure correct Share Address / host values in 3x-ui itself: SpeedyBot intentionally uses panel-generated URLs rather than inventing public addresses.

---

## Connection guides

Open:

`/sudoadmin → 📲 راهنمای اتصال`

Supported guide categories:

- Android
- iPhone / iOS
- Windows
- macOS
- Linux
- Android TV / TV Box

For each platform, add multiple ordered items:

- Text
- Photo (+ optional caption)
- Video (+ optional caption)
- Preview the finished guide
- Reorder items using their item ID and sort value

Telegram's existing file ID is stored, not the media binary itself, keeping the SQLite database small.

Users can open guides from the main menu, account/service view, and the automatic CTA sent after a trial or paid service is delivered.

---

## CRM and trial follow-up

Open:

`/sudoadmin → 📈 CRM و پیگیری`

### Acquisition survey

Optional survey asked after a successful paid purchase. Default choices include:

- Friend recommendation
- Telegram search
- Channel advertisement
- Instagram
- Web/search
- Returning customer
- Other

The bot stores one acquisition answer per user and shows response statistics in admin.

### Trial follow-up

When Trial expires/exhausts, SpeedyBot can schedule a follow-up, default **6 hours later**. Configure 1–168 hours from admin.

Before messaging, the bot checks whether the user already bought a paid service. Customers who converted are skipped.

Users can answer structured reasons such as speed, price, setup difficulty, later purchase, no current need, ready to buy or other. The reply can lead to the purchase menu or support.

This CRM expiry detection is independent from user-facing quota/expiry notifications: disabling standard notification messages does not silently disable the sales follow-up pipeline.

---

## Existing services and custom names

### Custom service name

When enabled, a buyer can use an automatically generated name or choose their own client name.

Rules:

- 3–40 characters
- ASCII letters/numbers plus `.`, `_`, `-`
- Must not already exist in SpeedyBot
- Must not already exist in the connected 3x-ui panel

The duplicate check happens **before checkout**.

### Link a previously purchased service

From the user account, select **Add previously purchased service** and enter its 3x-ui client email/name.

SpeedyBot does not trust the name alone:

- If the panel client's `tgId` equals the current Telegram user ID, ownership is accepted automatically.
- Otherwise an ownership claim goes to the admins for approval/rejection.
- A panel client can be linked to only one SpeedyBot account.

Linked services appear in the account and are included in monitoring.

---

## Payments, wallet and marketing

### Card/manual payment

SpeedyBot can show your configured bank/card details, accept the user's receipt image, and queue the transaction for admin approval. Service provisioning occurs only after approval.

Configure payment information from `/sudoadmin` before going live.

### Wallet

- Immutable wallet transaction history.
- Admin credit/debit controls.
- Purchases can be paid from wallet when sufficient.

### Affiliate

- Permanent Telegram referral link.
- Referral bound on the invited user's first registration.
- Commission credited only after a qualifying cash-backed purchase is approved and provisioned.
- Exactly-once commission protection per purchase.

### Cashback, discount and gift codes

Admin can configure:

- Cashback percentage
- Percentage discount codes
- Fixed discount codes
- Minimum purchase requirements
- Expiry and usage limits
- Gift codes that credit wallet balance

---

## Service renewals

A paid service can be renewed from the user account.

Renewal:

- Keeps the existing client/subscription identity.
- Extends from the later of the existing expiry or current time, so early renewal does not throw away remaining time.
- Updates IP limit/quota based on the chosen renewal plan.
- Re-enables the client.
- Resets traffic for the new period.
- In v3.1, synchronizes the client to that renewal plan's selected inbounds.

---

## Groups

SpeedyBot integrates with 3x-ui Client Groups:

- Paid services → `Customers`
- Free trials → `Trial`

Names are stored in bot settings and can be reconciled from admin. Startup reconciliation also tries to place previously bot-issued clients into the proper group.

Check live groups:

```text
/groupsdiag
```

---

## Notifications

The background service monitor defaults to a five-minute cycle and can send one-time messages for:

- 90% traffic usage warning
- Paid-service expiry warning (default 24 hours)
- Trial expiry warning (default 3 hours)
- Traffic exhausted
- Time expired

Notification claims are stored in SQLite so a restart does not intentionally send the same event repeatedly.

---

## Diagnostics

### `/xuidiag`

Tests the read-only 3x-ui connection and reports errors such as authentication, base-path or HTTP problems without intentionally printing the Bearer token.

### `/groupsdiag`

Returns live group names and member counts from the panel.

### `/notifydiag`

Runs the service monitor immediately and reports tracked/found/missing/error counts.

---

## Updating

SpeedyBot can update from the public GitHub repository:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

Force redeploy of the current remote commit:

```bash
./update.sh --force
```

The updater:

1. Clones the latest `main` into a temporary directory.
2. Validates Python and shell syntax.
3. Installs/updates dependencies before downtime.
4. Stops the bot for a consistent SQLite backup.
5. Backs up `.env`, DB/WAL/SHM and application files.
6. Deploys the new source.
7. Restarts and health-checks the systemd service.
8. Attempts rollback if the new service fails.

Read [MIGRATION_NOTES.md](MIGRATION_NOTES.md) before major upgrades.

---

## Backups

Automatic SQLite backup is enabled by default with retention. Manual backup is also available in admin.

Do not rely only on the VPS disk. For a real business, periodically copy the backup directory to a different machine/storage provider.

Important runtime data:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/backups/
```

---

## Security

- Never commit `.env`.
- Never post Telegram Bot tokens or 3x-ui API tokens in Issues/log screenshots.
- Bearer API tokens have powerful panel access; protect them as administrator credentials.
- Subscription links, proxy URIs and QR codes contain access credentials; treat them as passwords.
- Run the bot on a dedicated VPS/user boundary appropriate for your environment.
- Restrict SSH, keep Ubuntu/3x-ui updated and use TLS for externally exposed panel/subscription endpoints.
- Existing-service claims require `tgId` ownership or admin review specifically to prevent a user from claiming another person's client by guessing its name.

See [SECURITY.md](SECURITY.md).

---

## Troubleshooting

### Bot is not responding

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

### API returns 401 / 403

Usually verify the **plaintext API token** stored as `XUI_BEARER_TOKEN`. Do not use the token's display name or your panel web password.

### API returns 404

Check:

- X-UI API base URL
- X-UI Base Path
- Reverse proxy routing
- Panel version/API availability

For a panel at:

```text
https://panel.example.com:2053/secret/
```

you normally want:

```text
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Subscription works but direct address is wrong

SpeedyBot v3.1 uses panel-generated client links. Compare `/panel/api/clients/links/{email}` / 3x-ui **Copy URL** with the bot output. If both have the same wrong host/address, correct the inbound Share Address/host/public endpoint inside 3x-ui rather than hard-coding an address in SpeedyBot.

### Trial creates no direct URL for one inbound

Some inbound protocols do not have a client share-URL form. Select appropriate proxy inbounds for Trial from `🧪 تست و Inboundها`.

### Edit runtime environment

```bash
nano /root/SpeedyBot/.env
systemctl restart xui-bot.service
```

Do not paste the contents of `.env` into a public Issue.

---

## Project files

```text
SpeedyBot/
├── main.py
├── install.sh
├── update.sh
├── requirements.txt
├── VERSION.txt
├── README.md
├── README_FA.md
├── CHANGELOG.md
├── MIGRATION_NOTES.md
├── RELEASE_NOTES_v3.1.0.md
├── SECURITY.md
├── SUPPORT.md
├── CONTRIBUTING.md
├── AUTHOR.md
├── LICENSE
├── .env.example
└── .github/
```

Runtime files such as `.env`, SQLite databases, virtualenv, backups and logs are excluded by `.gitignore`.

---

## Roadmap / scope

SpeedyBot intentionally keeps the core self-hosted and Telegram-first. A separate web dashboard, online payment-gateway integrations, multi-panel routing, reseller/batch-order workflows and Mini App UI are larger modules and should be implemented with their own architecture rather than rushed into the core.

Feature requests and bug reports are welcome through GitHub Issues. Please remove all secrets before posting logs.

---

## License and author

Licensed under the **MIT License**. See [LICENSE](LICENSE).

Created and maintained by **SudoShayanNA**.

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- GitHub repository: **https://github.com/roseshayan/SpeedyBot**

If you redistribute or build on the project, keeping a link to the original repository helps users find documentation, security updates and the maintained upstream version.
