#!/usr/bin/env bash
set -Eeuo pipefail
# All network, Python and service commands are mocked; only temporary files change.
root="$(cd "${1:-$(dirname "${BASH_SOURCE[0]}")/..}" && pwd)"
base="$(mktemp -d /tmp/speedybot-harness.XXXXXX)"
[[ "$base" == /tmp/speedybot-harness.* ]] || exit 1
trap 'rm -rf -- "$base"' EXIT
export MSYS=winsymlinks:nativestrict
sha=1111111111111111111111111111111111111111
export sha
fixture="$base/fixture"
mkdir -p "$fixture/speedybot" "$fixture/tests"
printf new > "$fixture/main.py"
printf '5.0.0\n' > "$fixture/VERSION.txt"
touch "$fixture/requirements.txt" "$fixture/restore.py"
printf '#!/usr/bin/env bash\ntrue\n' > "$fixture/tests/test_update_shell.sh"
for script in install.sh update.sh restore.sh; do printf '#!/usr/bin/env bash\ntrue\n' > "$fixture/$script"; done
export fixture
python_stub="$base/mock-python"
cat > "$python_stub" <<'PY'
#!/usr/bin/env bash
set -eu
if [[ "${1-}" == '-m' && "${2-}" == 'venv' ]]; then
  mkdir -p "$3/bin"
  cp "$MOCK_PYTHON" "$3/bin/python3"
elif [[ "${1-}" == '-m' && "${2-}" == 'pip' && "${MODE-}" == 'depfail' && "$*" == *requirements.txt* ]]; then
  exit 31
elif [[ "${1-}" == '-m' && "${2-}" == 'unittest' && "${MODE-}" == 'testfail' ]]; then
  exit 32
fi
PY
chmod +x "$python_stub"
export MOCK_PYTHON="$python_stub"
git(){
  if [[ "$1" == 'ls-remote' ]]; then printf '%s\trefs/heads/main\n' "$sha";
  elif [[ "$1" == 'clone' ]]; then local dest="${@: -1}"; mkdir -p "$dest"; cp -a "$fixture/." "$dest/";
  elif [[ "$1" == '-C' ]]; then printf '%s\n' "$sha";
  else return 2; fi
}
keep(){ case "$1" in .git|.env|.venv|.venvs|backups|speedping.db|speedping.db-wal|speedping.db-shm|run.sh|.deployed_commit|__pycache__|*.log) return 0 ;; *) return 1 ;; esac; }
rsync(){
  local source="${@: -2:1}" dest="${@: -1}" item
  mkdir -p "$dest"
  if [[ "${MODE-}" == 'syncfail' && "$source" == */repo/ ]]; then printf partial > "$dest/main.py"; return 36; fi
  shopt -s dotglob nullglob
  for item in "$dest"/*; do keep "${item##*/}" || rm -rf -- "$item"; done
  for item in "$source"/*; do keep "${item##*/}" || cp -a "$item" "$dest/"; done
}
systemctl(){
  printf '%s\n' "$*" >> "$MOCK_LOG"
  if [[ "$1" == 'is-active' && "$MODE" == 'healthfail' ]]; then return 1; fi
  [[ "$1" != 'show' ]] || printf '0\n'
  return 0
}
mv(){ if [[ "${MODE-}" == 'movefail' && "${@: -2:1}" == */.venv ]]; then return 35; fi; command mv "$@"; }
sleep(){ :; }
journalctl(){ :; }
export -f git keep rsync systemctl mv sleep journalctl
# The only adaptation is bypassing the Linux root guard for this Windows harness.
sed '/^\[\[ "\$EUID" -eq 0 \]\] || fail /c\:' "$root/update.sh" > "$base/updater.sh"
for scenario in directory-success directory-healthfail symlink-healthfail directory-depfail directory-testfail directory-syncfail symlink-movefail; do
  app="$base/$scenario"
  mkdir -p "$app/.venv/bin"
  printf 'old-env\n' > "$app/.venv/marker"
  cp "$python_stub" "$app/.venv/bin/python3"
  if [[ "$scenario" == symlink-* ]]; then
    mkdir -p "$app/.venvs"
    mv "$app/.venv" "$app/.venvs/previous"
    ln -s "$app/.venvs/previous" "$app/.venv"
  fi
  printf 'old\n' > "$app/main.py"
  printf 'old-secret\n' > "$app/.env"
  printf 'old-db\n' > "$app/speedping.db"
  printf '4.3.0\n' > "$app/VERSION.txt"
  export MODE="${scenario#*-}" MOCK_LOG="$base/$scenario.log"
  : > "$MOCK_LOG"
  set +e
  SPEEDYBOT_UPDATER_REEXEC=1 SPEEDYBOT_APP_DIR="$app" SPEEDYBOT_PYTHON="$python_stub" bash "$base/updater.sh" > "$base/$scenario.output" 2>&1
  code=$?
  set -e
  [[ "$(cat "$app/.env")" == old-secret && "$(cat "$app/speedping.db")" == old-db ]]
  if [[ "$MODE" == 'success' ]]; then
    [[ "$code" -eq 0 && -L "$app/.venv" && "$(cat "$app/main.py")" == new ]]
    [[ "$(cat "$app"/backups/deploy-*/venv/marker)" == old-env ]]
  else
    [[ "$code" -ne 0 && "$(cat "$app/main.py")" == old && "$(cat "$app/.venv/marker")" == old-env ]]
    if [[ "$MODE" == 'healthfail' || "$MODE" == 'syncfail' ]]; then
      grep -q 'restart xui-bot.service' "$MOCK_LOG"
      if [[ "$scenario" == symlink-* ]]; then [[ -L "$app/.venv" ]]; else [[ ! -L "$app/.venv" ]]; fi
    else
      if [[ "$MODE" != 'movefail' ]]; then [[ ! -s "$MOCK_LOG" ]]; else [[ -L "$app/.venv" ]]; fi
    fi
  fi
  printf 'PASS %s\n' "$scenario"
done
