# Changelog

## 4.0.0 — Control Center & Growth Suite

### Added
- Modular v4 extension architecture with `app.py` + `speedybot_v4/`, leaving the stable v3 core in `main.py` intact.
- Redesigned customer account, categorized storefront and reorganized Telegram admin Control Center.
- Official Telegram button style support (`primary`, `success`, `danger`, default) for key user/admin actions.
- Optional Custom/Premium Emoji IDs for important buttons, `/emojiid` helper and a live eligibility test before activation.
- Operating modes: `NORMAL`, `SALES_PAUSED`, `MAINTENANCE`.
- User purchase/trial restriction (blacklist) with reason and audit events.
- Plan categories with migration of existing plans to a default category.
- Per-user trial overrides for traffic, days and IP limit while preserving Trial inbound routing.
- Customer feedback: 1–5 stars, optional comment, distribution and average-rating dashboard.
- Targeted broadcasts for all active users, customers, trial leads, expired-trial leads and users who never purchased.
- SQLite Audit Log with optional Telegram audit channel.
- Read-only emergency 3x-ui client snapshot export.
- v4 unit tests for migrations, categories, blacklist, audience segmentation, feedback and button payloads.

### Changed
- `install.sh` can deploy the modular v4 runtime and still supports the existing v3 layout.
- `update.sh` now re-executes from a temporary copy, validates the modular source before downtime, backs up v4 directories and falls back to the previous build on deployment failure.
- `run.sh` uses `app.py` when available and falls back to `main.py` for older builds.
- GitHub Actions validates `main.py`, `app.py`, all `speedybot_v4/*.py`, unit tests, shell syntax and the release version.
- Admin/user messages and navigation have been reorganized for faster scanning and fewer dense menus.

### Security / safety
- Panel Snapshot is intentionally read-only; no destructive one-click restore was added.
- Existing runtime secrets remain in `.env`; v4 introduces no new required secret.
- Blacklisted users retain support/account visibility rather than being silently locked out of help.
- Custom Emoji is optional and has a normal-text/emoji fallback.

## 3.1.0 — Trial delivery, inbound routing & lightweight CRM

### Fixed
- Corrected free-trial direct-link delivery using 3x-ui client-link APIs instead of mislabeling subscription URLs.
- Filtered direct links to actual proxy URI schemes.
- Re-synchronized configured Trial/Plan inbounds during idempotent retries.

### Added
- Per-plan and Trial inbound routing.
- Trial on/off switch.
- Admin-managed platform connection guides with text/photo/video.
- Acquisition-source survey and trial-expiry sales follow-up.
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
