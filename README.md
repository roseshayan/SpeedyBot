# SpeedPing Telegram Bot

SpeedPing is a Telegram sales bot for **X-UI / Sanaei 3.3.0**. It automates the customer flow from plan selection to payment review and client creation in the panel.

## What it does

- Shows available plans to the customer
- Accepts a payment receipt image
- Sends the receipt to the admin for review
- Lets the admin approve or reject the order
- Creates a new X-UI client automatically after approval
- Generates the subscription URL and direct config links
- Provides a support flow
- Includes an admin panel at `/sudoadmin`

## Tested environment

This project has been tested on:

- Ubuntu 24.04
- Sanaei panel 3.3.0
- Python 3
- `pyTelegramBotAPI`
- `requests`

## Project structure

- `main.py` — bot logic, database layer, and X-UI API integration
- `install.sh` — English installer with input validation and systemd setup
- `README.md` — English documentation
- `README_FA.md` — Persian documentation

## Requirements

You need:

- A Telegram bot token from BotFather
- Your Telegram numeric admin ID
- The X-UI / Sanaei panel bearer token
- The X-UI panel API base URL
- The panel security base path
- A subscription server base URL for `/sub/<id>` links

## Configuration values

The bot reads its settings from environment variables:

- `BOT_TOKEN`
- `ADMIN_ID`
- `XUI_API_URL`
- `XUI_BASE_PATH`
- `XUI_BEARER_TOKEN`
- `XUI_SUB_SERVER_URL`

### Example

```bash
BOT_TOKEN=123456789:AAAbbbCCCdddEEEfffGGG
ADMIN_ID=123456789
XUI_API_URL=http://127.0.0.1:2053
XUI_BASE_PATH=/
XUI_BEARER_TOKEN=your-panel-bearer-token
XUI_SUB_SERVER_URL=https://sub.example.com:2096
```

### Important rules

- `XUI_API_URL` must be only the base URL: scheme + host + port.
  - Correct: `http://127.0.0.1:2053`
  - Incorrect: `http://127.0.0.1:2053/panel`
- `XUI_BASE_PATH` must match the Sanaei panel security path.
  - If the panel has no security path, use `/`
  - If it has one, use something like `/pKPl2UQ2sKTDnSWXb0`
- `XUI_SUB_SERVER_URL` must be only the base URL for the subscription server.
  - Correct: `https://sub.example.com:2096`
  - Incorrect: `https://sub.example.com:2096/sub`

## Installation

### Automatic installation

1. Upload the project files to your Ubuntu server.
2. Make sure `install.sh` and `main.py` are in the same directory.
3. Run:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will:

- validate every input before continuing
- ask again if a value is invalid or empty
- create `/root/SpeedyBot`
- copy `main.py` there
- create a Python virtual environment
- install the required Python packages
- create `.env` and `run.sh`
- create a `systemd` service named `xui-bot.service`
- enable and start the service

## What gets installed

The service runs the bot from:

- `/root/SpeedyBot/main.py`

The database file is created here:

- `/root/SpeedyBot/speedping.db`

The environment variables are stored in:

- `/root/SpeedyBot/.env`

## Managing the service

### Check status

```bash
systemctl status xui-bot.service
```

### View logs

```bash
journalctl -u xui-bot.service -f
```

### Restart

```bash
systemctl restart xui-bot.service
```

### Stop

```bash
systemctl stop xui-bot.service
```

### Edit configuration

```bash
nano /root/SpeedyBot/.env
systemctl restart xui-bot.service
```

## Manual installation

If you prefer to install everything yourself:

### 1) Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 2) Copy the project

```bash
sudo mkdir -p /root/SpeedyBot
sudo cp main.py /root/SpeedyBot/main.py
cd /root/SpeedyBot
```

### 3) Create the virtual environment

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip setuptools wheel
./.venv/bin/python -m pip install pyTelegramBotAPI requests
```

### 4) Create `/root/SpeedyBot/.env`

```bash
export BOT_TOKEN=YOUR_BOT_TOKEN
export ADMIN_ID=YOUR_ADMIN_ID
export XUI_API_URL=YOUR_XUI_API_URL
export XUI_BASE_PATH=YOUR_XUI_BASE_PATH
export XUI_BEARER_TOKEN=YOUR_BEARER_TOKEN
export XUI_SUB_SERVER_URL=YOUR_SUB_SERVER_URL
```

### 5) Create `/root/SpeedyBot/run.sh`

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
source /root/SpeedyBot/.env
exec /root/SpeedyBot/.venv/bin/python3 /root/SpeedyBot/main.py
```

### 6) Create the systemd service

```bash
sudo nano /etc/systemd/system/xui-bot.service
```

Paste:

```ini
[Unit]
Description=SpeedPing Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/SpeedyBot
ExecStart=/root/SpeedyBot/run.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 7) Enable and start it

```bash
sudo systemctl daemon-reload
sudo systemctl enable xui-bot.service
sudo systemctl start xui-bot.service
```

## Troubleshooting

### Service does not start

Check the status first:

```bash
systemctl status xui-bot.service
```

Then check the logs:

```bash
journalctl -u xui-bot.service -n 100 --no-pager
```

### Bot does not respond

Make sure:

- `BOT_TOKEN` is correct
- `ADMIN_ID` is the numeric Telegram user ID
- `XUI_API_URL` does not contain `/panel` or `/sub`
- `XUI_BASE_PATH` is correct
- `XUI_SUB_SERVER_URL` is the base URL only

### Update the bot

Replace `main.py` with the new version and restart the service:

```bash
sudo cp main.py /root/SpeedyBot/main.py
sudo systemctl restart xui-bot.service
```

### Uninstall

```bash
sudo systemctl stop xui-bot.service
sudo systemctl disable xui-bot.service
sudo rm -f /etc/systemd/system/xui-bot.service
sudo rm -rf /root/SpeedyBot
sudo systemctl daemon-reload
```

## Notes

- The bot currently stores data in SQLite.
- The default bank/card settings are stored in the database and can be adjusted in the code or through the admin functions provided by the bot.
- This project is designed for Ubuntu-based servers with `systemd`.
