import discord
from discord.ext import commands
import subprocess
import threading
import re
import requests
import base64
import json
import time

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
                mc_message = re.search(r"\[.+\] \[Server thread/INFO\]: <(.+)> (.*)$", line) # Check for player message.
                mc_join = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) joined the game$", line) # Check for join message.
                mc_leave = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) left the game$", line) # Check for leave message.
                mc_advancement = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) has made the advancement \[(.+)\]$", line) # Check for advancement message.

                if mc_message:
                    sender = mc_message.group(1)
                    msg_content = mc_message.group(2)

                    # Temporary solution for preventing the ability to @everyone using the webhook
                    while "@everyone" in msg_content:
                        msg_content.replace("@everyone", " ")

                    # Get the sender's head (for discord avater)
                    skin_url = f"https://www.mc-heads.net/head/{sender}"
                    if not skin_url:
                        print(f"Error fetching skin for {sender}. Using default avatar.")
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

                elif mc_join:
                    bot.loop.create_task(channel.send(f"**{mc_join.group(1)}** joined the server!"))

                elif mc_leave:
                    bot.loop.create_task(channel.send(f"**{mc_leave.group(1)}** left the server!"))

                elif mc_advancement:
                    bot.loop.create_task(channel.send(f"**{mc_advancement.group(1)}** just got the achievement **{mc_advancement.group(2)}**!"))

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
            if username.lower() in whitelist.read().lower():
                await ctx.send(f"{username} is already whitelisted!")
                return
            whitelist.close()

        # Check is user is banned.
        with open("banned-players.json", 'r') as banlist:
            if username.lower() in banlist.read().lower():
                await ctx.send(f"{username} is banned!")
                return
            banlist.close()

        # Attempt to whitelist user.
        minecraft_process.stdin.write(f"whitelist add {username}\n")
        minecraft_process.stdin.flush()
        await ctx.send(f"Whitelisting user: `{username}`")

        # Check if user was succesfully whitelisted.
        time.sleep(1)
        with open("whitelist.json", 'r') as whitelist:
            if username.lower() in whitelist.read().lower():
                await ctx.send(f"Succesfully whitelisted `{username}`")
            else:
                await ctx.send(f"`{username}` does not exist :(")
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