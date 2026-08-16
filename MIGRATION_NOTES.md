# SpeedyBot migration notes

## v3.0.x → v3.1.0

No new environment variables are required. Keep your existing `.env` and `speedping.db`.

On first start, SpeedyBot automatically creates the new SQLite tables used for:

- Trial inbound routing (`trial_inbounds`)
- Per-plan inbound routing (`plan_inbounds`)
- Platform connection-guide content (`guide_items`)
- Acquisition/source survey (`user_acquisition`)
- Trial sales follow-ups (`trial_followups`)
- Existing-service links (`linked_services`)
- Existing-service ownership claims (`service_claims`)

New settings are seeded safely with these defaults:

- Free trial: enabled
- Connection guides: enabled
- Acquisition survey: enabled
- Trial follow-up: enabled
- Trial follow-up delay: 6 hours
- Custom service names: enabled
- Link existing service: enabled

If an inbound selector has no explicit rows, SpeedyBot preserves backward-compatible behavior and uses **all active inbounds**. Selecting specific inbounds in `/sudoadmin` changes that scope to the chosen list.

### Recommended upgrade procedure

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
systemctl status xui-bot.service --no-pager -l
journalctl -u xui-bot.service -n 100 --no-pager
```

After upgrade, open `/sudoadmin` and review:

1. `🧪 تست و Inboundها`
2. `📲 راهنمای اتصال`
3. `📈 CRM و پیگیری`
4. `👥 گروه‌های Sanaei`

Then test one free trial with a new Telegram account and verify that the returned direct URLs match 3x-ui's **Copy URL** output for the selected inbounds.

## Rollback

`update.sh` creates a timestamped backup before deployment. If the new service does not remain healthy, the updater attempts automatic rollback. Runtime data (`.env`, SQLite database and backups) is not replaced by repository defaults.
