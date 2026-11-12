# SpeedyBot migration notes

## v4.x → v5.0.0

1. Ensure **Python 3.11+** is installed. Current pyTelegramBotAPI and Pillow require it. Ubuntu 24.04's Python 3.12 is supported.
2. Copy a verified database/configuration backup to another machine. Keep `.env`, `speedping.db` and `backups/` in their existing locations.
3. Refresh the updater from the v5 release before upgrading; older updater copies do not include dependency rollback:

```bash
cd /root/SpeedyBot
cp -a update.sh update.sh.pre-v5
curl -fsSL https://raw.githubusercontent.com/roseshayan/SpeedyBot/main/update.sh -o update.sh
chmod 700 update.sh
bash -n update.sh
./update.sh --check
./update.sh
```

If the system default Python is older, use `SPEEDYBOT_PYTHON=/usr/bin/python3.12 ./update.sh` after installing the interpreter and matching venv package.

The updater creates the new environment under `.venvs/<deployment>/`, runs validation before stopping the bot, and changes `.venv` to point at it. The preceding `.venv` directory or symlink is retained in the deployment backup. A failed deployment attempts to restore code, database/configuration and the preceding environment together. Old environments are retained; clean them only after verifying the release and its backup.

Generated `run.sh` enters the application directory; Python loads `.env` using the application parser. Existing shell-style `export KEY='value'` settings remain supported. Avoid shell commands inside `.env`; store only configuration assignments.

Historical release notes moved to [docs/releases](docs/releases/README.md). There is no version-numbered runtime package and no database relocation. Read the [v5 release notes](docs/releases/RELEASE_NOTES_v5.0.0.md) and [API audit](docs/AUDIT_FA.md), then verify `/start`, `/sudoadmin`, `/xuidiag`, checkout, renewals and backup on the real bot.

## v3.1.x → v4.0.0

SpeedyBot v4 is shipped as **one integrated application**, not as a versioned extension layer.

The production entrypoint is:

```text
/root/SpeedyBot/main.py
```

Application modules live in the permanent, version-independent package:

```text
/root/SpeedyBot/speedybot/
```

There is no `app.py` runtime and no `speedybot_v4/` package in the integrated layout.

### Data preserved

Do not delete or replace these runtime files:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
/root/SpeedyBot/speedping.db-wal
/root/SpeedyBot/speedping.db-shm
/root/SpeedyBot/backups/
```

Existing users, transactions, wallet history, referral history, trials, plans, notifications, linked services, CRM data and settings are preserved.

### New SQLite data in v4

v4 adds:

- `user_blocks`
- `plan_categories`
- `plans.category_id`
- `trial_overrides`
- `customer_feedback`
- `audit_events`
- `broadcast_history`

Existing plans without a category are automatically assigned to the default `عمومی` category.

### Complete-project updater

The integrated updater synchronizes the **entire repository** instead of maintaining a manual list of files.

It uses `rsync --delete` so removed/renamed source files are also removed from the server. Mutable runtime data is explicitly excluded and preserved:

- `.env`
- `.venv/`
- SQLite DB/WAL/SHM
- `backups/`
- `run.sh`
- `.deployed_commit`

Before synchronization, the updater:

1. Clones the latest GitHub branch to `/tmp`.
2. Validates `main.py`, all `speedybot/*.py`, `install.sh` and `update.sh`.
3. Installs dependencies before downtime.
4. Stops the systemd service.
5. Creates a complete rollback backup of the deployed application plus runtime database/environment state.
6. Synchronizes the full repository.
7. Rewrites `run.sh` to execute `main.py`.
8. Restarts and health-checks the service.
9. Restores the previous complete application if deployment fails.

### One-time updater refresh for older installations

Older SpeedyBot installations may still have the pre-integrated updater that copies a fixed list of files. That updater cannot deploy the new `speedybot/` package correctly.

Before the **first** upgrade to the integrated layout, replace only the updater file in the existing installation directory:

```bash
cd /root/SpeedyBot
cp -a update.sh update.sh.pre-integrated-v4
curl -fsSL https://raw.githubusercontent.com/roseshayan/SpeedyBot/main/update.sh -o update.sh
chmod 700 update.sh
bash -n update.sh
```

This does **not** create another SpeedyBot installation and does not use a second application directory. It only refreshes `/root/SpeedyBot/update.sh` in place.

After that, all future releases can use the normal updater directly.

### Important when upgrading from the earlier v4 overlay build

The integrated updater automatically removes obsolete source paths such as:

```text
app.py
speedybot_v4/
tests/test_v4_storage.py
```

because they are no longer part of the repository. Their replacement paths are:

```text
main.py
speedybot/
tests/test_storage.py
```

### Upgrade

After the one-time updater refresh (if required):

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

### Verify after upgrade

```bash
cat /root/SpeedyBot/VERSION.txt
cat /root/SpeedyBot/run.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 150 --no-pager
```

Expected runner target:

```text
/root/SpeedyBot/main.py
```

Expected version:

```text
4.0.0
```

Then test in Telegram:

```text
/start
/sudoadmin
/xuidiag
/groupsdiag
/notifydiag
```

Also verify plan categories, operating mode, feedback, Trial/Inbound settings and Appearance & Buttons.

### Rollback

Deployment backups are stored under:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

The updater automatically attempts rollback when the newly deployed service does not stay healthy.

Do not remove the latest deployment backup until the new version has been verified in production.

### No new secrets required

v4 does not require a new environment variable. UI settings, Custom Emoji IDs, Audit Chat ID, categories and operating mode are stored in SQLite.

## v3.0.x → v3.1.0

v3.1 added Trial/Plan inbound routing, connection guides, acquisition CRM, Trial follow-up, custom service names and secure existing-service claims. Migration was additive and required no new environment variables.

## Security reminder

Never publish `.env`, API tokens, service URLs, proxy URIs, QR codes or panel snapshot files in GitHub Issues.
