## Summary

## Why is this change needed?

## Testing performed

- [ ] `python3 -m compileall -q main.py restore.py speedybot tests`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m pip check`
- [ ] `for script in install.sh update.sh restore.sh; do bash -n "$script"; done`
- [ ] `bash tests/test_update_shell.sh`
- [ ] No secrets/customer configs are included
- [ ] Documentation/changelog updated when behavior changed

## Compatibility / migration notes
