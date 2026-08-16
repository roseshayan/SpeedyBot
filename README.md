# SpeedyBot v4.0.0

<p align="center">
  <strong>Open-source Telegram sales, subscription and CRM bot for 3x-ui / Sanaei</strong><br>
  Automated provisioning • Free trials • Renewals • Wallet • Affiliate • Inbound routing • CRM • Connection guides • Control Center
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

SpeedyBot turns Telegram into a practical sales, self-service and operations layer for a **3x-ui / Sanaei** panel. It can create clients after payment approval, issue free trials, sell and renew plans, deliver subscription/direct links and QR codes, manage wallet/referral rewards, notify customers about service expiry, provide platform connection guides, and run most day-to-day administration from Telegram.

v4 adds a cleaner **Control Center**, operating modes, plan categories, user purchase restrictions, per-user trial overrides, customer feedback, targeted broadcasts, audit logging, read-only panel snapshots, and Telegram button styles / optional Custom Emoji support.

The stable v3 business core remains in `main.py`. v4 boots through `app.py` and loads modules from `speedybot_v4/`. Runtime data is stored in SQLite and the production service is managed by `systemd` on Ubuntu.

---

## Table of contents

- [Features](#features)
- [What's new in v4](#whats-new-in-v4)
- [Default catalog](#default-catalog)
- [Requirements](#requirements)
- [Before installation](#before-installation)
- [Step-by-step installation](#step-by-step-installation)
- [First-run checklist](#first-run-checklist)
- [Admin Control Center](#admin-control-center)
- [Operating modes](#operating-modes)
- [Plan categories](#plan-categories)
- [Free trials and inbound routing](#free-trials-and-inbound-routing)
- [Per-user trial overrides](#per-user-trial-overrides)
- [Connection guides](#connection-guides)
- [CRM and trial follow-up](#crm-and-trial-follow-up)
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
- [Migrating from v3.x to v4](#migrating-from-v3x-to-v4)
- [Backups and rollback](#backups-and-rollback)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Project layout](#project-layout)
- [License and author](#license-and-author)

---

## Features

### Automated sales and provisioning

- Automatic 3x-ui client creation after payment approval.
- Default free trial: **1 GB / 1 day / 1 IP**.
- Dynamic SQLite-backed plans.
- Per-plan IP limits.
- Manual card-transfer receipt workflow with admin approval.
- Wallet checkout.
- Idempotent provisioning / safe retry behavior.
- Subscription URL delivery.
- Direct proxy-link delivery.
- Subscription QR code.
- Service renewal using the same client identity.
- Optional extra-volume packs for metered plans.

### Inbound routing

Choose exact active inbounds for:

- Free Trial
- Plan #1
- Plan #2
- Any plan created later

If no explicit selection exists, SpeedyBot falls back to **all active inbounds** for backward compatibility. Existing clients are re-synchronized during safe retries and renewal can move a service to the destination plan's configured inbounds.

### Customer experience

- User account.
- Live service status.
- Remaining traffic / expiry visibility.
- Subscription and direct links.
- QR.
- Renewal.
- Extra-volume purchase where applicable.
- Purchase history.
- Wallet history.
- Gift and discount codes.
- Referral / affiliate link.
- Platform-specific connection guides.
- Secure linking of previously purchased services.
- Optional custom service name.
- Customer rating / feedback.
- Optional phone verification.
- Optional required Telegram-channel membership.

### Growth / CRM

- One-level referral rewards.
- Configurable cashback.
- Percentage or fixed discount codes.
- Gift wallet codes.
- Acquisition-source survey after the first successful paid purchase.
- Automated post-trial sales follow-up.
- Structured reasons for not purchasing.
- Targeted broadcasts by audience segment.
- Customer satisfaction feedback.

---

## What's new in v4

### New Control Center

`/sudoadmin` is reorganized into clearer business and operations sections so common actions are easier to scan and less text-dense.

### Operating modes

- `NORMAL` — normal operation.
- `SALES_PAUSED` — new purchases, renewals and volume add-ons are paused; account, guides and support stay available.
- `MAINTENANCE` — sales and new trials are paused; account, guides and support stay available.

### User restrictions / blacklist

Admins can restrict a Telegram user from purchases/trials with a stored reason and later remove the restriction. Support access remains available.

### Plan categories

Organize plans into categories such as Gaming, Germany, Static IP, Business, etc.

### Per-user trial override

Before the user's first trial, admins can override trial GB, days and IP limit for a specific Telegram ID.

### Customer feedback

1–5 stars, optional comment, average rating and rating distribution.

### Targeted broadcast

Send to specific audiences instead of everyone.

### Audit log

Important v4 administrative actions are stored in SQLite and can optionally be mirrored to a private Telegram chat/channel.

### Read-only panel snapshot

Exports a JSON snapshot of clients from the panel for disaster-recovery investigation. Automatic destructive restore is intentionally not included.

### Button styles / Custom Emoji

SpeedyBot supports Telegram's official button styles such as `primary`, `success`, and `danger`. Telegram bots cannot select arbitrary HEX/RGB colors for buttons.

Custom/Premium Emoji button icons are optional and fall back safely when Telegram does not allow them.

---

## Default catalog

Fresh databases receive:

| Plan | Duration | Traffic | IP limit | Default price |
|---|---:|---:|---:|---:|
| Unlimited - 1 user | 30 days | Unlimited | 1 | 250,000 Toman |
| Unlimited - 2 users | 30 days | Unlimited | 2 | 300,000 Toman |
| Unlimited - 3 users | 30 days | Unlimited | 3 | 350,000 Toman |

These are seed defaults only. Update prices and plans from `/sudoadmin` before production sales.

---

## Requirements

Recommended production environment:

- Ubuntu **24.04 LTS**
- Python 3.12
- Current 3x-ui/Sanaei panel exposing `/panel/api/*`
- 3x-ui Bearer API token
- Telegram bot token from `@BotFather`
- Numeric Telegram ID for the Owner
- Working subscription service if subscription URLs are used
- Outbound network access to Telegram and the panel

SpeedyBot uses long polling; Telegram does not require an inbound webhook port.

---

## Before installation

### 1. Create the Telegram bot

In `@BotFather`:

1. Send `/newbot`.
2. Choose a display name.
3. Choose a username ending in `bot`.
4. Copy and securely store the token.

Never put the token into a public Issue, screenshot, README or commit.

### 2. Find the Owner Telegram ID

Get the **numeric** Telegram user ID for the account that will own the bot. This becomes `ADMIN_ID`.

A Telegram username is not the same as a numeric Telegram ID.

### 3. Create a 3x-ui Bearer API token

In the panel:

```text
Settings → Security → API Token
```

Create a token and save the **plaintext token value** when shown.

The following are not the Bearer API token:

- Token display name
- Panel password
- Hidden panel web path

### 4. Understand API URL vs Base Path

If your panel opens at:

```text
https://panel.example.com:2053/secret-panel/
```

enter:

```text
X-UI API base URL: https://panel.example.com:2053
X-UI security base path: /secret-panel
```

If no hidden path is configured:

```text
X-UI security base path: /
```

Do not duplicate the hidden path inside the base URL field.

### 5. Subscription settings

If a real subscription URL looks like:

```text
https://sub.example.com:2096/sub/ABC123
```

installer values are:

```text
Subscription server base URL: https://sub.example.com:2096
Subscription URI path: /sub/
```

Use your actual 3x-ui subscription path if it differs.

---

## Step-by-step installation

Log in as root:

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

Before installing the service, the installer performs a **read-only API preflight** to catch authentication/base-path mistakes.

### Runtime files

```text
/root/SpeedyBot/.env
/root/SpeedyBot/.venv/
/root/SpeedyBot/speedping.db
/root/SpeedyBot/run.sh
/root/SpeedyBot/backups/
/etc/systemd/system/xui-bot.service
```

In v4, `run.sh` prefers `app.py` and falls back to `main.py` for older builds.

### Service status

```bash
systemctl status xui-bot.service --no-pager -l
```

### Live logs

```bash
journalctl -u xui-bot.service -f
```

### Last 150 log lines

```bash
journalctl -u xui-bot.service -n 150 --no-pager
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
2. Verify plan prices, duration, traffic and IP limit.
3. Configure plan categories.
4. Review **Trial & Inbounds**.
5. Enable/disable free trials as required.
6. Select inbounds for Trial and each plan.
7. Verify/reconcile `Customers` and `Trial` groups.
8. Create connection guides for Android/iOS/Windows/macOS/Linux/TV.
9. Review CRM and trial follow-up settings.
10. Configure phone verification/channel membership if needed.
11. Confirm operating mode is `NORMAL`.
12. Review button styles.
13. Configure/test an audit Telegram chat if desired.
14. Run `/xuidiag`.
15. Run `/groupsdiag`.
16. Run `/notifydiag`.
17. Issue one real trial.
18. Run one small end-to-end purchase before heavy production use.

---

## Admin Control Center

Open with:

```text
/sudoadmin
```

Major sections include:

- Sales analytics
- Plans
- Plan categories
- Volume packs
- Trial and inbounds
- Per-user trial overrides
- Sanaei Groups
- CRM / follow-up
- Customer feedback
- Targeted broadcast
- Wallet / referral
- Cashback / gift / discount codes
- Blacklist
- Operating mode
- Verification / channel membership
- Multiple admins
- Service notifications
- Backups
- Panel snapshot
- Audit log
- Button styles / Custom Emoji
- Payment data
- Welcome / FAQ content

---

## Operating modes

### NORMAL

Everything is available.

### SALES_PAUSED

New purchases, renewals and volume add-ons are blocked. Existing customers can still access their account, guides and support.

### MAINTENANCE

New purchases and new free trials are blocked. Existing account/service visibility, guides and support remain available.

---

## Plan categories

From `/sudoadmin`, create categories such as:

```text
Germany
Gaming
Anti-Sanction
Static IP
Business
```

Existing plans are assigned to the default `عمومی` category during v4 migration and can later be moved.

---

## Free trials and inbound routing

Open:

```text
/sudoadmin → Trial & Inbounds
```

You can:

- Turn Trial on/off.
- Select exact Trial inbounds.
- Select exact inbounds independently per plan.
- Reset a scope to all active inbounds.

### Direct config vs Subscription

These are separate concepts.

Direct proxy links are filtered to schemes such as:

```text
vless://
vmess://
trojan://
ss://
hysteria://
hysteria2://
hy2://
```

HTTP/HTTPS subscription URLs remain in the Subscription section and are not mislabeled as direct configs.

If a direct address is wrong, compare the bot output with 3x-ui **Copy URL**. If both contain the same wrong host, correct the inbound Share Address/Public Host in 3x-ui.

---

## Per-user trial overrides

Before a user's first trial, an admin can define:

```text
TelegramID | VolumeGB | Days | IPLimit | Optional note
```

Example:

```text
123456789 | 5 | 3 | 2 | VIP lead
```

Users without an override receive the normal global Trial. The configured Trial inbound selection still applies.

---

## Connection guides

Admin path:

```text
/sudoadmin → Connection Guides
```

Supported platforms:

- Android
- iPhone / iOS
- Windows
- macOS
- Linux
- Android TV / TV Box

Each guide can contain ordered:

- Text
- Photo + caption
- Video + caption
- Preview
- Reordering

Telegram `file_id` values are stored instead of media binaries, keeping SQLite smaller.

A guide CTA can be shown after successful paid/trial provisioning.

---

## CRM and trial follow-up

The acquisition survey can ask after the first successful purchase:

- Friend recommendation
- Telegram search
- Channel advertisement
- Instagram
- Web/search
- Returning customer
- Other

When a Trial expires, SpeedyBot can wait for a configured delay and check whether the user converted to a paid service. Converted customers are skipped.

Non-buyers can answer reasons such as quality, price, setup difficulty, later purchase, no current need, ready to buy, or other. Responses can lead to purchase/support CTAs.

---

## Existing services and custom names

### Custom service name

Rules:

- 3–40 characters
- ASCII letters/numbers plus `.`, `_`, `-`
- Checked against the local database before checkout
- Checked against the connected 3x-ui panel for duplicates

### Link an existing service

A user can enter a pre-existing 3x-ui client email/name.

Ownership is protected:

- Matching panel `tgId` → automatic link
- Non-matching `tgId` → admin approval required
- A client can be linked to one SpeedyBot account only

---

## Payments, wallet and marketing

### Manual/card payment

The bot shows configured payment details, receives a receipt image and waits for admin approval before provisioning.

### Wallet

- Balance
- Immutable ledger/history
- Admin credit/debit
- Wallet checkout

### Affiliate

- Permanent invite link
- Referral stored only on first registration
- Commission after qualifying approved/provisioned purchase
- Exactly-once commission protection

### Cashback / Discount / Gift

Admins can configure:

- Cashback percentage
- Percentage discount
- Fixed discount
- Minimum purchase
- Expiry / usage limit
- Gift code for wallet credit

---

## Renewals

Renewal keeps the same service identity and:

- Preserves remaining time during early renewal.
- Updates quota/IP limit for the selected plan.
- Re-enables the client.
- Resets traffic for the new period.
- Synchronizes the client to the selected renewal plan's inbounds.

---

## Groups

Default mapping:

```text
Paid → Customers
Trial → Trial
```

Check live state:

```text
/groupsdiag
```

---

## Customer feedback

Users can leave a 1–5 star rating and an optional comment.

Admin analytics show:

- Total feedback count
- Average rating
- Distribution per star
- Recent comments

The feature can be enabled/disabled.

---

## Targeted broadcasts

Current audience segments:

- All active users
- Customers
- Trial users who did not buy
- Expired-trial users who did not buy
- Users who never bought

Messages are delivered with Telegram `copy_message`, so text/photo/video/document messages can be reused.

Always test with a small audience before sending to all customers.

---

## Audit log

Events such as operating-mode changes, user restrictions, category changes, trial overrides, broadcasts, panel snapshots and UI changes are stored in SQLite.

You can optionally mirror important events to a private Telegram group/channel where the bot has permission to post.

---

## Panel snapshot

The admin can export a read-only JSON client snapshot from 3x-ui.

Treat snapshot files as sensitive credentials. Never publish them in GitHub Issues or public chats.

Automatic one-click restore is intentionally not implemented.

---

## Button styles and Custom Emoji

Supported Telegram button styles:

```text
default
primary
success
danger
```

Telegram does not expose arbitrary HEX/RGB button colors to bots.

For Custom Emoji:

1. Run `/emojiid`.
2. Send a Custom Emoji.
3. Save its ID for the desired button group.
4. Enable Custom/Premium Emoji in admin.

If Telegram rejects the icon, keep the option disabled; normal emoji/text remains functional.

---

## Notifications

The background monitor can send one-time events for:

- 90% traffic warning
- Paid-service expiry warning
- Trial expiry warning
- Traffic exhausted
- Time expired

Event claims are persisted in SQLite so a restart does not intentionally resend the same event.

---

## Diagnostics

### `/xuidiag`

Read-only 3x-ui API diagnostics for authentication/base-path/HTTP problems.

### `/groupsdiag`

Live group names/member counts.

### `/notifydiag`

Runs the service monitor once and reports tracked/found/missing/error counts.

---

## Updating

Read [MIGRATION_NOTES.md](MIGRATION_NOTES.md) before major releases.

### Check only

```bash
cd /root/SpeedyBot
./update.sh --check
```

### Normal update

```bash
./update.sh
```

### Force redeploy

```bash
./update.sh --force
```

The v4 updater:

1. Re-executes itself from `/tmp` so replacing `update.sh` cannot terminate the current updater.
2. Checks GitHub `main`.
3. Clones the remote source to a temporary directory.
4. Validates Python and shell syntax before downtime.
5. Installs dependencies before stopping the bot.
6. Stops the service.
7. Backs up `.env`, SQLite DB/WAL/SHM, source and v4 modules.
8. Deploys the new source.
9. Rewrites `run.sh` to prefer `app.py` with `main.py` fallback.
10. Restarts systemd.
11. Performs a health check.
12. Attempts rollback when deployment fails.

---

## Migrating from v3.x to v4

**Do not delete `.env` or `speedping.db`.**

Typical upgrade:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

Then verify:

```bash
cat VERSION.txt
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

Expected version:

```text
4.0.0
```

The v4 database migration is additive. Existing user, transaction, wallet, referral, trial and service data is preserved.

After upgrade, test:

```text
/start
/sudoadmin
/xuidiag
/groupsdiag
/notifydiag
```

---

## Backups and rollback

Important runtime data:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

Deployment backups are typically stored under:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

If deployment fails, the updater attempts to restore the previous source/database and restart the old service.

For a real business, periodically copy backups off the VPS.

---

## Troubleshooting

### Bot is not responding

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 200 --no-pager
```

### Restart loop / duplicate processes

```bash
systemctl show xui-bot.service -p NRestarts
pgrep -af 'python.*(app.py|main.py)'
```

Only the systemd-managed production process should normally use the production bot token.

### 401 / 403

Verify the **plaintext Bearer API token**. Do not use the token display name or panel web password.

### 404

Check:

- API base URL
- Hidden base path
- Reverse-proxy routing
- Panel API availability/version

Example:

```text
Panel: https://panel.example.com:2053/secret/
XUI_API_URL=https://panel.example.com:2053
XUI_BASE_PATH=/secret
```

### Subscription works but direct address is wrong

Compare the bot-generated direct link with 3x-ui **Copy URL**. If both contain the wrong public host, fix the inbound Share Address/Public Host inside 3x-ui.

### Trial has no direct URL for one inbound

Some protocols do not expose a usable share URL. Select appropriate proxy inbounds for Trial.

### Edit `.env`

```bash
nano /root/SpeedyBot/.env
systemctl restart xui-bot.service
```

Never paste `.env` into a public Issue.

---

## Security

- Never commit `.env`.
- Never expose Telegram bot tokens.
- Never expose 3x-ui API tokens.
- Treat subscription/direct links and QR codes as passwords.
- Treat panel snapshot files as sensitive.
- Keep SSH, Ubuntu and 3x-ui updated.
- Use TLS for externally exposed panel/subscription endpoints.
- Existing-service claims require matching `tgId` or admin approval.
- Redact sensitive paths/tokens/domains before posting logs publicly.

See [SECURITY.md](SECURITY.md).

---

## Project layout

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

Runtime files such as `.env`, SQLite databases, `.venv`, backups and logs are excluded by `.gitignore`.

---

## Roadmap / scope

Larger future modules may include:

- Multi-panel routing
- Batch-order / reseller suite
- Multiple online payment gateways
- Telegram Mini App
- Independent web admin
- AI support
- Multi-step/dry-run panel restore

These should be developed as tested modules instead of rushed patches to the core.

Feature requests and bug reports are welcome through GitHub Issues. Remove all secrets before posting logs.

---

## License and author

Licensed under the **MIT License**.

Created and maintained by **SudoShayanNA**.

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- Repository: **https://github.com/roseshayan/SpeedyBot**

If you redistribute or build on the project, keeping a link to the original repository helps users find documentation, security updates and maintained upstream releases.
