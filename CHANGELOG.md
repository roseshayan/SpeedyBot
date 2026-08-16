# Changelog

## 4.0.0 — Control Center & Growth Suite

### Added
- Redesigned customer account, categorized storefront and reorganized Telegram admin Control Center.
- Official Telegram button style support (`primary`, `success`, `danger`, default) for key user/admin actions.
- Optional Custom/Premium Emoji IDs for important buttons, `/emojiid` helper and live eligibility testing.
- Operating modes: `NORMAL`, `SALES_PAUSED`, `MAINTENANCE`.
- User purchase/trial restriction (blacklist) with reason and audit events.
- Plan categories with automatic migration of existing plans to a default category.
- Per-user Trial overrides for traffic, days and IP limit while preserving Trial inbound routing.
- Customer feedback: 1–5 stars, optional comment, distribution and average-rating dashboard.
- Targeted broadcasts for active users, customers, Trial leads, expired-Trial leads and users who never purchased.
- SQLite Audit Log with optional Telegram audit channel.
- Read-only emergency 3x-ui client snapshot export.
- Unit tests for migrations, categories, blacklist, audience segmentation, feedback and button payloads.

### Architecture
- v4 is now the **integrated SpeedyBot application**, not a versioned overlay.
- Root `main.py` is the single official production entrypoint.
- Business logic and Control Center modules live in the permanent `speedybot/` package.
- The former `app.py` entrypoint and `speedybot_v4/` directory were removed.
- The previous monolithic business core was moved without functional rewriting to `speedybot/core.py` and is loaded by the integrated entrypoint.
- Tests were renamed from `test_v4_storage.py` to the version-independent `test_storage.py`.

### Installer / updater
- `install.sh` installs the complete repository layout and always runs `main.py`.
- `update.sh` re-executes from a temporary copy before self-update.
- Updates now synchronize the **entire GitHub repository** with `rsync --delete`, rather than maintaining a fragile manual file list.
- Mutable runtime state is excluded from synchronization: `.env`, `.venv/`, SQLite DB/WAL/SHM, `backups/`, `run.sh` and `.deployed_commit`.
- A complete application + runtime rollback backup is created before synchronization.
- Obsolete files/directories are automatically removed during upgrade because the deployed application mirrors the current repository.
- The updater performs Python/shell validation, dependency installation, systemd restart, health checks and automatic rollback on failure.
- GitHub Actions validates the integrated `main.py`, all `speedybot/*.py`, unit tests, shell scripts and repository layout.

### UX
- Admin/user messages and navigation were reorganized for faster scanning and less dense menus.
- Shop and account screens now use the categorized v4 experience.
- Official Telegram button styling and optional Custom Emoji remain backward-safe with normal-text/emoji fallback.

### Security / safety
- Panel Snapshot is intentionally read-only; no destructive one-click restore was added.
- Existing runtime secrets remain in `.env`; v4 introduces no new required secret.
- Blacklisted users retain support/account visibility rather than being silently locked out of help.
- Complete-project updates never overwrite runtime secrets or the production SQLite database from GitHub.

## 3.1.0 — Trial delivery, inbound routing & lightweight CRM

### Fixed
- Corrected free-Trial direct-link delivery using 3x-ui client-link APIs instead of mislabeling subscription URLs.
- Filtered direct links to actual proxy URI schemes.
- Re-synchronized configured Trial/Plan inbounds during idempotent retries.

### Added
- Per-plan and Trial inbound routing.
- Trial on/off switch.
- Admin-managed platform connection guides with text/photo/video.
- Acquisition-source survey and Trial-expiry sales follow-up.
- Custom service names with local/panel duplicate checks.
- Secure existing-service claims via matching `tgId` or admin approval.

## 3.0.0 — Sales & management suite

- Added Sanaei Client Groups (`Customers` / `Trial`).
- Replaced hard-coded plans with SQLite-backed plan management.
- Added 1/2/3-user default monthly unlimited plans and dynamic IP limits.
- Added renewals, optional extra-volume packs and subscription QR codes.
- Added discount codes, gift-wallet codes, cashback, phone verification, membership gating and multiple admins.
- Added automatic backups, expanded analytics and safer GitHub-based updates.

## 2.2.0 — Service notifications

- Added background quota/expiry monitoring, warnings and one-time exhaustion/expiry notices.
- Added persistent notification de-duplication and `/notifydiag`.

## 2.1.0 — Sanaei API compatibility & diagnostics

- Aligned calls with current `/panel/api/*` Bearer-token API.
- Added base-path-safe URL joining, `/xuidiag`, detailed HTTP diagnostics and installer API preflight.
- Corrected Subscription ID handling and configurable subscription path.

## 2.0.0 — Affiliate & Wallet

- Added referral/affiliate links, exactly-once commissions, wallet ledger and wallet checkout.
- Added idempotent provisioning, retry/recovery flows and soft user deactivation.
