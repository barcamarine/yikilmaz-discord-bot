import nextcord as discord
from nextcord.ext import commands, tasks
import os
from datetime import datetime, time

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Otomatik duyurular (sınırsız)
announcements = []
announcement_id_counter = 1

@bot.event
async def on_ready():
    global announcement_id_counter
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif!')
    check_announcements.start()

# ==================== DUYURU KOMUTLARI ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, channel: discord.TextChannel, *, message):
    """Belirli kanala anlık duyuru at"""
    await channel.send(f'📢 **DUYURU**\n\n{message}')
    await ctx.send(f'✅ Duyuru {channel.mention} kanalına gönderildi!')

@bot.command()
@commands.has_permissions(administrator=True)
async def otomatik_duyuru(ctx, saat: str, kanal: discord.TextChannel, *, mesaj):
    """Günlük otomatik duyuru ayarla (saat formatı: HH:MM) - Sınırsız eklenebilir"""
    global announcement_id_counter
    try:
        hour, minute = map(int, saat.split(':'))
        
        duyuru = {
            'id': announcement_id_counter,
            'channel_id': kanal.id,
            'message': mesaj,
            'time': time(hour, minute),
            'guild_id': ctx.guild.id,
            'created_by': ctx.author.name
        }
        
        announcements.append(duyuru)
        announcement_id_counter += 1
        
        await ctx.send(f'✅ Otomatik duyuru ayarlandı!\n🆔 ID: **{duyuru["id"]}**\n🕐 Saat: **{saat}**\n📢 Kanal: {kanal.mention}\n📝 Mesaj: {mesaj[:100]}...')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}\nDoğru kullanım: `!otomatik_duyuru 09:00 #kanal Mesaj`')

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru_sil(ctx, id: int):
    """ID ile duyuru sil"""
    global announcements
    original_len = len(announcements)
    announcements = [a for a in announcements if not (a['id'] == id and a['guild_id'] == ctx.guild.id)]
    
    if len(announcements) < original_len:
        await ctx.send(f'✅ ID **{id}** olan duyuru silindi!')
    else:
        await ctx.send('❌ Bu ID ile duyuru bulunamadı!')

@bot.command()
async def duyuru_liste(ctx):
    """Tüm aktif duyuruları listele"""
    guild_announcements = [a for a in announcements if a['guild_id'] == ctx.guild.id]
    if not guild_announcements:
        await ctx.send('📋 Aktif duyuru yok!')
        return
    
    msg = '📋 **Aktif Duyurular:**\n\n'
    for ann in guild_announcements:
        channel = bot.get_channel(ann['channel_id'])
        channel_mention = channel.mention if channel else '❌ Silinmiş Kanal'
        saat = ann['time'].strftime('%H:%M')
        msg += f'🆔 **{ann["id"]}** | 🕐 {saat} | {channel_mention}\n📝 {ann["message"][:50]}...\n\n'
    
    await ctx.send(msg)

@tasks.loop(minutes=1)
async def check_announcements():
    """Her dakika duyuruları kontrol et"""
    now = datetime.now().time()
    now = time(now.hour, now.minute)
    
    for ann in announcements:
        if ann['time'].hour == now.hour and ann['time'].minute == now.minute:
            channel = bot.get_channel(ann['channel_id'])
            if channel:
                try:
                    await channel.send(f'📢 **OTOMATİK DUYURU**\n\n{ann["message"]}')
                    print(f'✅ Duyuru gönderildi: ID {ann["id"]}')
                except:
                    print(f'❌ Duyuru gönderilemedi: ID {ann["id"]}')

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
    
    embed.add_field(name='📢 Duyuru', value='`!duyuru #kanal mesaj` - Anlık duyuru\n`!otomatik_duyuru HH:MM #kanal mesaj` - Günlük otomatik duyuru\n`!duyuru_liste` - Tüm duyuruları göster\n`!duyuru_sil ID` - ID ile duyuru sil', inline=False)
    embed.add_field(name='⚙️ Diğer', value='`!ping` - Gecikme testi\n`!yardim` - Bu menü', inline=False)
    
    await ctx.send(embed=embed)

# Hata yakalama
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ Bunu yapmak için yetkin yok!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Eksik parametre! Doğru kullanım:\n`!{ctx.command.name} {ctx.command.signature}`')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('❌ Hatalı parametre! Kanalı # ile etiketle, saati HH:MM formatında yaz.')
    else:
        print(f'Hata: {error}')

# Botu çalıştır
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
