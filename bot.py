import nextcord as discord
from nextcord.ext import commands, tasks
import os
from datetime import datetime, time

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Otomatik duyurular
announcements = {}

@bot.event
async def on_ready():
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif!')
    check_announcements.start()

# ==================== DUYURU KOMUTLARI ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, channel: discord.TextChannel, *, message):
    """Belirli kanala duyuru at"""
    await channel.send(f'📢 **DUYURU**\n\n{message}')
    await ctx.send(f'✅ Duyuru {channel.mention} kanalına gönderildi!')

@bot.command()
@commands.has_permissions(administrator=True)
async def otomatik_duyuru(ctx, saat: str, kanal: discord.TextChannel, *, mesaj):
    """Günlük otomatik duyuru ayarla (saat formatı: HH:MM)"""
    try:
        hour, minute = map(int, saat.split(':'))
        announcement_id = f"{ctx.guild.id}_{kanal.id}"
        
        announcements[announcement_id] = {
            'channel_id': kanal.id,
            'message': mesaj,
            'time': time(hour, minute),
            'guild_id': ctx.guild.id
        }
        
        await ctx.send(f'✅ Otomatik duyuru ayarlandı!\n🕐 Saat: **{saat}**\n📢 Kanal: {kanal.mention}\n📝 Mesaj: {mesaj}')
    except:
        await ctx.send('❌ Saat formatı hatalı! Örnek: `!otomatik_duyuru 09:00 #duyurular Günaydın!`')

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru_sil(ctx, kanal: discord.TextChannel):
    """Otomatik duyuruyu sil"""
    announcement_id = f"{ctx.guild.id}_{kanal.id}"
    if announcement_id in announcements:
        del announcements[announcement_id]
        await ctx.send(f'✅ {kanal.mention} için otomatik duyuru silindi!')
    else:
        await ctx.send('❌ Bu kanal için duyuru bulunamadı!')

@bot.command()
async def duyuru_liste(ctx):
    """Aktif duyuruları göster"""
    guild_announcements = [a for a in announcements.values() if a['guild_id'] == ctx.guild.id]
    if not guild_announcements:
        await ctx.send('📋 Aktif duyuru yok!')
        return
    
    msg = '📋 **Aktif Duyurular:**\n\n'
    for ann in guild_announcements:
        channel = bot.get_channel(ann['channel_id'])
        saat = ann['time'].strftime('%H:%M')
        msg += f'🕐 {saat} - {channel.mention}: {ann["message"][:50]}...\n'
    
    await ctx.send(msg)

@tasks.loop(minutes=1)
async def check_announcements():
    """Her dakika duyuruları kontrol et"""
    now = datetime.now().time()
    now = time(now.hour, now.minute)
    
    for ann_id, ann in announcements.items():
        if ann['time'].hour == now.hour and ann['time'].minute == now.minute:
            channel = bot.get_channel(ann['channel_id'])
            if channel:
                await channel.send(f'📢 **OTOMATİK DUYURU**\n\n{ann["message"]}')

# ==================== EKSTRA KOMUTLAR ====================

@bot.command()
async def ping(ctx):
    """Bot gecikmesini göster"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Pong! Gecikme: **{latency}ms**')

@bot.command()
async def yardim(ctx):
    """Yardım menüsü"""
    embed = discord.Embed(title='🤖 YIKILMAZ BOT - KOMUTLAR', color=0x3498db)
    
    embed.add_field(name='📢 Duyuru', value='`!duyuru` `!otomatik_duyuru` `!duyuru_sil` `!duyuru_liste`', inline=False)
    embed.add_field(name='⚙️ Diğer', value='`!ping` `!yardim`', inline=False)
    
    await ctx.send(embed=embed)

# Hata yakalama
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ Bunu yapmak için yetkin yok!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('❌ Eksik parametre! Komutu doğru kullandığından emin ol.')
    else:
        print(f'Hata: {error}')

# Botu çalıştır
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
