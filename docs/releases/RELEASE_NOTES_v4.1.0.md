# SpeedyBot v4.1.0 — White-label Branding & Customer Menu Controls

This release makes customer-facing deployments easier to white-label and lets each operator decide which customer menu actions should be visible.

## Added

- White-label brand name setting, managed directly from the Telegram admin panel.
- New **Brand & Customer Menu** admin section.
- Independent visibility controls for:
  - Buy plans
  - Account
  - Free trial
  - Affiliate
  - Connection guide
  - FAQ/help
  - Gift/discount code
  - Feedback/rating
  - Support
- One-click reset to show all customer menu buttons again.
- Customer menu rows are rebuilt dynamically so hidden buttons do not leave empty gaps.

## Changed

- The admin Control Center title now uses the configured brand instead of a hard-coded SpeedyBot title.
- The categorized storefront title now uses the configured brand instead of `SpeedPing`.
- Hiding the feedback/rating entry also removes it from the account screen and blocks stale feedback callbacks.
- Untouched legacy `SpeedPing` welcome/FAQ defaults are migrated to neutral white-label copy during upgrade.
- Admin-customized welcome and FAQ text is preserved by the migration.

## Upgrade notes

After updating, open:

`/sudoadmin → 🏷 برند و منوی مشتری`

Set the deployment brand name, then toggle any customer buttons that should not be shown.

The existing full feedback feature switch remains available under **Customer Feedback**. Menu visibility and feature enablement are intentionally separate controls.
