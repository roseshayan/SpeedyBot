# SpeedPing Telegram Bot

A Telegram sales bot for **X-UI / Sanaei 3.3.0** that automates the full order flow:

1. show available plans
2. receive proof of payment
3. let the admin approve or reject the payment
4. create the client in the X-UI panel
5. deliver both a subscription link and direct config links to the user

The project uses a local **SQLite** database and runs as a **systemd** service on Ubuntu.

## Tested environment

- Ubuntu 24.04
- Sanaei panel 3.3.0
- Python 3
- `pyTelegramBotAPI`
- `requests`

## What this bot does

- Shows a simple Telegram menu to customers
- Displays bank/card payment details
- Accepts payment receipt images
- Sends the receipt to the admin for manual verification
- Lets the admin approve or reject the order
- On approval, creates a new X-UI client automatically
- Generates:
  - a subscription URL
  - direct config links
- Provides a support chat flow
- Includes an admin panel at `/sudoadmin`

## Project files

- `main.py` — bot logic, SQLite database, X-UI API integration
- `install.sh` — automatic installer for Ubuntu/Debian with `systemd`
- `README.md` — English documentation
- `README.fa.md` — Persian documentation

## Requirements

You need:

- A Telegram bot token from [BotFather]
- Your Telegram numeric admin ID
- Access to the X-UI / Sanaei panel admin token
- The panel API base URL
- The panel base path
- A subscription server URL for serving `/sub/...` links

### Environment variables

The bot reads these values from environment variables:

- `BOT_TOKEN`
- `ADMIN_ID`
- `XUI_API_URL`
- `XUI_BASE_PATH`
- `XUI_BEARER_TOKEN`
- `XUI_SUB_SERVER_URL`

Example values:

```bash
BOT_TOKEN=123456:ABCDEF...
ADMIN_ID=123456789
XUI_API_URL=http://127.0.0.1:2053
XUI_BASE_PATH=/
XUI_BEARER_TOKEN=your-panel-bearer-token
XUI_SUB_SERVER_URL=https://sub.example.com:2096
```

### Important notes about the panel values

- `XUI_API_URL` must include the protocol and port.
- `XUI_BASE_PATH` must match the panel security path.
  - If the panel has no security path, use `/`
  - If it does, use something like `/pKPl2UQ2sKTDnSWXb0`
- `XUI_SUB_SERVER_URL` is used to build subscription links like:
  `https://sub.example.com:2096/sub/<id>`

## Installation on Ubuntu 24.04

### Option 1: automatic installation

Upload the project files to your server, then run:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will ask for:

- Telegram bot token
- Telegram admin ID
- X-UI API URL
- X-UI base path
- X-UI bearer token
- Subscription server URL

It will then:

- install Python packages
- create `/root/xui-shop-bot`
- copy `main.py` there
- create a virtual environment
- install dependencies
- create a `systemd` service named `xui-bot.service`
- enable and start the bot

### Option 2: manual installation

Install system packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

Create the working directory:

```bash
sudo mkdir -p /root/xui-shop-bot
sudo cp main.py /root/xui-shop-bot/main.py
cd /root/xui-shop-bot
```

Create the virtual environment and install dependencies:

```bash
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install pyTelegramBotAPI requests
```

Create the systemd service file:

```bash
sudo nano /etc/systemd/system/xui-bot.service
```

Paste this:

```ini
[Unit]
Description=X-UI Telegram Shop Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/xui-shop-bot
ExecStart=/root/xui-shop-bot/.venv/bin/python3 /root/xui-shop-bot/main.py
Restart=always
RestartSec=5
Environment=BOT_TOKEN=YOUR_BOT_TOKEN
Environment=ADMIN_ID=YOUR_ADMIN_ID
Environment=XUI_API_URL=YOUR_XUI_API_URL
Environment=XUI_BASE_PATH=YOUR_XUI_BASE_PATH
Environment=XUI_BEARER_TOKEN=YOUR_BEARER_TOKEN
Environment=XUI_SUB_SERVER_URL=YOUR_SUB_SERVER_URL

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable xui-bot.service
sudo systemctl start xui-bot.service
```

Check status and logs:

```bash
sudo systemctl status xui-bot.service
sudo journalctl -u xui-bot.service -f
```

## First-time configuration inside the bot

After the bot starts, open Telegram and send `/start`.

The bot creates its local database file:

- `speedping.db`

At first launch, the database contains default bank settings:

- Card number
- Card holder name
- Bank name

You should change these from the admin panel before taking real payments.

## User flow

### 1) Open the bot
The user sends `/start` and sees the main menu.

