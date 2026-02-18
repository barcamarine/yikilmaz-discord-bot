import nextcord as discord
from nextcord.ext import commands, tasks
import os
from datetime import datetime, time

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Duyuru listeleri
gunluk_duyurular = []
haftalik_duyurular = []
tarihli_duyurular = []
gunluk_id = 1
haftalik_id = 1
tarihli_id = 1

# Türkçe gün isimleri
TURKCE_GUNLER = {
    'pazartesi': 0,
    'sali': 1,
    'salı': 1,
    'carsamba': 2,
    'çarşamba': 2,
    'persembe': 3,
    'perşembe': 3,
    'cuma': 4,
    'cumartesi': 5,
    'pazar': 6
}

@bot.event
async def on_ready():
    global gunluk_id, haftalik_id, tarihli_id
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif!')
    print(f'⏰ Bot saati: {datetime.now()}')
    
    # Etkinlikleri otomatik yükle
    await load_events()
    
    check_all_announcements.start()

async def load_events():
    """Tüm etkinlikleri otomatik yükle (10 dk önce) - Jotun YOK"""
    global haftalik_id
    
    # KANAL ID'SİNİ BURAYA YAZ (ETKİNLİK KANALININ ID'Sİ)
    KANAL_ID = 792408594465030165  # <-- BUNU DEĞİŞTİR!
    
    # ========== PAZARTESİ ==========
    events_pzt = [
        (10, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (11, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (12, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (16, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (17, 50, "⚔️ Düello Turnuvası (Savaşçı) başlıyor!"),
        (18, 30, "🐉 Antik Ejderha Kutbu Etkinliği başlıyor!"),
        (18, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (19, 20, "🛡️ Savaş Arenası Etkinliği başlıyor!"),
        (20, 5, "⚔️ Grup Düello Turnuvası başlıyor!"),
        (21, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
    ]
    
    # ========== SALI ==========
    events_sal = [
        (9, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (10, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (11, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (12, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (16, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (17, 50, "⚔️ Düello Turnuvası (Ninja) başlıyor!"),
        (18, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (19, 20, "🛡️ Savaş Arenası Etkinliği başlıyor!"),
        (20, 5, "⚔️ Grup Düello Turnuvası başlıyor!"),
    ]
    
    # ========== ÇARŞAMBA ==========
    events_crs = [
        (9, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (10, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (11, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (16, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (17, 50, "⚔️ Düello Turnuvası (Sura) başlıyor!"),
        (18, 30, "🐉 Antik Ejderha Kutbu Etkinliği başlıyor!"),
        (18, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (19, 20, "👑 Üç İmparatorluk Savaşı Etkinliği başlıyor!"),
        (21, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
    ]
    
    # ========== PERŞEMBE ==========
    events_prş = [
        (10, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (11, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (12, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (13, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (16, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (17, 50, "⚔️ Düello Turnuvası (Şaman) başlıyor!"),
        (18, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (19, 20, "🛡️ Savaş Arenası Etkinliği başlıyor!"),
    ]
    
    # ========== CUMA ==========
    events_cum = [
        (9, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (10, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (11, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (16, 50, "⚔️ Düello Turnuvası (Genel) başlıyor!"),
        (17, 50, "🔥 Kusursuz Cehennem başlıyor!"),
        (18, 30, "🐉 Antik Ejderha Kutbu Etkinliği başlıyor!"),
        (19, 0, "🛡️ Savaş Arenası Etkinliği başlıyor!"),
        (19, 20, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (20, 5, "⚔️ Grup Düello Turnuvası başlıyor!"),
    ]
    
    # ========== CUMARTESİ ==========
    events_cts = [
        (9, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (10, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (11, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (12, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (13, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (16, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (17, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (18, 30, "🐉 Antik Ejderha Kutbu Etkinliği başlıyor!"),
        (18, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (19, 20, "👑 Üç İmparatorluk Savaşı Etkinliği başlıyor!"),
        (19, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (22, 50, "🔥 Kusursuz Cehennem başlıyor!"),
    ]
    
    # ========== PAZAR ==========
    events_pzr = [
        (9, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (10, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (11, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (12, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (13, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (14, 50, "🌐 Sanal Evren Etkinliği başlıyor!"),
        (15, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (16, 50, "🟢 Yeşil Vadi Etkinliği başlıyor!"),
        (17, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (18, 30, "🐉 Antik Ejderha Kutbu Etkinliği başlıyor!"),
        (18, 50, "📖 Kayıp Alfabe Etkinliği başlıyor!"),
        (19, 20, "🛡️ Savaş Arenası Etkinliği başlıyor!"),
    ]
    
    # Tüm etkinlikleri ekle
    gunler = [
        (0, events_pzt, "Pazartesi"),
        (1, events_sal, "Salı"),
        (2, events_crs, "Çarşamba"),
        (3, events_prş, "Perşembe"),
        (4, events_cum, "Cuma"),
        (5, events_cts, "Cumartesi"),
        (6, events_pzr, "Pazar"),
    ]
    
    for gun_no, events, gun_adi in gunler:
        for hour, minute, message in events:
            duyuru = {
                'id': haftalik_id,
                'gun': gun_no,
                'gun_adi': gun_adi,
                'channel_id': KANAL_ID,
                'message': f"||@everyone|| 📢 10 dk sonra {message}",
                'time': time(hour, minute),
                'guild_id': None,
                'created_by': 'System'
            }
            haftalik_duyurular.append(duyuru)
            haftalik_id += 1
    
    print(f'✅ {len(haftalik_duyurular)} etkinlik yüklendi!')

# ==================== GÜNLÜK DUYURULAR ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_duyuru(ctx, saat: str, kanal: discord.TextChannel, *, mesaj):
    global gunluk_id
    try:
        hour, minute = map(int, saat.split(':'))
        duyuru = {
            'id': gunluk_id,
            'channel_id': kanal.id,
            'message': mesaj,
            'time': time(hour, minute),
            'guild_id': ctx.guild.id,
            'created_by': ctx.author.name
        }
        gunluk_duyurular.append(duyuru)
        gunluk_id += 1
        await ctx.send(f'✅ Günlük duyuru ayarlandı! ID: **{duyuru["id"]}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_sil(ctx, id: int):
    global gunluk_duyurular
    original_len = len(gunluk_duyurular)
    gunluk_duyurular = [d for d in gunluk_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    if len(gunluk_duyurular) < original_len:
        await ctx.send(f'✅ Günlük duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bulunamadı!')

@bot.command()
async def gunluk_liste(ctx):
    guild_duyurular = [d for d in gunluk_duyurular if d['guild_id'] == ctx.guild.id]
    if not guild_duyurular:
        await ctx.send('📋 Günlük duyuru yok!')
        return
    msg = '📋 **Günlük Duyurular:**\n\n'
    for d in guild_duyurular:
        saat = d['time'].strftime('%H:%M')
        msg += f'🆔 **{d["id"]}** | 🕐 {saat}\n'
    await ctx.send(msg)

# ==================== HAFTALIK DUYURULAR ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_duyuru(ctx, gun: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    global haftalik_id
    gun_normalize = gun.lower().replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    if gun_normalize not in TURKCE_GUNLER:
        await ctx.send('❌ Geçersiz gün!')
        return
    try:
        hour, minute = map(int, saat.split(':'))
        gun_no = TURKCE_GUNLER[gun_normalize]
        duyuru = {
            'id': haftalik_id,
            'gun': gun_no,
            'gun_adi': gun.capitalize(),
            'channel_id': kanal.id,
            'message': mesaj,
            'time': time(hour, minute),
            'guild_id': ctx.guild.id,
            'created_by': ctx.author.name
        }
        haftalik_duyurular.append(duyuru)
        haftalik_id += 1
        await ctx.send(f'✅ Haftalık duyuru ayarlandı! ID: **{duyuru["id"]}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_sil(ctx, id: int):
    global haftalik_duyurular
    original_len = len(haftalik_duyurular)
    haftalik_duyurular = [d for d in haftalik_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    if len(haftalik_duyurular) < original_len:
        await ctx.send(f'✅ Haftalık duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bulunamadı!')

@bot.command()
async def haftalik_liste(ctx):
    guild_duyurular = [d for d in haftalik_duyurular if d['guild_id'] == ctx.guild.id or d['guild_id'] is None]
    if not guild_duyurular:
        await ctx.send('📋 Haftalık duyuru yok!')
        return
    guild_duyurular.sort(key=lambda x: (x['gun'], x['time'].hour, x['time'].minute))
    msg = '📋 **Haftalık Duyurular:**\n\n'
    for d in guild_duyurular[:15]:
        saat = d['time'].strftime('%H:%M')
        msg += f'🆔 **{d["id"]}** | 📅 {d["gun_adi"]} 🕐 {saat}\n'
    await ctx.send(msg)

# ==================== TARİHLİ DUYURULAR ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_duyuru(ctx, tarih: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    global tarihli_id
    try:
        tarih = tarih.replace('/', '.')
        gun, ay, yil = map(int, tarih.split('.'))
        hedef_tarih = datetime(yil, ay, gun)
        hour, minute = map(int, saat.split(':'))
        duyuru = {
            'id': tarihli_id,
            'tarih': hedef_tarih,
            'tarih_str': f'{gun:02d}.{ay:02d}.{yil}',
            'channel_id': kanal.id,
            'message': mesaj,
            'time': time(hour, minute),
            'guild_id': ctx.guild.id,
            'created_by': ctx.author.name,
            'sent': False
        }
        tarihli_duyurular.append(duyuru)
        tarihli_id += 1
        await ctx.send(f'✅ Tarihli duyuru ayarlandı! ID: **{duyuru["id"]}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_sil(ctx, id: int):
    global tarihli_duyurular
    original_len = len(tarihli_duyurular)
    tarihli_duyurular = [d for d in tarihli_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    if len(tarihli_duyurular) < original_len:
        await ctx.send(f'✅ Tarihli duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bulunamadı!')

@bot.command()
async def tarihli_liste(ctx):
    guild_duyurular = [d for d in tarihli_duyurular if d['guild_id'] == ctx.guild.id and not d['sent']]
    if not guild_duyurular:
        await ctx.send('📋 Tarihli duyuru yok!')
        return
    msg = '📋 **Tarihli Duyurular:**\n\n'
    for d in guild_duyurular:
        saat = d['time'].strftime('%H:%M')
        msg += f'🆔 **{d["id"]}** | 📅 {d["tarih_str"]} 🕐 {saat}\n'
    await ctx.send(msg)

# ==================== ANLIK DUYURU ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, kanal: discord.TextChannel, *, mesaj):
    await kanal.send(mesaj)
    await ctx.send(f'✅ Duyuru gönderildi!')

# ==================== YARDIM ====================

@bot.command()
async def yardim(ctx):
    embed = discord.Embed(title='🤖 YIKILMAZ BOT - KOMUTLAR', color=0x3498db)
    embed.add_field(name='📅 Haftalık Duyuru', value='`!haftalik_duyuru Gün HH:MM #kanal mesaj`\n`!haftalik_liste` | `!haftalik_sil ID`', inline=False)
    embed.add_field(name='🔄 Günlük Duyuru', value='`!gunluk_duyuru HH:MM #kanal mesaj`\n`!gunluk_liste` | `!gunluk_sil ID`', inline=False)
    embed.add_field(name='📆 Tarihli Duyuru', value='`!tarihli_duyuru GG.AA.YYYY HH:MM #kanal mesaj`\n`!tarihli_liste` | `!tarihli_sil ID`', inline=False)
    embed.add_field(name='📢 Anlık Duyuru', value='`!duyuru #kanal mesaj`', inline=False)
    await ctx.send(embed=embed)

# ==================== KONTROL SİSTEMİ ====================

@tasks.loop(minutes=1)
async def check_all_announcements():
    now = datetime.now()
    current_time = time(now.hour, now.minute)
    current_weekday = now.weekday()
    
    # Günlük duyurular
    for d in gunluk_duyurular:
        if d['time'].hour == current_time.hour and d['time'].minute == current_time.minute:
            await send_announcement(d)
    
    # Haftalık duyurular
    for d in haftalik_duyurular:
        if (d['gun'] == current_weekday and 
            d['time'].hour == current_time.hour and 
            d['time'].minute == current_time.minute):
            await send_announcement(d)
    
    # Tarihli duyurular
    for d in tarihli_duyurular:
        if (not d['sent'] and 
            d['tarih'].day == now.day and 
            d['tarih'].month == now.month and 
            d['tarih'].year == now.year and
            d['time'].hour == current_time.hour and 
            d['time'].minute == current_time.minute):
            await send_announcement(d)
            d['sent'] = True

async def send_announcement(duyuru):
    try:
        channel = bot.get_channel(duyuru['channel_id'])
        if channel:
            await channel.send(duyuru['message'])
            print(f'✅ Duyuru gönderildi: ID {duyuru.get("id", "N/A")}')
    except Exception as e:
        print(f'❌ Hata: {e}')

# Hata yakalama
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ Yetkin yok!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Eksik parametre! `!{ctx.command.name}`')
    else:
        print(f'Hata: {error}')

# Botu çalıştır
TOKEN = os.getenv('DISCORD_TOKEN')
bot.run(TOKEN)
