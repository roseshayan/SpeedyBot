# SpeedyBot migration notes

## v3.1.x → v4.0.0

SpeedyBot v4 is now shipped as **one integrated application**, not as a versioned extension layer.

The production entrypoint remains the familiar root file:

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

### Important when upgrading from the earlier v4 overlay build

The updater automatically removes obsolete source paths such as:

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
