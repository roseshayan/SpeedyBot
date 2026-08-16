# SpeedyBot v3.1.0 — Smarter Trials, Inbound Routing & CRM

This release focuses on real-world feedback from public users of the project and improves the complete journey from **trial → connection → follow-up → conversion**.

## 🐛 Fixed

- Fixed incorrect/missing direct configuration addresses in free-trial delivery.
- Direct links are now read from the official 3x-ui client link endpoints and filtered to real proxy URI schemes.
- Subscription URLs are no longer presented as if they were direct proxy configurations.
- Existing clients found during retry are re-synchronized to the correct inbound selection.

## 🧭 Inbound routing

- Select which inbounds are used for free trials.
- Select a separate inbound set for every plan.
- Reset any scope to all active inbounds.
- Renewing to another plan also synchronizes the service to that plan's inbound set.

## 🎁 Trial controls

- Enable or disable the free-trial feature directly from `/sudoadmin`.
- The trial menu button disappears automatically when the feature is disabled.

## 📲 Managed connection guides

Admins can build per-platform tutorials directly inside Telegram:

- Android
- iPhone / iOS
- Windows
- macOS
- Linux
- Android TV / TV Box

Each platform can contain multiple text, photo and video items with preview and manual ordering. A guide button is shown after service delivery and in the user's account/menu.

## 📈 Lightweight CRM

- Optional post-purchase “How did you hear about us?” survey.
- Source analytics in the admin panel.
- Automatic trial-expiry follow-up after a configurable delay.
- Users who already bought are skipped automatically.
- Structured reasons for not purchasing + support/purchase CTA.
- Follow-up detection remains active even if normal service-expiry notifications are disabled.

## 🏷 Service ownership & naming

- Users can choose a custom service name during purchase.
- Duplicate names are checked against both SpeedyBot and 3x-ui before checkout.
- Users can link a previously purchased 3x-ui client to their bot account.
- Ownership is automatically accepted only when `tgId` matches; otherwise an admin must approve the claim.

## 📊 Admin improvements

The CRM dashboard now shows survey response rate, follow-up activity, users who converted before a follow-up, linked external services and pending ownership claims.

## Upgrade

```bash
cd /root/SpeedyBot
./update.sh
```

No new `.env` values are required. Database migration is automatic.

---

Created and maintained by **SudoShayanNA**  
Telegram: `@SudoShayanNA`  
Email: `namayandeshayan@gmail.com`  
Repository: https://github.com/roseshayan/SpeedyBot
