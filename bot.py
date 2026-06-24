import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os
import asyncio
from datetime import datetime, timedelta

from flask import Flask, request
import threading

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1462134265360945235

PLAYFAB_TITLE_ID = os.getenv("PLAYFAB_TITLE_ID")
PLAYFAB_SECRET = os.getenv("PLAYFAB_SECRET")

BAN_LOG_FILE = "ban_log.json"
BAN_STATS_MESSAGE_FILE = "banstats_message.json"

# ============================================================
# ROLE GROUPS
# ============================================================
FULL_ACCESS = ["HB | Owners", "Knuckles", "...", "NEPTUNE"]
TRIAL_MOD = "Trial Mod"
NORMAL_STAFF = ["Mod", "Head Mod", "Admin", "Head Admin", "Co Owner", "Founder"]
STAFF_ROLES = NORMAL_STAFF + FULL_ACCESS + [TRIAL_MOD]

# ============================================================
# DISCORD SETUP
# ============================================================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============================================================
# BAN LOGGING
# ============================================================
def load_ban_log():
    if not os.path.exists(BAN_LOG_FILE):
        return []
    with open(BAN_LOG_FILE, "r") as f:
        return json.load(f)

def save_ban_log(data):
    with open(BAN_LOG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def log_ban(playfab_id, ban_type="staff"):
    data = load_ban_log()
    data.append({
        "playfab_id": playfab_id,
        "timestamp": datetime.utcnow().isoformat(),
        "type": ban_type
    })
    save_ban_log(data)

def count_bans_in_range(start, end):
    data = load_ban_log()
    return sum(1 for entry in data if start <= datetime.fromisoformat(entry["timestamp"]) < end)

def count_bans_by_type(ban_type):
    data = load_ban_log()
    return sum(1 for entry in data if entry.get("type") == ban_type)

# ============================================================
# BANSTATS MESSAGE STORAGE
# ============================================================
def load_banstats_message():
    if not os.path.exists(BAN_STATS_MESSAGE_FILE):
        return None
    with open(BAN_STATS_MESSAGE_FILE, "r") as f:
        return json.load(f)

def save_banstats_message(data):
    with open(BAN_STATS_MESSAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ============================================================
# BANSTATS AUTO UPDATE
# ============================================================
async def update_banstats_embed():
    await bot.wait_until_ready()
    first_run = True

    while True:
        try:
            msg_info = load_banstats_message()
            if not msg_info:
                await asyncio.sleep(10)
                continue

            channel = bot.get_channel(msg_info["channel_id"])
            message = await channel.fetch_message(msg_info["message_id"])

            now = datetime.utcnow()
            start_today = datetime(now.year, now.month, now.day)
            start_yesterday = start_today - timedelta(days=1)

            total_bans = len(load_ban_log())
            bans_today = count_bans_in_range(start_today, start_today + timedelta(days=1))
            bans_yesterday = count_bans_in_range(start_yesterday, start_today)

            staff_bans = count_bans_by_type("staff")
            spam_bans = count_bans_by_type("spam")
            player_bans = count_bans_by_type("player")

            embed = discord.Embed(title="📊 Ban Statistics", color=0x00AEEF)
            embed.add_field(name="Total Bans", value=f"`{total_bans}`", inline=False)
            embed.add_field(name="Bans Today", value=f"`{bans_today}`", inline=True)
            embed.add_field(name="Bans Yesterday", value=f"`{bans_yesterday}`", inline=True)
            embed.add_field(
                name="Banned By...",
                value=(
                    f"👮 Staff: `{staff_bans}`\n"
                    f"🤖 Spam Reports: `{spam_bans}`\n"
                    f"📣 Player Reports: `{player_bans}`"
                ),
                inline=False
            )
            embed.set_footer(text="Updates every 7 minutes")

            await message.edit(embed=embed)

        except Exception as e:
            print("Error updating banstats:", e)

        await asyncio.sleep(10 if first_run else 420)
        first_run = False

# ============================================================
# /banstats_setup
# ============================================================
@tree.command(
    name="banstats_setup",
    description="Create the ban statistics dashboard",
    guild=discord.Object(id=GUILD_ID)
)
async def banstats_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Ban Statistics",
        description="Initializing...",
        color=0x00AEEF
    )
    msg = await interaction.channel.send(embed=embed)
    save_banstats_message({"channel_id": interaction.channel.id, "message_id": msg.id})
    await interaction.response.send_message("✅ Ban statistics dashboard created.", ephemeral=True)

# ============================================================
# WEBHOOK SERVER (CloudScript → bot)
# ============================================================
app = Flask(__name__)

@app.route("/banwebhook", methods=["POST"])
def ban_webhook():
    data = request.json
    playfab_id = data.get("playfab_id")
    ban_type = data.get("type", "staff")
    if playfab_id:
        log_ban(playfab_id, ban_type)
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask).start()

# ============================================================
# PLAYFAB FUNCTION
# ============================================================
def grant_cosmetic(playfab_id: str, cosmetic_id: str):
    url = f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Server/GrantItemsToUser"
    headers = {
        "Content-Type": "application/json",
        "X-SecretKey": PLAYFAB_SECRET
    }
    payload = {"PlayFabId": playfab_id, "ItemIds": [cosmetic_id]}
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.status_code, response.text

# ============================================================
# /claim
# ============================================================
@tree.command(
    name="claim",
    description="Claim a cosmetic using your PlayFab ID",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    playfab_id="Your PlayFab ID",
    cosmetic_id="The cosmetic item ID to grant (if allowed)"
)
async def claim(interaction: discord.Interaction, playfab_id: str, cosmetic_id: str):
    member = interaction.user
    role_names = [role.name for role in member.roles]

    if not any(r in STAFF_ROLES for r in role_names):
        await interaction.response.send_message("❌ Only staff can use this command.", ephemeral=True)
        return

    if any(r in FULL_ACCESS for r in role_names):
        final_cosmetic = cosmetic_id
    elif TRIAL_MOD in role_names:
        final_cosmetic = "LBATF"
    elif any(r in NORMAL_STAFF for r in role_names):
        if cosmetic_id not in ["LBATQ", "LBATF"]:
            await interaction.response.send_message("❌ You can only choose LBATQ or LBATF.", ephemeral=True)
            return
        final_cosmetic = cosmetic_id
    else:
        await interaction.response.send_message("❌ Unexpected role error.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    status, text = grant_cosmetic(playfab_id, final_cosmetic)

    if status == 200:
        await interaction.followup.send(f"✅ Granted **{final_cosmetic}** to **{playfab_id}**", ephemeral=True)
    else:
        await interaction.followup.send(
            f"❌ PlayFab error\n\n**Status:** {status}\n**Response:** {text}",
            ephemeral=True
        )

# ============================================================
# ON_READY
# ============================================================
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    synced = await tree.sync(guild=guild)
    print("SYNCED COMMANDS:", [cmd.name for cmd in synced])
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(update_banstats_embed())

# ============================================================
# RUN BOT
# ============================================================
bot.run(BOT_TOKEN)
