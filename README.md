# SpeedyBot

An open-source Telegram storefront and admin console for **3x-ui (Sanaei)**. Sell and renew subscriptions, issue trials, and deliver subscription links, direct configs, and QR codes.

[Website and full guide](https://roseshayan.github.io/SpeedyBot/en/) · [فارسی](README_FA.md) · [Changelog](CHANGELOG.md) · [MIT License](LICENSE)

## Quick install

**Before you start.** Use a Linux VPS with systemd and Python 3.11+ (Ubuntu 24.04 LTS recommended) and a running 3x-ui panel with an active inbound. Have your Telegram bot token from [@BotFather](https://t.me/BotFather), your numeric Telegram ID, and a token from **3x-ui → Settings → Security → API Token** ready. The VPS needs outbound access to Telegram and the panel.

For a fresh install, switch to root with `sudo -i` and run these commands.

```bash
apt update
apt install -y git
git clone https://github.com/roseshayan/SpeedyBot.git /root/SpeedyBot
cd /root/SpeedyBot
bash install.sh
```

| Installer prompt | Value to enter |
| --- | --- |
| Telegram bot token / Admin ID | The BotFather token and your numeric Telegram user ID |
| API base URL / security base path | For `https://panel.example.com:2053/private/`, enter `https://panel.example.com:2053` and `/private` separately. Use `/` when there is no hidden path. |
| Panel Bearer API Token | The 3x-ui token value |
| Subscription server / URI path | For `https://sub.example.com:2096/sub/abc`, enter `https://sub.example.com:2096` and `/sub/` separately. Use the actual values from your panel. |

The installer checks the panel API and starts `xui-bot.service`. Confirm it with `systemctl status xui-bot.service --no-pager` and open your bot in Telegram. Send `/start` and then `/sudoadmin` from the owner account. Set the payment details, review plans and inbounds, and test a trial and a purchase before accepting payments.

[Full installation guide](https://roseshayan.github.io/SpeedyBot/en/#install) · [Admin panel guide](https://roseshayan.github.io/SpeedyBot/en/#admin) · [Troubleshooting](https://roseshayan.github.io/SpeedyBot/en/#troubleshooting)

## What you can manage

| In Telegram | What SpeedyBot handles |
| --- | --- |
| Store | Plans, manual receipt approval, wallet checkout, renewals and volume add-ons |
| Customer account | Live usage, subscription links, direct configs, QR codes, and connection guides |
| Control Center | Trial and plan inbounds, verification rules, rewards, CRM, notifications, and backups |

## Update an existing installation

Run these commands as root.

```bash
cd /root/SpeedyBot
bash update.sh --check
bash update.sh
```

The updater stages and tests the new version, preserves `.env` and the live database during source synchronization, and attempts rollback if the service fails to start. See [migration notes](MIGRATION_NOTES.md) and [backup and recovery](https://roseshayan.github.io/SpeedyBot/en/#operations).

Keep tokens, customer configs and database backups private. [Security](SECURITY.md) · [Support](SUPPORT.md) · [Contributing](CONTRIBUTING.md)

Maintained by [SudoShayanNA](AUTHOR.md).
