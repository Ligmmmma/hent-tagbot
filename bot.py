import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os

TOKEN = os.getenv("BOT_TOKEN")
PLAYFAB_TITLE_ID = os.getenv("PLAYFAB_TITLE_ID")
PLAYFAB_SECRET = os.getenv("PLAYFAB_SECRET")

GUILD_ID = 1462134265360945235

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
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ============================================================
# PLAYFAB GRANT FUNCTION
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
# /claim COMMAND
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

    # Staff check
    if not any(r in STAFF_ROLES for r in role_names):
        await interaction.response.send_message("❌ Only staff can use this command.", ephemeral=True)
        return

    # FULL ACCESS
    if any(r in FULL_ACCESS for r in role_names):
        final_cosmetic = cosmetic_id

    # TRIAL MOD
    elif TRIAL_MOD in role_names:
        final_cosmetic = "LBATF"

    # NORMAL STAFF
    elif any(r in NORMAL_STAFF for r in role_names):
        if cosmetic_id not in ["LBATQ", "LBATF"]:
            await interaction.response.send_message("❌ You can only choose LBATQ or LBATF.", ephemeral=True)
            return
        final_cosmetic = cosmetic_id

    else:
        await interaction.response.send_message("❌ Unexpected role error.", ephemeral=True)
        return

    # Grant cosmetic
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
# ON READY
# ============================================================
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    synced = await tree.sync(guild=guild)
    print("Synced commands:", [cmd.name for cmd in synced])
    print(f"Logged in as {bot.user}")

# ============================================================
# RUN BOT
# ============================================================
bot.run(TOKEN)
