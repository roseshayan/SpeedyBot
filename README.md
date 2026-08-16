# SpeedyBot v4.0.0

<p align="center"><strong>Open-source Telegram sales, subscription and customer-management bot for 3x-ui / Sanaei</strong></p>

<p align="center"><a href="README_FA.md">🇮🇷 راهنمای فارسی</a> · <a href="CHANGELOG.md">Changelog</a> · <a href="SECURITY.md">Security</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

> **Author / Maintainer:** **SudoShayanNA**  
> Telegram: **@SudoShayanNA** · Email: **namayandeshayan@gmail.com**  
> Official repository: **https://github.com/roseshayan/SpeedyBot**

SpeedyBot turns Telegram into a self-hosted storefront and control center for a modern **3x-ui / Sanaei** deployment. It provisions clients, sells and renews services, issues trials, manages wallets and referrals, routes plans to selected inbounds, follows up leads, and gives administrators an operational dashboard without requiring a separate web panel.

## v4 highlights

- New modular runtime: stable v3 business core remains in `main.py`; v4 product features live in `speedybot_v4/` and are loaded by `app.py`.
- Cleaner customer account, categorized plan storefront and reorganized admin Control Center.
- Official Telegram button styles: `primary` (blue), `success` (green), `danger` (red), plus default style.
- Optional Custom/Premium Emoji IDs on important buttons, with safe fallback and `/emojiid` helper.
- Operating modes: **Normal**, **Sales Paused**, **Maintenance**.
- User purchase blacklist/restriction with reason and audit trail.
- Plan categories for country/use-case/product grouping.
- Per-user trial override: traffic, days and IP limit.
- 1–5 star customer feedback with comments and admin analytics.
- Targeted broadcasts to all users, customers, trial leads, expired-trial leads, or users who never purchased.
- SQLite audit events and optional Telegram audit channel.
- Read-only emergency 3x-ui client snapshot export.
- v3.1 features remain available: secure existing-service claims, custom client names, CRM acquisition survey, trial follow-up, connection guides, plan/trial inbound routing, groups, wallet, referral, cashback, discount/gift codes and notifications.

## Requirements

Recommended:

- Ubuntu 24.04 LTS
- Python 3.12+
- Current 3x-ui/Sanaei panel with `/panel/api/*`
- 3x-ui Bearer API token
- Telegram bot token from `@BotFather`
- Numeric Telegram ID for the owner/admin
- Working subscription server if subscription URLs are required

SpeedyBot uses long polling; no Telegram webhook port is required.

## Fresh installation

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
2. Owner/Admin Telegram numeric ID
3. X-UI API base URL, for example `https://panel.example.com:2053`
4. X-UI security base path, for example `/secret` or `/`
5. Plaintext Bearer API Token from **Settings → Security → API Token**
6. Subscription server base URL
7. Subscription URI path, usually `/sub/`

Before installing the service, the installer performs a read-only API preflight.

Runtime files:

```text
/root/SpeedyBot/.env          secrets, chmod 600
/root/SpeedyBot/speedping.db  SQLite data
/root/SpeedyBot/run.sh        systemd runner
```

