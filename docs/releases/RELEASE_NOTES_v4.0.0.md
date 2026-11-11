# SpeedyBot v4.0.0 — Control Center & Growth Suite

SpeedyBot v4 is a **full-project release** focused on operational control, customer experience, safer updates and maintainability.

Unlike the early v4 development layout, the final release is not shipped as an extension folder on top of v3. **v4 is the application itself.**

## ✨ New UI & Control Center

- Cleaner `/sudoadmin` dashboard with grouped actions and readable status summaries.
- Cleaner customer account and categorized plan storefront.
- Official Telegram button styles: blue (`primary`), green (`success`), red (`danger`) and default.
- Optional Telegram Custom/Premium Emoji IDs on key buttons.
- `/emojiid` helper for extracting Custom Emoji IDs.
- Live Custom Emoji eligibility testing before enabling configured Premium Emoji buttons.

## 🛠 Operations

- Operating modes:
  - 🟢 Normal
  - 🟠 Sales Paused
  - 🔴 Maintenance
- Purchase/Trial blacklist with stored reason.
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
  - Trial users who did not purchase;
  - expired-Trial users who did not purchase;
  - users who never purchased.

## 🧱 Integrated application architecture

- `main.py` is the single official production entrypoint.
- The application package is permanently named `speedybot/`; it is not tied to a release number.
- The previous business core is preserved in `speedybot/core.py` while the v4 Control Center and UX modules live beside it in the same package.
- The temporary development paths `app.py` and `speedybot_v4/` are not part of the final integrated release.
- systemd, manual execution, installer and updater all run the same `main.py` entrypoint.

Final source layout:

```text
SpeedyBot/
├── main.py
├── speedybot/
│   ├── core.py
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
├── install.sh
└── update.sh
```

## 🔄 Complete-project updater

The updater now mirrors the **complete GitHub repository** instead of copying a hard-coded list of files.

- Re-executes from a temporary file before replacing itself.
- Clones the complete GitHub branch to `/tmp`.
- Validates Python and shell source before downtime.
- Installs dependencies before stopping the production bot.
- Creates a complete rollback copy of the currently deployed application.
- Preserves `.env`, SQLite DB/WAL/SHM, `.venv`, `backups/`, `run.sh` and `.deployed_commit`.
- Uses `rsync --delete` so obsolete/renamed source files disappear from the server automatically.
- Writes `run.sh` to execute `main.py` only.
- Restarts systemd and checks for immediate crash loops.
- Restores the previous complete application and database state if deployment fails.

This means the deployed `/root/SpeedyBot` source tree matches the published repository instead of accumulating old version-specific folders.

## ✅ CI / tests

GitHub Actions checks:

- `main.py`;
- every `speedybot/*.py` module;
- SQLite migration/category tests;
- blacklist lookup;
- broadcast audience segmentation;
- feedback analytics;
- styled/Custom Emoji button payloads;
- `install.sh` and `update.sh` shell syntax;
- absence of deprecated `app.py` and `speedybot_v4/` paths;
- exact release version `4.0.0`.

## 🔒 Notes

- No new required environment variable.
- Migration preserves existing SpeedyBot business data.
- Panel snapshots and proxy/subscription URLs are sensitive credentials — never publish them.
- Telegram does not expose arbitrary RGB/HEX bot-button colors; SpeedyBot uses Telegram's official style choices.
- Custom Emoji on bot buttons is subject to Telegram eligibility rules and remains optional.

## Upgrade

For existing installations, first make sure the server is using the latest `update.sh`, then:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

Verify:

```bash
cat VERSION.txt
cat run.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

The runner must point to:

```text
/root/SpeedyBot/main.py
```

Open `/sudoadmin` and verify **Operating Mode**, **Plan Categories**, **Feedback**, **Audit Log**, **Trial & Inbounds**, and **Appearance & Buttons**.

---

Created and maintained by **SudoShayanNA**  
Telegram: **@SudoShayanNA**  
Email: **namayandeshayan@gmail.com**  
Repository: **https://github.com/roseshayan/SpeedyBot**
