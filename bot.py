import os
import discord
import aiohttp
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load token dari file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
    print("ERROR: Token tidak ditemukan! Pastikan file .env sudah benar.")
    exit()

# URL API FiveM & Logo Server
FIVEM_SERVERS = {
    "ni": {"url": "https://servers-frontend.fivem.net/api/servers/single/88x6zb", "logo": "https://media.discordapp.net/attachments/1218529915721351278/1346045483704909845/NusaIndah_FinalLogo.png"},
    "kb": {"url": "https://servers-frontend.fivem.net/api/servers/single/mez5p7", "logo": "https://media.discordapp.net/attachments/951083994370433055/1248594024881848332/KB-h_1.png"},
    "idp": {"url": "https://servers-frontend.fivem.net/api/servers/single/237yxy", "logo": "https://cdn.discordapp.com/attachments/616666479940599811/1022545370456268891/logo_indopride_v2-01.png"},
    "hope": {"url": "https://servers-frontend.fivem.net/api/servers/single/brm6gd", "logo": "https://cdn.discordapp.com/attachments/929186470919565313/1140947550132772904/3.png"},
    "kk": {"url": "https://servers-frontend.fivem.net/api/servers/single/r35px8", "logo": "https://cdn.discordapp.com/attachments/929186470919565313/1140947550132772904/3.png"},
    "jing": {"url": "https://servers-frontend.fivem.net/api/servers/single/53k9ra", "logo": "https://cdn.discordapp.com/attachments/1183700333797589022/1328681412106387509/JING-ARENA-500_1.webp?ex=67db4dbe&is=67d9fc3e&hm=4ea04dbf9028e5982fe8411e9b0b4cface1e14a8d6501171f3ffb25fec59c846&"},
}



# ID channel yang diizinkan
WHITELISTED_CHANNELS = {1200016475700854824}

# Atur intents bot Discord
intents = discord.Intents.default()
intents.message_content = True

# Inisialisasi bot
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} siap!')

def is_allowed_channel(ctx):
    return ctx.channel.id in WHITELISTED_CHANNELS

async def fetch_players(server_name):
    if server_name not in FIVEM_SERVERS:
        return None
    
    api_url = FIVEM_SERVERS[server_name]["url"]
    timeout = aiohttp.ClientTimeout(total=20)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if "Data" in data and isinstance(data["Data"], dict) and "players" in data["Data"]:
                        return data["Data"]["players"]
                return None
    except asyncio.TimeoutError:
        return "TIMEOUT"
    except aiohttp.ClientError:
        return None

def split_players(players, chunk_size=20):
    return [players[i:i + chunk_size] for i in range(0, len(players), chunk_size)]

@bot.command()
async def cek(ctx, server_name: str, *, query: str = None):
    if not is_allowed_channel(ctx):
        await ctx.send("Perintah ini hanya dapat digunakan di channel tertentu.")
        return

    if server_name not in FIVEM_SERVERS:
        await ctx.send(f"Server `{server_name}` tidak tersedia.")
        return
    
    players = await fetch_players(server_name)
    
    if players == "TIMEOUT":
        await ctx.send(f"Server `{server_name}` tidak merespons dalam waktu yang ditentukan.")
        return
    if players is None:
        await ctx.send(f"Terjadi kesalahan saat mengambil data dari server `{server_name}`.")
        return
    if not players:
        await ctx.send(f"{server_name.upper()} tidak memiliki pemain online saat ini.")
        return

    if query:
        players = [p for p in players if query.lower() in str(p.get("id", "")) 
                                      or query.lower() in p.get("name", "").lower() 
                                      or query.lower() in str(p.get("ping", ""))]
        if not players:
            await ctx.send(f"Tidak ada pemain dengan `{query}` di server `{server_name}`.")
            return
    
    pages = split_players(players, chunk_size=20)
    total_pages = len(pages)

    async def send_embed(page_num):
        embed = discord.Embed(
            title=f"{server_name.upper()} - {len(players)} Pemain Online",
            description=f"**Page {page_num+1}/{total_pages}**\n",
            color=0x3498db
        )
        embed.set_thumbnail(url=FIVEM_SERVERS[server_name]["logo"])
        
        player_list = ""
        for player in pages[page_num]:
            player_list += f"({player.get('id', '?')}) {player.get('name', 'Unknown')[:40]}\n"
        
        embed.add_field(name="Daftar Pemain:", value=f"```{player_list}```", inline=False)
        return embed

    message = await ctx.send(embed=await send_embed(0))

    if total_pages > 1:
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and reaction.emoji in ["⬅️", "➡️"]

        page_num = 0
        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                
                if reaction.emoji == "⬅️" and page_num > 0:
                    page_num -= 1
                elif reaction.emoji == "➡️" and page_num < total_pages - 1:
                    page_num += 1
                
                await message.edit(embed=await send_embed(page_num))

                try:
                    await message.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    pass
            except asyncio.TimeoutError:
                break

bot.run(TOKEN)
