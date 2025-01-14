import discord
from discord.ext import commands
import subprocess
import threading
import re
import requests
import base64
import json

BOT_TOKEN = "DISCORD BOT TOKEN HERE"
CHANNEL_ID = 12345 # Channel ID for reading messages to be sent to the Minecraft server.
COMMAND_CHANNEL_ID = 12345 # Channel ID for executing commands on Minecraft server. (DANGER THIS IS FOR MODS ONLY)
WHITELIST_CHANNEL_ID = 1245 # Channel ID where users can whitelist themselves or others.
WEBHOOK_URL = "DISCORD WEBHOOK URL FOR MINECRAFT MESSAGES"
MC_SERVER_PARAMS = ["java.exe", "-Xmx2G", "-Xms2G", "-jar", "server.jar", "nogui"] # Arguments for launching the server.jar file


# Initialize the Discord bot.
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Start the Minecraft server process.
minecraft_process = subprocess.Popen(
    MC_SERVER_PARAMS,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Thread to read Minecraft server console output and send messages to Discord.
def read_minecraft_output():
    channel = None
    while True:
        if not channel:
            channel = bot.get_channel(CHANNEL_ID)
        line = minecraft_process.stdout.readline()
        if line:
            print(f"Minecraft: {line.strip()}")
            if channel and "[Server thread/INFO]" in line: # Check for Minecraft system message.
                mc_message = re.search(r"\[.+\] \[.+\]: <(.+)> (.*)$", line) # Check if the system message is a player message.
                if mc_message:
                    sender = mc_message.group(1)
                    msg_content = mc_message.group(2)

                    # Get the sender's head (for discord avater)
                    skin_url = f"https://www.mc-heads.net/head/{sender}"
                    if not skin_url:
                        print(f"Could not find skin for {sender}. Using default avatar.")
                        skin_url = None

                    payload = {
                        "username": sender,
                        "content": msg_content,
                        "avatar_url": skin_url
                    }

                    # Send the POST request to the Discord webhook
                    response = requests.post(WEBHOOK_URL, json=payload)
                    if response.status_code != 204:
                        print(f"Failed to send webhook: {response.status_code}, {response.text}")


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    threading.Thread(target=read_minecraft_output, daemon=True).start()


@bot.command(name="whitelist")
async def execute_mc_command(ctx, *, username: str):
    """
    Command to whitelist yourself on the Minecraft server.
    Usage: !whitelist <in-game username>
    """
    if ctx.channel.id == WHITELIST_CHANNEL_ID:
        # Check if user is already whitelisted.
        with open("whitelist.json", 'r') as whitelist:
            if username in whitelist.read():
                await ctx.send(f"{username} is already whitelisted!")
                return
            whitelist.close()

        # Check is user is banned.
        with open("banned-players.json", 'r') as banlist:
            if username in banlist.read():
                await ctx.send(f"{username} is banned!")
                return
            banlist.close()

        # Attempt to whitelist user.
        minecraft_process.stdin.write(f"whitelist add {username}\n")
        minecraft_process.stdin.flush()
        await ctx.send(f"Whitelisting user: `{username}`")

        # Check if user was succesfully whitelisted.
        with open("whitelist.json", 'r') as whitelist:
            if username in whitelist.read():
                await ctx.send(f"Succesfully whitelisted {username}")
            else:
                await ctx.send(f"{username} does not exist :(")
            whitelist.close()
    else:
        await ctx.send("This command can only be used in a designated whitelisting channel.")


@bot.command(name="mc")
async def execute_mc_command(ctx, *, command: str):
    """
    Command to execute Minecraft server commands.
    Usage: !mc <command>
    """
    if ctx.channel.id == COMMAND_CHANNEL_ID:
        minecraft_process.stdin.write(command + "\n")
        minecraft_process.stdin.flush()
        await ctx.send(f"Command executed: `{command}`")
    else:
        await ctx.send("This command can only be used in a designated command channel.")


# Handle messages sent in the target Discord channels.
@bot.event
async def on_message(message):
    if not message.author.bot:
        # Handle messages in the main channel (broadcast to Minecraft)
        if message.channel.id == CHANNEL_ID:
            command = '/tellraw @a {"text":"<' + str(message.author) + '> ' + str(message.content) + '"}\n'
            minecraft_process.stdin.write(command)
            minecraft_process.stdin.flush()

    await bot.process_commands(message) # Handle the commands.



try:
    bot.run(BOT_TOKEN)
except KeyboardInterrupt:
    print("Shutting down...")
    minecraft_process.terminate()