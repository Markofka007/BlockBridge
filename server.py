import asyncio
import discord
from discord.ext import commands
import threading
import re
import json
import requests
import socket
import struct
import time
import os
from dotenv import load_dotenv

load_dotenv()

ENABLE_COMMAND_EXECUTION = os.getenv("ENABLE_COMMAND_EXECUTION", "true").lower() == "true"
ENABLE_WHITELIST = os.getenv("ENABLE_WHITELIST", "true").lower() == "true"
ENABLE_SEED = os.getenv("ENABLE_SEED", "false").lower() == "true"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SERVER_DIR = os.getenv("SERVER_DIR", ".")
RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", "25575"))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
_admin_channel_id = os.getenv("ADMIN_CHANNEL_ID")
ADMIN_CHANNEL_ID = int(_admin_channel_id) if _admin_channel_id else None

if ENABLE_WHITELIST:
    WHITELIST_CHANNEL_ID = int(os.getenv("WHITELIST_CHANNEL_ID"))

# Death message keywords used to detect and forward player deaths.
# Since this is pattern-based it may have false positive. I might fix this if I feel like it.
DEATH_KEYWORDS = (
    "was slain", "was shot", "was killed", "was blown up", "was pummeled",
    "was fireballed", "was squished", "was skewered", "was stung", "was doomed",
    "was struck by lightning", "was obliterated", "was impaled",
    "drowned", "blew up", "burned to death", "went up in flames",
    "fell from", "fell off", "fell out of the world", "hit the ground too hard",
    "tried to swim in lava", "suffocated", "starved to death",
    "walked into a cactus", "experienced kinetic energy", "froze to death",
    "was pricked to death", "died",
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def _rcon_send(sock, req_id, pkt_type, payload):
    data = payload.encode("utf-8") + b"\x00\x00"
    sock.sendall(struct.pack("<iii", len(data) + 8, req_id, pkt_type) + data)

def _rcon_recv(sock):
    length = struct.unpack("<i", _rcon_read(sock, 4))[0]
    data = _rcon_read(sock, length)
    req_id, pkt_type = struct.unpack("<ii", data[:8])
    return req_id, pkt_type, data[8:-2].decode("utf-8")

def _rcon_read(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("RCON connection closed")
        buf += chunk
    return buf

def rcon_command(command):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((RCON_HOST, RCON_PORT))
            _rcon_send(sock, 1, 3, RCON_PASSWORD)  # login
            if _rcon_recv(sock)[0] == -1:
                print("RCON error: authentication failed")
                return None
            _rcon_send(sock, 2, 2, command)
            return _rcon_recv(sock)[2]
    except Exception as e:
        print(f"RCON error: {e}")
        return None


# Thread that tails logs/latest.log and forwards events to Discord.
def tail_log():
    log_path = os.path.join(SERVER_DIR, "logs", "latest.log")
    while not os.path.exists(log_path):
        print(f"Waiting for log file at {log_path}...")
        time.sleep(2)

    channel = None
    admin_channel = None

    f = open(log_path, "r")
    f.seek(0, 2)  # Start from the end so we don't replay old events on (re)start

    while True:
        if not channel:
            channel = bot.get_channel(CHANNEL_ID)
        if not admin_channel and ADMIN_CHANNEL_ID:
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)

        line = f.readline()
        if not line:
            time.sleep(0.1)
            # Reopen if the file shrank. Server restart rotates logs/latest.log
            try:
                if os.path.getsize(log_path) < f.tell():
                    f.close()
                    f = open(log_path, "r")
            except OSError:
                pass
            continue

        # Server start/stop
        if "[Server thread/INFO]" in line:
            if "Done (" in line and channel:
                bot.loop.create_task(channel.send("Server is now online!"))
                continue
            if "Stopping the server" in line and channel:
                bot.loop.create_task(channel.send("Server is shutting down."))
                continue

        # Log alerts — WARN level lines and "Can't keep up" overload warnings
        if admin_channel and ("/WARN]" in line or "Can't keep up" in line):
            bot.loop.create_task(admin_channel.send(f"```{line.strip()}```"))
            continue

        if "[Server thread/INFO]" not in line:
            continue

        mc_message = re.search(r"\[.+\] \[Server thread/INFO\]: <(.+)> (.*)$", line)
        mc_join = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) joined the game$", line)
        mc_leave = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) left the game$", line)
        mc_advancement = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) has made the advancement \[(.+)\]$", line)
        mc_challenge = re.search(r"\[.+\] \[Server thread/INFO\]: (\w+) has completed the challenge \[(.+)\]$", line)

        if mc_message:
            sender = mc_message.group(1)
            msg_content = mc_message.group(2)

            payload = {
                "username": sender,
                "content": msg_content,
                "avatar_url": f"https://www.mc-heads.net/head/{sender}",
                "allowed_mentions": {"parse": []}
            }

            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send webhook: {response.status_code}, {response.text}")

        elif mc_join and channel:
            bot.loop.create_task(channel.send(f"**{mc_join.group(1)}** joined the server!"))

        elif mc_leave and channel:
            bot.loop.create_task(channel.send(f"**{mc_leave.group(1)}** left the server!"))

        elif mc_advancement and channel:
            bot.loop.create_task(channel.send(f"**{mc_advancement.group(1)}** just got the advancement **{mc_advancement.group(2)}**!"))

        elif mc_challenge and channel:
            bot.loop.create_task(channel.send(f"**{mc_challenge.group(1)}** just completed the challenge **{mc_challenge.group(2)}**!"))

        # Death messages — checked last to avoid false positives from other patterns
        elif channel and any(kw in line for kw in DEATH_KEYWORDS):
            mc_death = re.search(r"\[Server thread/INFO\]: (.+)$", line)
            if mc_death:
                bot.loop.create_task(channel.send(f"**{mc_death.group(1)}**"))


