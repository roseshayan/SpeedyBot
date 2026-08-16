# Contributing to SpeedyBot

Thanks for helping improve SpeedyBot.

## Recommended workflow

1. Fork the repository.
2. Create a focused branch.
3. Keep changes small and explain the reason for them.
4. Never commit `.env`, API tokens, bot tokens, databases or real subscription URLs.
5. Run syntax checks before opening a PR:

```bash
python3 -m py_compile main.py
bash -n install.sh
bash -n update.sh
```

6. Update documentation and `CHANGELOG.md` when behavior changes.
7. Open a Pull Request with reproduction/testing details.

For security vulnerabilities, follow `SECURITY.md` instead of opening a public Issue.

Maintainer: **SudoShayanNA** — https://github.com/roseshayan/SpeedyBot
