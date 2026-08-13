# SpeedyBot v3 Migration Notes

## Existing production database

The migration is additive. Do not delete `speedping.db` or `.env`.

When v3 starts for the first time it automatically:
- adds the new plan, discount, gift, cashback and admin tables;
- adds new transaction snapshot fields;
- preserves existing users, wallet balances, referrals, trials and transactions;
- seeds three plans only when the `plans` table is empty;
- preserves historical v2.x plan-1 transactions as 30-day unlimited / IP limit 2 snapshots;
- starts background group reconciliation for bot-issued services.

## Default v3 plans

1. Unlimited / 30 days / 1 user — 250,000 Toman — IP limit 1
2. Unlimited / 30 days / 2 users — 300,000 Toman — IP limit 2
3. Unlimited / 30 days / 3 users — 350,000 Toman — IP limit 3

## Sanaei groups

Default target groups:
- paid services: `Customers`
- free trials: `Trial`

Check live panel groups after deployment:

```text
/groupsdiag
```

Or use `/sudoadmin` → Sanaei Groups → Reconcile.

## Upgrade from an existing installation

If GitHub already contains v3:

```bash
cd /root/SpeedyBot
./update.sh
```

If you are uploading this ZIP manually before pushing v3 to GitHub, copy the v3 project files into `/root/SpeedyBot` while preserving `.env`, `speedping.db`, `.venv` and `backups`, then restart the service. The v3 updater refuses an accidental downgrade to an older GitHub VERSION unless `--force` is explicitly used.
