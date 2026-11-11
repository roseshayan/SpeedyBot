# Contributing to SpeedyBot

Thanks for helping improve SpeedyBot.

## Recommended workflow

1. Fork the repository.
2. Create a focused branch.
3. Keep changes small and explain the reason for them.
4. Never commit `.env`, API tokens, bot tokens, databases or real subscription URLs.
5. Use Python 3.11+ and run the release checks before opening a PR:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m compileall -q main.py restore.py speedybot tests
python -m unittest discover -s tests -v
for script in install.sh update.sh restore.sh; do bash -n "$script"; done
bash tests/test_update_shell.sh
```

6. Update documentation and `CHANGELOG.md` when behavior changes.
7. Open a Pull Request with reproduction/testing details.

Unit tests run offline with temporary configuration/databases; do not configure production tokens for tests. CI runs the same checks on Python 3.11–3.15 using the real release dependencies.

Application code belongs in `speedybot/`, regression tests in `tests/`, architecture/audit notes in `docs/`, and version notes in `docs/releases/`. Keep the production entrypoint and runtime data paths stable. Update `VERSION.txt`, `speedybot.VERSION`, citation metadata and release documentation together when cutting a release.

For security vulnerabilities, follow `SECURITY.md` instead of opening a public Issue.

Maintainer: **SudoShayanNA** — https://github.com/roseshayan/SpeedyBot
