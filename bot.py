import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1462134265360945235

PLAYFAB_TITLE_ID = os.getenv("PLAYFAB_TITLE_ID")
PLAYFAB_SECRET = os.getenv("PLAYFAB_SECRET")

# -----------------------------
# DISCORD SETUP
# -----------------------------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# -----------------------------
# PLAYFAB FUNCTION
# -----------------------------
def grant_cosmetic(playfab_id: str, cosmetic_id: str):
    url = f"https://{PLAYFAB_TITLE_ID}.playfabapi.com/Server/GrantItemsToUser"

    headers = {
        "Content-Type": "application/json",
        "X-SecretKey": PLAYFAB_SECRET
    }

    payload = {
        "PlayFabId": playfab_id,
        "ItemIds": [cosmetic_id]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.status_code, response.text

# -----------------------------
# /claim COMMAND (WORKING)
# -----------------------------
@tree.command(
    name="claim",
    description="Claim a cosmetic using your PlayFab ID",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    playfab_id="Your PlayFab ID",
    cosmetic_id="The cosmetic item ID to grant"
)
async def claim(interaction: discord.Interaction, playfab_id: str, cosmetic_id: str):
    print("CLAIM COMMAND TRIGGERED")

    await interaction.response.defer(ephemeral=True)

    status, text = grant_cosmetic(playfab_id, cosmetic_id)

    if status == 200:
        await interaction.followup.send(
            f"✅ Granted **{cosmetic_id}** to **{playfab_id}**",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"❌ PlayFab error\n\n**Status:** {status}\n**Response:** {text}",
            ephemeral=True
        )

# -----------------------------
# ON_READY (WORKING SYNC)
# -----------------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)

    # Delete old commands
    old_cmds = await tree.fetch_commands(guild=guild)
    for cmd in old_cmds:
        print("Deleting old command:", cmd.name)
        tree.remove_command(cmd.name, type=cmd.type, guild=guild)

    # Sync new commands
    synced = await tree.sync(guild=guild)
    print("SYNCED COMMANDS:", synced)

    print(f"Logged in as {bot.user}")

# -----------------------------
# RUN BOT
# -----------------------------
bot.run(BOT_TOKEN)
