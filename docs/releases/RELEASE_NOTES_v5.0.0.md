# SpeedyBot 5.0.0 — reliability and repository maintenance

Release baseline: 2026-11-11. See [the Persian audit and roadmap](../AUDIT_FA.md) for the architecture review and API findings.

## Runtime and dependencies

- Minimum Python version is now **3.11**. Ubuntu 24.04 LTS with Python 3.12 remains a supported installation target.
- Direct dependency versions are pinned to the current stable PyPI releases checked on 2026-11-11: pyTelegramBotAPI 4.37.1, requests 2.34.2, qrcode 8.2 and Pillow 13.0.0.
- Official version sources: [pyTelegramBotAPI](https://pypi.org/project/pyTelegramBotAPI/4.37.1/), [requests](https://pypi.org/project/requests/2.34.2/), [qrcode](https://pypi.org/project/qrcode/8.2/), [Pillow](https://pypi.org/project/Pillow/13.0.0/).

## CI and deployment

- Fixed the tokenless CI test import; tests use isolated configuration and the real installed Telegram library.
- GitHub Actions checks Python 3.11–3.15, installs the release dependencies, verifies dependency consistency, compiles application/tests and runs the offline regression suite.
- Action versions are pinned to verified checkout 7.0.1 and setup-python 7.1.0 commit SHAs. Dependabot maintains Python and Actions updates in grouped pull requests.
- The updater validates a release in a separate fixed-path virtualenv before downtime. Deployment backup includes the previous `.venv` directory or symlink, allowing rollback of dependencies together with code and data.
- Generated runners enter the application directory and let the Python environment loader read `.env`.
- Fresh installation refuses to overwrite an existing configuration; use the updater for an existing bot.

## Repository and compatibility

- Historical release notes are grouped under `docs/releases/`; README versions, project layout and citation metadata are synchronized.
- Shell and source files have consistent LF line endings. Generated environments and deployment metadata are ignored by Git.
- `main.py`, `speedybot/`, `.env`, `speedping.db` and `backups/` retain their existing locations.
- The API audit targets the current official [3x-ui documentation](https://docs.sanaei.dev/). The audit document records compatibility limitations and proposed follow-up features.

## API, configuration and restore fixes

- Panel lookups normalize nested `obj.client` data, partial client updates preserve existing settings, and bulk volume adjustments check actual API results. Link and QR callbacks verify ownership, including shared subscriptions.
- Interrupted renewals and volume additions are held for operator verification rather than replayed automatically; service retries claim the transaction before issuing another request.
- Environment updates validate values, preserve quoted secrets and use atomic writes. Configuration changes are reflected in current runtime requests.
- Privileged callbacks require administrator authorization; trial issuance has persistent recovery state, and backup/restore handles SQLite WAL state safely.
- Backup validation rejects incompatible data before restore. Telegram restore follows the documented 20 MB Bot API download limit.
- CLI restore anchors default paths to the installation, checks service state, stops the running service before replacing its database and restarts it afterward. Custom restore targets do not stop an unrelated bot service.
- Regression coverage includes isolated full-package startup and real Telegram menu serialization, in addition to API, storage, environment and restore cases.
- Mocked deployment tests cover successful updates, directory/symlink virtualenv rollback, partial source-sync failure, virtualenv move failure and validation failures before service downtime.

## Upgrade

Read [migration notes](../../MIGRATION_NOTES.md), copy a backup off the server, then run:

```bash
cd /root/SpeedyBot
./update.sh --check
./update.sh
systemctl status xui-bot.service --no-pager -l
```

Systems with an older Python should select an installed 3.11+ interpreter explicitly: `SPEEDYBOT_PYTHON=/usr/bin/python3.12 ./update.sh`. The updater fails before changing the running bot if this requirement is not met.

Production Telegram/panel integration and real systemd deployment require the operator's server and credentials; offline unit tests do not establish that live integration.