@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
    threading.Thread(target=tail_log, daemon=True).start()


if ENABLE_WHITELIST:
    @bot.command(name="whitelist")
    async def whitelist_cmd(ctx, *, username: str):
        """
        Command to whitelist yourself on the Minecraft server.
        Usage: !whitelist <in-game username>
        """
        if ctx.channel.id != WHITELIST_CHANNEL_ID:
            await ctx.send("This command can only be used in a designated whitelisting channel.")
            return

        with open(os.path.join(SERVER_DIR, "whitelist.json"), "r") as f:
            if username.lower() in f.read().lower():
                await ctx.send(f"`{username}` is already whitelisted!")
                return

        with open(os.path.join(SERVER_DIR, "banned-players.json"), "r") as f:
            if username.lower() in f.read().lower():
                await ctx.send(f"`{username}` is banned!")
                return

        response = await asyncio.to_thread(rcon_command, f"whitelist add {username}")
        if response is None:
            await ctx.send("Could not connect to the server. Is it running?")
        elif "Added" in response:
            await ctx.send(f"Successfully whitelisted `{username}`!")
        elif "already" in response.lower():
            await ctx.send(f"`{username}` is already whitelisted!")
        else:
            await ctx.send(f"`{username}` does not exist :(")


if ENABLE_COMMAND_EXECUTION and ADMIN_CHANNEL_ID:
    @bot.command(name="mc")
    async def mc_cmd(ctx, *, command: str):
        """
        Command to execute Minecraft server commands.
        Usage: !mc <command>
        """
        if ctx.channel.id != ADMIN_CHANNEL_ID:
            await ctx.send("This command can only be used in the admin channel.")
            return

        response = await asyncio.to_thread(rcon_command, command)
        if response is None:
            await ctx.send("Could not connect to the server. Is it running?")
        elif response:
            await ctx.send(f"```{response}```")
        else:
            await ctx.send(f"Command executed: `{command}`")


@bot.command(name="online")
async def online_cmd(ctx):
    """
    Command to see who is currently online.
    Usage: !online
    """
    if ctx.channel.id != CHANNEL_ID:
        await ctx.send("This command can only be used in the chat channel.")
        return

    response = await asyncio.to_thread(rcon_command, "list")
    if response is None:
        await ctx.send("Could not connect to the server. Is it running?")
        return

    # Response format: "There are N of a max of M players online: player1, player2, ..."
    match = re.search(r"There are (\d+) of a max of \d+ players online: (.*)", response)
    if match:
        count = int(match.group(1))
        if count == 0:
            await ctx.send("No users are currently online :(")
        else:
            players = match.group(2).strip()
            player_list = "\n".join(f"{i}. `{p.strip()}`" for i, p in enumerate(players.split(",")))
            await ctx.send(f"Users online:\n{player_list}")
    else:
        await ctx.send(response)


@bot.command(name="status")
async def status_cmd(ctx):
    """
    Command to check if the server is online.
    Usage: !status
    """
    if ctx.channel.id != CHANNEL_ID:
        await ctx.send("This command can only be used in the chat channel.")
        return

    response = await asyncio.to_thread(rcon_command, "list")
    if response is None:
        await ctx.send("Server is **offline** (or unreachable).")
        return

    match = re.search(r"There are (\d+) of a max of (\d+) players online", response)
    if match:
        count, max_players = match.group(1), match.group(2)
        await ctx.send(f"Server is **online**. Players: {count}/{max_players}")
    else:
        await ctx.send("Server is **online**.")


if ENABLE_SEED:
    @bot.command(name="seed")
    async def seed_cmd(ctx):
        """
        Shows the world seed.
        Usage: !seed
        """
        if ctx.channel.id != CHANNEL_ID:
            await ctx.send("This command can only be used in the chat channel.")
            return

        response = await asyncio.to_thread(rcon_command, "seed")
        if response is None:
            await ctx.send("Could not connect to the server. Is it running?")
            return

        # Response format: "Seed: [1234567890]"
        match = re.search(r"Seed: \[(.+)\]", response)
        if match:
            await ctx.send(f"World seed: `{match.group(1)}`")
        else:
            await ctx.send(response)


@bot.event
async def on_message(message):
    if not message.author.bot and message.channel.id == CHANNEL_ID:
        text = f"<{message.author}> {message.content}"
        asyncio.create_task(asyncio.to_thread(rcon_command, f"/tellraw @a {json.dumps({'text': text})}"))

    await bot.process_commands(message)


bot.run(BOT_TOKEN)