Check the service:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -f
```

## Upgrade from v3.x

Do not delete `.env` or `speedping.db`.

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

The v4 updater:

1. runs itself from a temporary copy;
2. clones and validates the new source before downtime;
3. installs dependencies before stopping the bot;
4. backs up `.env`, SQLite DB/WAL/SHM, source and v4 modules;
5. deploys the new files;
6. switches the runner to `app.py` when available;
7. restarts and health-checks systemd;
8. restores the previous build if deployment fails.

v4 database migrations are additive. Existing sales, users, wallet history, trials and service records are preserved.

## Admin Control Center

Send:

```text
/sudoadmin
```

Major sections include:

- Sales analytics and plan management
- Plan categories
- Trial and inbound routing
- Per-user custom trial settings
- Sanaei Groups (`Customers` / `Trial`)
- CRM and trial follow-up
- Customer feedback analytics
- Targeted broadcast
- Rewards, referral, cashback, gift/discount codes
- Operating mode and user restrictions
- Authentication/membership and admins
- Notifications and live server status
- Backups and read-only panel snapshot
- Audit Log
- Button appearance and Custom Emoji
- Payment details, texts and FAQ

## Operating modes

`Normal` keeps all features available.

`Sales Paused` blocks paid purchases, renewals and extra-volume checkout while account, guides and support remain available.

`Maintenance` also disables new free trials. Existing account/service views, guides and support stay available so users are not locked out of help during maintenance.

## Plan categories

Use `/sudoadmin → Plan Categories` to create groups such as:

```text
Germany
Gaming
Static IP
Anti-Sanction
Business
```

Existing plans are automatically assigned to a default category during migration. Assign any plan to another category from admin.

## Custom trial per user

Before a user takes their first trial, an admin can set:

```text
TelegramID | Traffic GB | Days | IP Limit | Optional note
```

Example:

```text
123456789 | 5 | 3 | 2 | VIP prospect
```

The normal Trial inbound selection still applies. Users without an override continue using the global trial configuration.

## Customer feedback

Users can submit a 1–5 star rating and optional comment. Admin sees average rating, distribution and recent comments. Feedback can be disabled from Control Center.

## Targeted broadcast

Broadcasts can copy any supported Telegram message type to selected audiences:

- all active users;
- paid customers;
- users who received a trial but did not buy;
- expired-trial users who did not buy;
- users who never purchased.

A result summary and broadcast history are stored after delivery.

## Blacklist / purchase restriction

Admins can restrict a Telegram user from purchases and trials while leaving account/support access available. A reason is stored so future administrators know why the restriction exists.

## Audit Log

Important v4 admin actions are written to SQLite. Optionally configure a Telegram group/channel Chat ID to receive operational events. The bot must have permission to post there.

Do not use the audit channel as your only backup.

## Read-only panel snapshot

`Panel Snapshot` calls the 3x-ui client export endpoint and sends the admin a JSON snapshot. It is intentionally **read-only**; v4 does not provide a one-click destructive panel restore.

The snapshot contains sensitive service credentials. Never upload it to GitHub or public support chats.

## Button styles and Custom Emoji

Telegram currently provides predefined button styles rather than arbitrary RGB/HEX colors:

- `primary` — blue
- `success` — green
- `danger` — red
- default client style

Use `/sudoadmin → Appearance & Buttons` to cycle styles for Buy, Account, Trial, Guide, Support and Admin actions.

Custom Emoji IDs can also be assigned. Use:

```text
/emojiid
```

then send a Telegram Custom Emoji to extract its ID. Telegram applies eligibility rules to Custom Emoji on bot buttons. SpeedyBot therefore keeps the feature optional and performs a live test before enabling configured Premium Emoji buttons. If unavailable, normal emoji/text remains usable.

## Existing v3.1 capabilities

SpeedyBot still includes:

- paid and trial client provisioning;
- exact inbound selection per trial and per plan;
- direct protocol links + subscription URL + QR;
- renewal preserving existing service identity;
- volume packs for metered plans;
- secure existing-client claim via `tgId` or admin approval;
- optional custom service name with duplicate validation against bot DB and 3x-ui;
- wallet and immutable wallet ledger;
- one-level affiliate/referral rewards;
- cashback;
- percentage/fixed discount codes and gift-wallet codes;
- phone verification and required-channel membership;
- connection guides for Android, iOS, Windows, macOS, Linux and TV using text/photo/video;
- acquisition-source survey;
- smart follow-up after a free trial expires;
- expiry/quota notifications;
- automatic/manual SQLite backups;
- multiple admins;
- diagnostics: `/xuidiag`, `/groupsdiag`, `/notifydiag`.

## CI and tests

Every pull request runs GitHub Actions with:

```text
Python syntax: main.py, app.py, speedybot_v4/*.py
Unit tests: v4 migrations, categories, blacklist, audiences, feedback, UI payloads
Shell syntax: install.sh, update.sh
Version validation
```

Do not merge a PR when the required CI check is red.

## Troubleshooting

Bot not responding:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

401/403 from 3x-ui: verify the plaintext Bearer API Token.

404 from 3x-ui: verify API base URL, security base path and reverse-proxy routing.

Subscription works but direct config address is wrong: compare SpeedyBot output with 3x-ui **Copy URL**. If both contain the same wrong address, fix Share Address/public host settings in 3x-ui.

## Security

- Never commit `.env`.
- Treat panel API tokens, subscription URLs, proxy URIs, QR codes and snapshots as credentials.
- Use HTTPS for public panel/subscription endpoints.
- Restrict SSH access and keep Ubuntu/3x-ui updated.
- Read [SECURITY.md](SECURITY.md) before public deployment.

## Project structure

```text
SpeedyBot/
├── main.py             # stable v3 business core
├── app.py              # v4 production entrypoint
├── speedybot_v4/       # modular v4 features/UI
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

## License & author

MIT licensed. Created and maintained by **SudoShayanNA**.

- Telegram: **@SudoShayanNA**
- Email: **namayandeshayan@gmail.com**
- GitHub: **https://github.com/roseshayan/SpeedyBot**

If you redistribute or build on SpeedyBot, keeping attribution and the upstream repository link helps users find security fixes and maintained releases.
