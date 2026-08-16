# Changelog

## 3.1.0 - Trial delivery, inbound routing & lightweight CRM

### Fixed
- Fixed free-trial direct-link delivery. SpeedyBot now retrieves direct protocol URLs from the official 3x-ui client link APIs instead of treating a subscription URL as a direct configuration.
- Filters direct-delivery results to actual proxy URI schemes (`vless://`, `vmess://`, `trojan://`, `ss://`, `hysteria://`, `hysteria2://`, `hy2://`).
- Retry/idempotent provisioning now re-syncs an existing client to the configured Trial/Plan inbound set instead of leaving stale inbound attachments.

### Added
- Per-purpose inbound routing from the Telegram admin panel:
  - choose inbounds used for free trials;
  - choose a different inbound set for every plan;
  - reset a scope to “all active inbounds”;
  - renewals can move the existing client to the inbound set of the selected renewal plan.
- Admin switch to enable/disable free trials without editing source code.
- Platform-specific connection guides managed entirely from Telegram admin:
  - Android, iOS/iPhone, Windows, macOS, Linux and Android TV/TV Box;
  - text, photo and video items using Telegram file IDs, plus preview/reordering;
  - automatic guide CTA after paid/trial delivery plus a permanent user-menu entry.
- Optional acquisition survey after the first successful paid purchase (“How did you hear about us?”) with admin analytics.
- Trial-expiry sales follow-up CRM:
  - configurable on/off switch and delay (1–168 hours);
  - skips users who already purchased;
  - asks structured reasons for not buying;
  - provides purchase/support CTA;
  - works even when service-expiry notification messages are disabled.
- Optional custom service names during purchase, with server-side validation and duplicate-name detection against both the local database and 3x-ui.
- Secure linking of previously purchased/existing 3x-ui clients to a Telegram account:
  - automatic claim when the panel client `tgId` matches the Telegram user;
  - otherwise an admin approval workflow is created;
  - one panel client cannot be claimed by multiple bot users.
- Linked external services appear in the user account and are included in service monitoring.
- Expanded CRM dashboard with acquisition response rate, follow-up counts, pre-follow-up conversions, linked-service count and pending claims.

### Security / behavior notes
- Existing-service import does not trust a typed email alone; ownership is verified by `tgId` or explicit admin approval.
- Direct proxy URLs and subscription URLs remain separate concepts in UI and delivery.
- No new environment variables are required. SQLite schema migration is automatic at startup.

## 3.0.0 - Sales & management suite

- Added Sanaei client-group integration using the official Clients Groups API.
  - Paid services are assigned to `Customers`.
  - Free trials are assigned to `Trial`.
  - `/groupsdiag` and the admin Groups screen show the live group count and member counts.
  - Startup reconciliation migrates previously issued bot services into the correct groups.
- Replaced hard-coded plans with SQLite-backed plan management.
  - Default catalog: unlimited 30-day plans for 1/2/3 users at 250k/300k/350k Toman.
  - `limitIp` is 1/2/3 respectively.
  - Admins can add, edit, enable or disable plans.
- Added service renewal while preserving the existing subscription identity.
  - Early renewals extend from the later of current expiry or now.
  - Renewal updates quota/IP limit, re-enables the client and resets the new period traffic.
- Added optional extra-volume packs for limited-volume plans.
- Added QR generation for subscription links.
- Added user purchase history and improved service/account views.
- Added discount codes, gift-wallet codes and configurable cashback.
- Added phone-number verification and mandatory Telegram-channel membership gates (disabled by default).
- Added multiple bot admins; the original `ADMIN_ID` remains Owner.
- Added configurable welcome/FAQ content and configurable deterministic/random service usernames.
- Added automatic SQLite backups with retention plus manual admin backup.
- Expanded sales analytics with purchase/renewal/volume breakdown, today's revenue and live panel group/online counts.
- Added safe public-GitHub updater (`./update.sh`) with pre-deploy validation, backups and rollback.
- Tightened safety/idempotency around wallet refunds, receipt retry, subscription IDs and notification tracking.

## 2.2.0 - Service notifications

- Added automatic background monitoring for bot-issued paid and trial services.
- Uses one `GET /panel/api/clients/list` request per monitoring cycle to read quota, traffic and expiry.
- Sends one-time volume warning at 90% usage.
- Sends one-time expiry warning at 24 hours for paid services and 3 hours for free trials.
- Sends one-time notifications when traffic quota is exhausted or expiry time is reached.
- Prevents duplicate notifications across bot/server restarts using the `service_notifications` SQLite table.
- Marks exhausted/expired free trials as `EXPIRED` while retaining their anti-abuse history.
- Added `/notifydiag` for a manual admin-side service check.
- Added `🔔 اعلان سرویس‌ها` admin panel with toggle and manual check.
- Monitoring interval defaults to 5 minutes and is stored in DB settings.


## 2.1.0 - Sanaei API compatibility & diagnostics

- Aligned all 3x-ui calls with the current `/panel/api/*` REST API documentation.
- Added safe web-base-path URL joining for installations with a hidden panel path.
- Added `/xuidiag` admin command for read-only Inbounds/Clients API diagnostics.
- Added explicit HTTP 401/403/404/5xx diagnostics without exposing the Bearer token.
- Added installer API preflight so invalid Bearer tokens/base paths are caught before the bot service starts.
- `update.sh` now refreshes project scripts/docs/version files while preserving `.env`, database, virtualenv and backups.
- Fixed `install.sh` self-copy failure when the installer is already located in `/root/SpeedyBot`.
- Added configurable `XUI_SUB_PATH` because the 3x-ui subscription URI path is configurable.
- Stopped treating client UUID/ID as a subscription ID; subscription URLs now use `subId` only.
- Added traffic-endpoint fallback for retrieving `subId`.
- URL-encode client emails in API paths.

## 2.0.0 - Affiliate & Wallet

- Added one-level referral / affiliate program with permanent invitation codes.
- Added Telegram deep links (`/start ref_<code>`).
- Referral is bound only on the invitee's first-ever bot registration.
- Added configurable referral commission percentage (default: 10%).
- Commission is credited only after a cash-backed purchase is approved and the X-UI service is successfully provisioned.
- Added exactly-once commission protection per purchase transaction.
- Added wallet balance and immutable wallet ledger/history.
- Added direct plan purchase from wallet when balance is sufficient.
- Wallet-funded purchases do not create a new referral commission, preventing circular credit generation.
- Added admin affiliate dashboard, enable/disable, commission percentage, wallet adjustment, and top affiliates.
- Added safe ISSUE/Retry flow for failed service provisioning.
- Added wallet refund action for failed wallet purchases, only when no client exists on X-UI.
- Paid service provisioning is idempotent to prevent duplicate X-UI clients during retries/restarts.
- Added startup recovery for transactions left in PROCESSING.
- Added startup reconciliation for approved purchases whose referral commission was interrupted before credit.
- User removal is now a soft deactivation so financial/referral/trial history cannot be reset for abuse.
- Added `update.sh` for safe server upgrades while preserving `.env` and `speedping.db`.
