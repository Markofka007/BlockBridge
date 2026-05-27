# BlockBridge ⛏️
A Discord bot that bridges communication between a Minecraft server and a Discord channel.
Current features include:
- ✨ Chat bridging ✨
- Player join/leave announcements
- Player death announcements
- Player advancement and challenge announcements
- Server start/stop announcements
- Log-based alerts for warnings and performance issues
- Command to check server status
- Command to see who's online
- Command execution (optional)
- World seed command (optional)
- Self-served whitelisting (optional)

# How it works
BlockBridge runs alongside your Minecraft server as a separate process. It connects to the server in two ways:
- **Incoming events** (chat, joins, leaves, deaths, advancements, start/stop) - tails `logs/latest.log` and forwards matching lines to Discord
- **Outgoing commands** (tellraw, whitelist, etc.) - sends commands via RCON

This means the bot and server have independent lifecycles. You can restart the bot without touching the server, and a server crash won't take the bot down with it. This is a **major** improvement from the previous version where the bot wraps the server process. However, you must configure the following `server.properties` settings for this to work:

# Prerequisites
You must enable RCON in your server's `server.properties` before starting:
```
enable-rcon=true
rcon.password=your_password_here
rcon.port=25575
```

# Install and Setup
1. Download `server.py`, `requirements.txt`, and `.env.example` anywhere you'd like. They don't need to live inside the Minecraft server directory.
2. Install requirements:
    ```
    pip install -r requirements.txt
    ```
3. Rename or copy `.env.example` to `.env` and fill in your values:
    ```
    cp .env.example .env
    ```
    - `BOT_TOKEN` - your Discord bot token
    - `CHANNEL_ID` - the channel to bridge with Minecraft chat
    - `WEBHOOK_URL` - a webhook for the same channel (used to send MC messages with player avatars)
    - `SERVER_DIR` - absolute path to your Minecraft server directory (where `logs/` lives). Defaults to the current working directory if omitted.
    - `RCON_HOST` - hostname or IP of your Minecraft server (usually `localhost`)
    - `RCON_PORT` - RCON port from `server.properties` (default `25575`)
    - `RCON_PASSWORD` - RCON password from `server.properties`
    - `ADMIN_CHANNEL_ID` - channel for admin commands and log alerts. Required if `ENABLE_COMMAND_EXECUTION=true` or `RESTART_COMMAND` is set.

4. Toggle optional features in `.env`:
    - `ENABLE_COMMAND_EXECUTION` - enables the `!mc` command. Set to `false` to disable.
    - `ENABLE_WHITELIST` - enables the `!whitelist` command. Set to `false` to disable. If `true`, also set `WHITELIST_CHANNEL_ID`.
    - `ENABLE_SEED` - enables the `!seed` command. Defaults to `false` since it exposes the world seed.

> **Important:** Never share your `.env` file. It contains your bot token and RCON password.

# Usage
Start your Minecraft server normally, then run `python3 server.py`. The bot and server are fully independent, so you can stop and restart either one without affecting the other.

## Chat Bridge
Messages sent in the bridged Discord channel are forwarded to Minecraft via `/tellraw`, and messages sent by players in-game are forwarded to Discord via webhook using the player's skin as an avatar.

## Status
`!status`
Shows whether the server is online or offline, and the current player count.

## Online
`!online`
Lists players currently online by querying the server live via RCON.

## Seed
`!seed`
Shows the world seed. Must be enabled with `ENABLE_SEED=true` in `.env`.

## Command Execution
`!mc <command>`
Executes a command on the Minecraft server via RCON and returns the server's response. Must be enabled with `ENABLE_COMMAND_EXECUTION=true` in `.env`. Only works in the admin channel.

> **WARNING:** This allows arbitrary command execution on the Minecraft server. Only grant admin channel access to trusted moderators.

Example commands:
- `!mc time set day`
- `!mc ban herobrine`
- `!mc give @a diamond 64`
- `!mc op Notch`

## Whitelist
`!whitelist <username>`
Whitelists the given player. Rejects banned players, already-whitelisted players, and usernames that don't exist. Must be enabled with `ENABLE_WHITELIST=true` in `.env`.

Example:
- `!whitelist Notch`

## Log Alerts
Warning-level log lines and `"Can't keep up"` overload messages are automatically forwarded to the admin channel as they appear. Requires `ADMIN_CHANNEL_ID` to be set.
