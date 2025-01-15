# BlockBridge 👾⛏️
A Discord bot that bridges communication between a Minecraft server and a Discord channel.
Current features include:
- Chat bridging
- Command execution
- Self-served whitelisting

# Install and Setup
1. Download `server.py` and place it in your Minecraft server's directory. This is the directory with files like `server.jar`, `whitelist.json`, and `banned-players.json`.
2. Download `requirements.txt` and install the requirements with `pip install -r requirements.txt`.
3. Open `server.py` and change the following variable at the top:
    - Change `BOT_TOKEN` to your Discord bot's token.
    - Change `CHANNEL_ID` to the channel ID you want to bridge to your Minecraft server's chat.
    - Change `COMMAND_CHANNEL_ID` to the channel ID you want to allow users to execute commands from. WARNING: THIS IS DANGEROUS! Only allow trusted Minecraft server mods into this channel! We recommend disallowing everyone and only allowing specific users into this channel.
    - Change `WHITELIST_CHANNEL_ID` to the channel ID where users can whitelist themselves or others. If you don't want public whitelisting, change this to the same channel ID as `COMMAND_CHANNEL_ID`.
    - Change `WEBHOOK_URL` to the webhook for the channel you want to bridge to your Minecraft server's chat. This will be the same channel as `CHANNEL_ID`.
    - (Optional) Modify `MC_SERVER_PARAMS` to change the amount of RAM that is used or to add extra arguments.

# Usage
Once all the variables are configured, then the Minecraft and Discord chats should be bridged! Just execute `server.py` and it will automatically start the Minecraft server jar file. Keep in mind that this Python script is the handler for the server jar executable, so you will not be able to interact with the server's terminal.

## Command Execution
`!mc <command>`
This executes the given command in the Minecraft server subprocess. This is a substitute for the server's terminal, and it allows for other authorized mods to execute command without being logged into the game.

Examples:
- `!mc time set day`
- `!mc ban Notch`
- `!mc give @a diamond 64`


## Whitelist
`!whitelist <username>`
This attempts to whitelist the given user. This will not work if the user is banned or already whitelisted. I've had issues in the past with people giving the wrong usernames, so this will tell you if the username does not exist.

Example:
- `!whitelist Notch`


# Todo
- Add a delay before checking if the user was whitelisted
- Make whitelisting case insensitive
- Add a server status command
- Achievement alerts
- Alerts for when a user joins/leaves
