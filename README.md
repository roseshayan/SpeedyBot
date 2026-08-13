# SpeedyBot v3

Telegram VPN sales and service-management bot for **3x-ui / Sanaei**.

## Highlights

- Automated paid-client and 1GB/1-day trial provisioning.
- Sanaei Groups integration: paid clients → `Customers`, trials → `Trial`.
- SQLite-backed dynamic plan catalog and admin plan management.
- Default unlimited 30-day plans: 1 user / 250k Toman, 2 users / 300k, 3 users / 350k; `limitIp` matches user count.
- Service renewal with the existing client/subscription identity.
- Optional extra-volume packs for metered services.
- Subscription/direct links plus QR codes.
- Wallet, referral commissions, cashback, discount codes and gift codes.
- Purchase history, service status and expiry/quota notifications.
- Optional phone verification and mandatory-channel membership.
- Multiple bot admins, editable welcome/FAQ, sales analytics and automatic SQLite backups.
- Public-GitHub self updater with backup, validation and rollback.

## Install

```bash
git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
chmod +x install.sh update.sh
./install.sh
```

## Update

```bash
cd /root/SpeedyBot
./update.sh
```

Use `./update.sh --check` to check for a newer commit and `./update.sh --force` to redeploy the latest commit.

## Admin commands

- `/sudoadmin` — main admin panel
- `/xuidiag` — read-only 3x-ui API diagnostics
- `/groupsdiag` — live Sanaei client-group counts
- `/notifydiag` — run notification/service-monitor diagnostics

For full Persian documentation see [README_FA.md](README_FA.md).
