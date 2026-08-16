# SpeedyBot v4.0.0 — Control Center & Growth Suite

SpeedyBot v4 focuses on **operational control, customer experience and maintainability** while preserving the proven v3 sales/provisioning core.

## ✨ New UI & Control Center

- Cleaner `/sudoadmin` dashboard with grouped actions and readable status summary.
- Cleaner customer account and categorized plan storefront.
- Official Telegram colored button styles: blue (`primary`), green (`success`), red (`danger`) and default.
- Optional Telegram Custom/Premium Emoji IDs on key buttons.
- `/emojiid` helper for extracting Custom Emoji IDs.
- Live Custom Emoji eligibility test before enabling configured Premium Emoji buttons.

## 🛠 Operations

- Operating modes:
  - 🟢 Normal
  - 🟠 Sales Paused
  - 🔴 Maintenance
- Purchase/trial blacklist with stored reason.
- SQLite Audit Log and optional Telegram audit channel.
- Read-only emergency 3x-ui client snapshot export.

## 🛍 Product management

- Plan categories with automatic migration of old plans into a default category.
- Category-based storefront.
- Per-user Trial overrides for GB, days and IP limit.
- Existing Trial inbound selection remains authoritative.

## 📈 Customer & growth tools

- 1–5 star customer feedback with optional comment and admin analytics.
- Targeted broadcasts to:
  - all active users;
  - paying customers;
  - trial users who did not purchase;
  - expired-trial users who did not purchase;
  - users who never purchased.

## 🧱 Architecture

- v3 business core stays in `main.py`.
- v4 additions are modular under `speedybot_v4/`.
- `app.py` installs the extension layer and becomes the production entrypoint.
- This reduces risk for existing installations and makes future modules easier to maintain.

## 🔄 Safer updates

- Updater re-executes from a temporary copy so it can safely replace itself.
- Source is validated before downtime.
- Dependencies are installed before the bot is stopped.
- `.env`, SQLite DB/WAL/SHM, source, docs and v4 modules are backed up.
- The runner automatically uses `app.py` when present and falls back to `main.py` for older builds.
- Failed deployment attempts restore the previous build.

## ✅ CI / tests

GitHub Actions now checks:

- `main.py`, `app.py` and every `speedybot_v4/*.py` file;
- v4 SQLite migration/category tests;
- blacklist lookup;
- broadcast audience segmentation;
- feedback analytics;
- styled/Custom Emoji button payloads;
- `install.sh` and `update.sh` syntax;
- exact release version `4.0.0`.

## 🔒 Notes

- No new required environment variable.
- Migration is additive and keeps existing SpeedyBot business data.
- Panel snapshots and proxy/subscription URLs are sensitive credentials — never publish them.
- Telegram does not expose arbitrary RGB/HEX bot-button colors; v4 uses the official style choices.
- Custom Emoji on bot buttons is subject to Telegram eligibility rules and remains optional.

## Upgrade

After this release is merged/published:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

Then verify:

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 100 --no-pager
```

Open `/sudoadmin` and verify **Operating Mode**, **Plan Categories**, **Feedback**, **Audit Log**, and **Appearance & Buttons**.

---

Created and maintained by **SudoShayanNA**  
Telegram: **@SudoShayanNA**  
Email: **namayandeshayan@gmail.com**  
Repository: **https://github.com/roseshayan/SpeedyBot**
