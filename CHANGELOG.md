# Changelog

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