### 2) Select a plan
The bot shows the available plans defined in `PLANS` inside `main.py`.

Current default plan:

```python
1: {"name": "Unlimited Plan (Monthly)", "price": 300000, "volume": 0, "days": 30}
```

### 3) Pay manually
The bot shows the bank details stored in the SQLite database.

### 4) Send proof of payment
The user must reply with a **photo** of the payment receipt.

If the user sends text instead of a photo, the bot rejects it and asks again.

### 5) Admin review
The receipt is forwarded to the admin with two buttons:

- Approve payment
- Reject receipt

### 6) Automatic account creation
When the admin approves the receipt:

- a client email is generated in the form:
  `speedping_<telegram_id>_<transaction_id>`
- the bot reads all active inbounds from the panel
- the new client is added to those inbounds
- the bot requests direct config links
- the bot sends the user:
  - subscription link
  - direct links

## User commands and menus

### Commands

- `/start` — open the main menu
- `/sudoadmin` — open the admin panel

### Main menu buttons

- Browse and buy plans
- Account
- Support

### Account section

The account view shows approved transactions and lets the user open each service to see:

- current usage
- total quota
- expiry time
- subscription link
- direct config links

### Support section

Support mode allows users to send:

- text
- photos
- voice messages
- videos
- documents

Those messages are forwarded to the admin. The admin can reply directly, and the reply is sent back to the original user.

## Admin panel features

The admin panel is available through `/sudoadmin`.

Available actions:

- Sales and bot statistics
- Live server status
- Broadcast message to all users
- Edit bank card information
- Delete a user from the bot database
- Delete a subscription from the X-UI panel

## How the bot talks to Sanaei / X-UI

The bot uses the panel API with the bearer token you provide.

Main endpoints used by the code:

- `GET /panel/api/server/status`
- `GET /panel/api/inbounds/list`
- `POST /panel/api/clients/add`
- `GET /panel/api/clients/get/{email}`
- `GET /panel/api/clients/traffic/{email}`
- `GET /panel/api/clients/links/{email}`
- `POST /panel/api/clients/del/{email}?keepTraffic=0`

The bot expects the panel to support those endpoints exactly as implemented in the project.

## Database

The bot uses `speedping.db` in the working directory.

Tables:

- `users`
- `transactions`
- `support_messages`
- `settings`

### Default settings stored in the database

- `card_number`
- `card_holder`
- `bank_name`

## Editing prices and plans

All plans are defined in the `PLANS` dictionary inside `main.py`.

To add a plan, edit that dictionary and restart the service.

Example:

```python
PLANS = {
    1: {"name": "Unlimited Plan (Monthly)", "price": 300000, "volume": 0, "days": 30},
    2: {"name": "20 GB / 30 Days", "price": 250000, "volume": 20, "days": 30},
}
```

Notes:

- `price` is in toman
- `volume = 0` means unlimited volume
- `days` controls the expiry time
- the bot currently uses the same plan price when calculating revenue statistics

## Updating bank details

Use `/sudoadmin`, then open **Bank settings**.

You can change:

- card number
- account holder name
- bank name

These values are stored in SQLite, not hardcoded in Telegram messages.

## Logs and service management

Useful commands:

```bash
sudo systemctl restart xui-bot.service
sudo systemctl stop xui-bot.service
sudo systemctl start xui-bot.service
sudo systemctl status xui-bot.service
sudo journalctl -u xui-bot.service -f
```

## Troubleshooting

### Bot does not start
Check:

- `BOT_TOKEN` is correct
- `ADMIN_ID` is numeric
- the virtual environment exists
- `pyTelegramBotAPI` and `requests` are installed

### Bot starts but panel actions fail
Check:

- `XUI_API_URL` is reachable from the server
- `XUI_BASE_PATH` is correct
- `XUI_BEARER_TOKEN` is valid
- your panel user token has permission to use the API
- the panel endpoints match Sanaei 3.3.0 behavior

### User receives no config after approval
Check:

- the panel has active inbounds
- the client creation request succeeds
- `XUI_SUB_SERVER_URL` is correct
- the subscription server is reachable

### Receipt forwarding or support replies fail
Check:

- the admin ID is correct
- the admin is using the bot account that matches `ADMIN_ID`
- the bot is not blocked by Telegram rate limits

## Security recommendations

- Do not expose your panel API token publicly.
- Run the bot only on a trusted server.
- Change the default bank values immediately.
- Use a strong base path and secure panel access.
- Back up `speedping.db` regularly.
- Restrict the server firewall so only the required ports are reachable.

## License

No license is defined in this repository. Treat it as private unless you add one.
