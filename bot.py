import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os

# -----------------------------
# CONFIG (ENV VARS)
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = 1462134265360945235

PLAYFAB_TITLE_ID = os.getenv("PLAYFAB_TITLE_ID")
PLAYFAB_SECRET = os.getenv("PLAYFAB_SECRET")

# FULL ACCESS ROLES (can choose ANY cosmetic)
FULL_ACCESS = ["HB | Owners", "Knuckles", "...", "NEPTUNE"]

# TRIAL MOD ROLE (forced LBATF)
TRIAL_MOD = "Trial Mod"

# -----------------------------
# DISCORD SETUP
# -----------------------------
intents = discord.Intents.default()
intents.members = True
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
# /claim COMMAND
# -----------------------------
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

    # Determine cosmetic based on role
    if any(r in FULL_ACCESS for r in role_names):
        # Full access → use whatever they typed
        final_cosmetic = cosmetic_id

    elif TRIAL_MOD in role_names:
        # Trial mod → forced LBATF
        final_cosmetic = "LBATF"

    else:
        # All other staff → forced LBATQ
        final_cosmetic = "LBATQ"

    await interaction.response.defer(ephemeral=True)

    status, text = grant_cosmetic(playfab_id, final_cosmetic)

    if status == 200:
        await interaction.followup.send(
            f"✅ Granted **{final_cosmetic}** to **{playfab_id}**",
            ephemeral=True
        )
    else:
        await interaction.followup.send(
            f"❌ PlayFab error\n\n**Status:** {status}\n**Response:** {text}",
            ephemeral=True
        )

# -----------------------------
# ON_READY
# -----------------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    synced = await tree.sync(guild=guild)
    print("SYNCED COMMANDS:", [cmd.name for cmd in synced])
    print(f"Logged in as {bot.user}")

# -----------------------------
# RUN BOT
# -----------------------------
bot.run(BOT_TOKEN)
