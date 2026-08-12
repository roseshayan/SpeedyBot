#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="xui-bot.service"
APP_DIR="/root/SpeedyBot"
ENV_FILE="$APP_DIR/.env"
RUNNER_FILE="$APP_DIR/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
NC="\033[0m"

info()    { printf "${BLUE}[INFO]${NC} %s\n" "$*"; }
success() { printf "${GREEN}[OK]${NC} %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC} %s\n" "$*" >&2; }
error()   { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

trap 'error "Installation failed at line $LINENO. Check the message above."' ERR

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    error "Please run this script as root."
    exit 1
  fi
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

prompt_value() {
  local prompt="$1"
  local default="${2-}"
  local value=""
  while true; do
    if [[ -n "$default" ]]; then
      read -r -p "$prompt [$default]: " value || true
      value="$(trim "${value:-$default}")"
    else
      read -r -p "$prompt: " value || true
      value="$(trim "${value:-}")"
    fi
    if [[ -n "$value" ]]; then
      printf '%s' "$value"
      return 0
    fi
    warn "Value cannot be empty."
  done
}

prompt_secret() {
  local prompt="$1"
  local value=""
  while true; do
    # Write prompt to stderr so it doesn't get captured by command substitution
    printf "%s: " "$prompt" >&2
    read -r value || true
    printf '\n' >&2
    value="$(trim "${value:-}")"
    if [[ -n "$value" ]]; then
      printf '%s' "$value"
      return 0
    fi
    warn "Value cannot be empty."
  done
}

validate_bot_token() {
  [[ "$1" =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]]
}

prompt_bot_token() {
  local value
  while true; do
    value="$(prompt_secret "Telegram bot token")"
    # Remove any possible whitespace or control characters (just in case)
    value="$(echo "$value" | tr -d '\n\r\t')"
    if validate_bot_token "$value"; then
      printf '%s' "$value"
      return 0
    fi
    warn "Invalid Telegram bot token format. Example: 123456789:AAAbbbCCC..."
  done
}

validate_admin_id() {
  [[ "$1" =~ ^[0-9]+$ ]] && [[ "$1" != "0" ]]
}

prompt_admin_id() {
  local value
  while true; do
    value="$(prompt_value "Telegram admin numeric ID")"
    if validate_admin_id "$value"; then
      printf '%s' "$value"
      return 0
    fi
    warn "Admin ID must be a positive numeric Telegram user ID."
  done
}

validate_base_url() {
  local value="$1"
  [[ "$value" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?/?$ ]]
}

normalize_base_url() {
  local value="$1"
  value="${value%/}"
  printf '%s' "$value"
}

prompt_base_url() {
  local value
  while true; do
    value="$(prompt_value "X-UI API base URL (scheme + host + port only, no path)" "http://127.0.0.1:2053")"
    value="$(normalize_base_url "$value")"
    if validate_base_url "$value"; then
      printf '%s' "$value"
      return 0
    fi
    warn "Invalid URL. Use a value like http://127.0.0.1:2053 or https://panel.example.com:2053"
  done
}

validate_base_path() {
  local value="$1"
  [[ -n "$value" ]]
  [[ "$value" == "/" || "$value" =~ ^/[^[:space:]]*$ ]]
}

normalize_base_path() {
  local value="$1"
  value="$(trim "$value")"
  [[ -z "$value" ]] && value="/"
  [[ "$value" != "/" ]] && value="${value%/}"
  [[ -z "$value" ]] && value="/"
  printf '%s' "$value"
}

prompt_base_path() {
  local value
  while true; do
    value="$(prompt_value "X-UI security base path (use / if none)" "/")"
    value="$(normalize_base_path "$value")"
    if validate_base_path "$value"; then
      printf '%s' "$value"
      return 0
    fi
    warn "Base path must start with / and must not contain spaces."
  done
}

validate_sub_url() {
  local value="$1"
  [[ "$value" =~ ^https?://[^[:space:]/?#]+(:[0-9]{1,5})?/?$ ]]
}

normalize_sub_url() {
  local value="$1"
  value="${value%/}"
  printf '%s' "$value"
}

prompt_sub_url() {
  local value
  while true; do
    value="$(prompt_value "Subscription server base URL (scheme + host + port only, no /sub path)" "https://sub.example.com:2096")"
    value="$(normalize_sub_url "$value")"
    if validate_sub_url "$value"; then
      printf '%s' "$value"
      return 0
    fi
    warn "Invalid subscription URL. Use a value like https://sub.example.com:2096"
  done
}

normalize_sub_path() {
  local value="$1"
  value="$(trim "$value")"
  [[ -z "$value" ]] && value="/sub/"
  [[ "$value" != /* ]] && value="/$value"
  [[ "$value" != */ ]] && value="$value/"
  printf '%s' "$value"
}

prompt_sub_path() {
  local value
  while true; do
    value="$(prompt_value "Subscription URI path (Settings -> Subscription)" "/sub/")"
    value="$(normalize_sub_path "$value")"
    if [[ "$value" =~ ^/[^[:space:]]*/$ ]]; then
      printf '%s' "$value"
      return 0
    fi
    warn "Invalid subscription path. Example: /sub/"
  done
}

prompt_bearer_token() {
  local value
  while true; do
    value="$(prompt_secret "Panel Bearer API Token (plaintext value, NOT token name)")"
    # Remove any possible whitespace or control characters
    value="$(echo "$value" | tr -d '\n\r\t')"
    if [[ -n "$value" ]]; then
      printf '%s' "$value"
      return 0
    fi
    warn "Bearer token cannot be empty."
  done
}

safe_export_line() {
  local key="$1"
  local value="$2"
  printf 'export %s=%q\n' "$key" "$value"
}

confirm() {
  local answer
  while true; do
    read -r -p "$1 [y/N]: " answer || true
    answer="$(trim "${answer:-}")"
    case "${answer,,}" in
      y|yes) return 0 ;;
      n|no|"") return 1 ;;
      *) warn "Please answer yes or no." ;;
    esac
  done
}

