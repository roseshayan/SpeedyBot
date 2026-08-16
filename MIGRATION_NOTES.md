# SpeedyBot migration notes

## v3.1.x → v4.0.0

v4 is designed as an **additive migration**. The stable v3 business core remains in `main.py`; the new runtime entrypoint is `app.py`, which installs features from `speedybot_v4/` before polling starts.

### Data preserved

Keep these files exactly as they are:

```text
/root/SpeedyBot/.env
/root/SpeedyBot/speedping.db
```

Existing users, transactions, wallet history, referral history, trials, plan data, notifications and linked services are not deleted.

### New SQLite data

v4 adds:

- `user_blocks`
- `plan_categories`
- `plans.category_id`
- `trial_overrides`
- `customer_feedback`
- `audit_events`
- `broadcast_history`

Existing plans with no category are automatically attached to the default `عمومی` category.

### Upgrade

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
```

The updater creates a deployment backup before replacing runtime files and switches `run.sh` to `app.py` when available.

### Verify after upgrade

```bash
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 100 --no-pager
```

Then test in Telegram:

```text
/start
/sudoadmin
/xuidiag
/groupsdiag
/notifydiag
```

Also open **Appearance & Buttons**, **Plan Categories**, **Operating Mode**, and **Feedback** once to confirm the v4 extension loaded.

### Rollback

If the new service fails its updater health check, `update.sh` attempts to restore the previous source and SQLite database automatically.

Manual deployment backups are under:

```text
/root/SpeedyBot/backups/deploy-YYYYMMDD-HHMMSS/
```

Do not remove these backups until v4 has been running successfully in production.

### No new secrets required

v4 does not require a new environment variable. Premium/Custom Emoji IDs, UI settings, audit Chat ID, categories and operating mode are stored in SQLite.

## v3.0.x → v3.1.0

v3.1 added trial/plan inbound routing, connection guides, acquisition CRM, trial follow-up, custom service names and secure existing-service claims. Migration was additive and required no new environment variables.

## Security reminder

Never publish `.env`, service URLs, proxy URIs, QR codes or read-only panel snapshot files in GitHub Issues.
