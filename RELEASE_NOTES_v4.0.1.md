# SpeedyBot v4.0.1 — Routing & Installer Reliability Patch

A focused reliability update based on real v4 production feedback.

## Fixed

- Direct configs now prefer the real public 3x-ui subscription body, including Base64 subscriptions, so manual configs match the links customers actually receive from Subscription.
- Trial/Plan Inbound selection now shows the real effective state and removes selected Inbounds from actual 3x-ui client membership.
- Attach/Detach operations are verified by re-reading `inboundIds` from 3x-ui; a mismatch is no longer silently reported as success.
- Telegram Bot Token installation UX is clearer: hidden input is explicitly explained, receipt is confirmed without revealing the secret, and invalid tokens can be retried.

## Added

- Global Free Trial traffic / duration / IP-limit settings.
- Safe deletion for unused plans.
- Safe category deletion with automatic plan reassignment.
- Additional routing/subscription unit tests.

Existing `.env`, users, services, transactions and SQLite runtime data remain compatible with v4.0.0.