main() {
  require_root

  if ! command_exists apt-get; then
    error "apt-get was not found."
    exit 1
  fi

  if [[ ! -f "$SOURCE_DIR/main.py" ]]; then
    error "main.py was not found next to install.sh."
    exit 1
  fi

  if [[ -f "$SERVICE_FILE" ]]; then
    warn "An existing $SERVICE_NAME service was found. It will be replaced."
  fi

  echo
  echo "============================================================"
  echo " SpeedPing Telegram Bot installer"
  echo " Ubuntu 24.04 + current Sanaei/3x-ui /panel/api/* REST API"
  echo "============================================================"
  echo

  BOT_TOKEN="$(prompt_bot_token)"
  ADMIN_ID="$(prompt_admin_id)"
  XUI_API_URL="$(prompt_base_url)"
  XUI_BASE_PATH="$(prompt_base_path)"
  XUI_BEARER_TOKEN="$(prompt_bearer_token)"
  XUI_SUB_SERVER_URL="$(prompt_sub_url)"
  XUI_SUB_PATH="$(prompt_sub_path)"

  echo
  info "Summary:"
  printf '  Bot token:              %s\n' "********"
  printf '  Admin ID:               %s\n' "$ADMIN_ID"
  printf '  X-UI API URL:           %s\n' "$XUI_API_URL"
  printf '  X-UI base path:         %s\n' "$XUI_BASE_PATH"
  printf '  Subscription base URL:  %s\n' "$XUI_SUB_SERVER_URL"
  printf '  Subscription URI path:  %s\n' "$XUI_SUB_PATH"
  printf '  App directory:          %s\n' "$APP_DIR"
  echo

  if ! confirm "Continue with installation"; then
    warn "Installation cancelled."
    exit 0
  fi

  export DEBIAN_FRONTEND=noninteractive
  info "Updating package index and installing system dependencies..."
  apt-get update
  apt-get install -y python3 python3-pip python3-venv curl

  info "Preparing application directory..."
  mkdir -p "$APP_DIR"
  if [[ "$SOURCE_DIR" != "$APP_DIR" ]]; then
    cp "$SOURCE_DIR/main.py" "$APP_DIR/main.py"
  else
    info "Source is already $APP_DIR; skipping main.py self-copy."
  fi
  cd "$APP_DIR"

  info "Creating virtual environment..."
  python3 -m venv .venv

  info "Installing Python dependencies..."
  ./.venv/bin/python -m pip install --upgrade pip setuptools wheel
  if [[ -f "$SOURCE_DIR/requirements.txt" ]]; then
    ./.venv/bin/python -m pip install -r "$SOURCE_DIR/requirements.txt"
  else
    ./.venv/bin/python -m pip install pyTelegramBotAPI requests
  fi

  info "Writing environment file..."
  cat > "$ENV_FILE" <<EOF
export BOT_TOKEN=$(printf '%q' "$BOT_TOKEN")
export ADMIN_ID=$(printf '%q' "$ADMIN_ID")
export XUI_API_URL=$(printf '%q' "$XUI_API_URL")
export XUI_BASE_PATH=$(printf '%q' "$XUI_BASE_PATH")
export XUI_BEARER_TOKEN=$(printf '%q' "$XUI_BEARER_TOKEN")
export XUI_SUB_SERVER_URL=$(printf '%q' "$XUI_SUB_SERVER_URL")
export XUI_SUB_PATH=$(printf '%q' "$XUI_SUB_PATH")
EOF
  chmod 600 "$ENV_FILE"

  info "Testing 3x-ui API authentication and base path (read-only)..."
  set +e
  PREFLIGHT_OUTPUT="$(
    XUI_API_URL="$XUI_API_URL" XUI_BASE_PATH="$XUI_BASE_PATH" XUI_BEARER_TOKEN="$XUI_BEARER_TOKEN" \
    "$APP_DIR/.venv/bin/python3" - <<'PY'
import os, sys, requests
base = os.environ['XUI_API_URL'].rstrip('/')
path = os.environ.get('XUI_BASE_PATH', '').strip()
prefix = '' if path in ('', '/') else '/' + path.strip('/')
url = f"{base}{prefix}/panel/api/inbounds/list"
try:
    r = requests.get(url, headers={
        'Authorization': 'Bearer ' + os.environ['XUI_BEARER_TOKEN'],
        'Accept': 'application/json'
    }, timeout=15)
except Exception as e:
    print(f"NETWORK_ERROR|{type(e).__name__}: {e}")
    sys.exit(20)
body = (r.text or '').strip().replace('\n', ' ')[:500] or '<empty response body>'
print(f"HTTP_{r.status_code}|{url}|{body}")
try:
    ok = r.status_code == 200 and bool(r.json().get('success'))
except Exception:
    ok = False
if ok:
    sys.exit(0)
if r.status_code in (401, 403):
    sys.exit(21)
if r.status_code == 404:
    sys.exit(22)
sys.exit(23)
PY
  )"
  PREFLIGHT_CODE=$?
  set -e
  if [[ "$PREFLIGHT_CODE" -ne 0 ]]; then
    error "3x-ui API preflight failed: $PREFLIGHT_OUTPUT"
    case "$PREFLIGHT_CODE" in
      21) error "Bearer auth was rejected. Use the PLAINTEXT API Token created in Settings -> Security -> API Token; do not use its name or the web base path." ;;
      22) error "API returned 404. Check X-UI web base path, panel version, and reverse proxy routing." ;;
      20) error "Could not connect to the panel. Check DNS/firewall/TLS and panel port." ;;
      *)  error "Panel returned an unexpected response. Check the response above and 3x-ui logs." ;;
    esac
    exit 1
  fi
  success "3x-ui API preflight passed: $PREFLIGHT_OUTPUT"

  info "Creating service runner..."
  cat > "$RUNNER_FILE" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
source /root/SpeedyBot/.env
exec /root/SpeedyBot/.venv/bin/python3 /root/SpeedyBot/main.py
EOF
  chmod 700 "$RUNNER_FILE"

  info "Creating systemd service..."
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=SpeedPing Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=$RUNNER_FILE
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

  info "Reloading systemd and starting service..."
  systemctl daemon-reload
  systemctl enable "$SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"

  sleep 3
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    success "Installation completed successfully."
    echo
    systemctl --no-pager --full status "$SERVICE_NAME" || true
    echo
    echo "Useful commands:"
    echo "  Status:   systemctl status $SERVICE_NAME"
    echo "  Logs:     journalctl -u $SERVICE_NAME -f"
    echo "  Restart:  systemctl restart $SERVICE_NAME"
    echo "  Stop:     systemctl stop $SERVICE_NAME"
    echo "  Edit env:  sudo nano $ENV_FILE"
  else
    error "Service failed to start."
    journalctl -u "$SERVICE_NAME" -n 50 --no-pager || true
    exit 1
  fi
}

main "$@"