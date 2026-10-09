# SpeedyBot v4.3.0 — Card Image Support & Live Panel/Domain Management

This release introduces dynamic card image sending during checkout, in-bot live `.env` and panel domain management, and full compatibility audit with the official Sanaei 3x-ui OpenAPI specification.

## Added

- **Card Image Support**: Admins can register a card photo or QR code via the admin panel (`💳 حساب واریز`).
- **Dynamic Card Photo Checkout**: During card-to-card checkout, the bot sends the card photo with full transaction details as caption.
- **Graceful Fallback**: If no card image is set, or if photo transmission fails, the bot seamlessly falls back to standard text instructions without interrupting checkout.
- **In-Bot Panel & Domain Management**: Added `🌐 پنل و دامنه (.env)` in the admin panel to view and modify panel URLs, paths, and Bearer tokens.
- **Persistent `.env` Synchronization**: Safe, non-destructive `.env` parser and updater (`speedybot/env_manager.py`) that synchronizes changes across database (`settings`), physical `.env` file, and active memory runtime.
- **Global Domain Replacement**: One-click bulk replacement tool (`old_domain | new_domain`) updating all panel endpoints, subscription URLs, and configs simultaneously.
- **Live Panel Connectivity Test**: In-bot diagnostic tool to verify panel connectivity, latency, and retrieve active 3x-ui server and Xray core status.

## Improved

- **Official 3x-ui API Alignment**: Audited all 19 panel API endpoints against the official Sanaei 3x-ui OpenAPI specification (`https://docs.sanaei.dev/openapi.json`), verifying HTTP methods, paths, and request schemas.
- **Dynamic Authentication Headers**: Replaced static global header references with dynamic `_xui_headers()`, ensuring token updates take effect immediately across all background and foreground operations without restarting the service.
- **Dynamic Subscription Links**: Subscription URLs are resolved on-demand using current configuration, ensuring domain migrations immediately apply to existing customer subscriptions.

## Admin Paths

- Card Image Management: `/sudoadmin → 💳 حساب واریز → 🖼 ثبت / تغییر عکس کارت`
- Panel & Domain Settings: `/sudoadmin → 🌐 پنل و دامنه (.env)`
- Bulk Domain Replace: `/sudoadmin → 🌐 پنل و دامنه (.env) → 🔄 تعویض سراسری دامنه`
- Live Panel Test: `/sudoadmin → 🌐 پنل و دامنه (.env) → 🧪 تست اتصال به پنل`

## Update

From your project directory on the server:

```bash
./update.sh
```
