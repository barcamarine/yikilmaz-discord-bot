import nextcord as discord
from nextcord.ext import commands, tasks
import os
from datetime import datetime, time
import calendar

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Duyuru listeleri
gunluk_duyurular = []  # Her gün aynı saatte tekrarlayan
haftalik_duyurular = []  # Belirli günlerde tekrarlayan (Pazartesi, Salı...)
tarihli_duyurular = []  # Belirli tarihlerde bir kez
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
    
    # ========== ETKİNLİKLERİ OTOMATİK YÜKLE ==========
    await load_events()
    
    check_all_announcements.start()

async def load_events():
    """Tüm etkinlikleri otomatik yükle (10 dk önce) - Jotun YOK"""
    global haftalik_id
    
    # Kanal ID'sini buraya yaz (etkinlik kanalının ID'si)
    # Örnek: 1234567890123456789
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
                'guild_id': None,  # Tüm sunucular için
                'created_by': 'System'
            }
            haftalik_duyurular.append(duyuru)
            haftalik_id += 1
    
    print(f'✅ {len(haftalik_duyurular)} etkinlik yüklendi!')

# ==================== GÜNLÜK DUYURULAR (Her Gün) ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_duyuru(ctx, saat: str, kanal: discord.TextChannel, *, mesaj):
    """Her gün aynı saatte tekrarlayan duyuru"""
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
        
        await ctx.send(f'✅ **Günlük duyuru** ayarlandı!\n🆔 ID: **{duyuru["id"]}**\n🕐 Her gün saat: **{saat}**\n📢 Kanal: {kanal.mention}\n📝 Mesaj: {mesaj[:100]}...')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}\nDoğru kullanım: `!gunluk_duyuru 09:00 #kanal Mesaj`')

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_sil(ctx, id: int):
    """Günlük duyuru sil"""
    global gunluk_duyurular
    original_len = len(gunluk_duyurular)
    gunluk_duyurular = [d for d in gunluk_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    
    if len(gunluk_duyurular) < original_len:
        await ctx.send(f'✅ Günlük duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bu ID ile günlük duyuru bulunamadı!')

@bot.command()
async def gunluk_liste(ctx):
    """Günlük duyuruları listele"""
    guild_duyurular = [d for d in gunluk_duyurular if d['guild_id'] == ctx.guild.id]
    if not guild_duyurular:
        await ctx.send('📋 Günlük duyuru yok!')
        return
    
    msg = '📋 **Günlük Duyurular (Her Gün):**\n\n'
    for d in guild_duyurular:
        channel = bot.get_channel(d['channel_id'])
        channel_mention = channel.mention if channel else '❌ Silinmiş Kanal'
        saat = d['time'].strftime('%H:%M')
        msg += f'🆔 **{d["id"]}** | 🕐 {saat} | {channel_mention}\n📝 {d["message"][:50]}...\n\n'
    
    await ctx.send(msg)

# ==================== HAFTALIK DUYURULAR (Belirli Gün) ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_duyuru(ctx, gun: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    """Belirli günde tekrarlayan duyuru (Pazartesi, Salı, Çarşamba, Perşembe, Cuma, Cumartesi, Pazar)"""
    global haftalik_id
    
    gun_normalize = gun.lower().replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    
    if gun_normalize not in TURKCE_GUNLER:
        await ctx.send('❌ Geçersiz gün! Doğru kullanım: Pazartesi, Salı, Çarşamba, Perşembe, Cuma, Cumartesi, Pazar')
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
        
        await ctx.send(f'✅ **Haftalık duyuru** ayarlandı!\n🆔 ID: **{duyuru["id"]}**\n📅 Her **{gun.capitalize()}** saat **{saat}**\n📢 Kanal: {kanal.mention}\n📝 Mesaj: {mesaj[:100]}...')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}\nDoğru kullanım: `!haftalik_duyuru Pazartesi 18:15 #kanal Mesaj`')

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_sil(ctx, id: int):
    """Haftalık duyuru sil"""
    global haftalik_duyurular
    original_len = len(haftalik_duyurular)
    haftalik_duyurular = [d for d in haftalik_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    
    if len(haftalik_duyurular) < original_len:
        await ctx.send(f'✅ Haftalık duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bu ID ile haftalık duyuru bulunamadı!')

@bot.command()
async def haftalik_liste(ctx):
    """Haftalık duyuruları listele"""
    guild_duyurular = [d for d in haftalik_duyurular if d['guild_id'] == ctx.guild.id or d['guild_id'] is None]
    if not guild_duyurular:
        await ctx.send('📋 Haftalık duyuru yok!')
        return
    
    gun_siralama = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
    guild_duyurular.sort(key=lambda x: (x['gun'], x['time'].hour, x['time'].minute))
    
    # Sayfalama (Discord 2000 karakter limiti)
    sayfa = 1
    toplam = len(guild_duyurular)
    
    msg = f'📋 **Haftalık Duyurular (Sayfa {sayfa}):**\nToplam: {toplam} adet\n\n'
    
    for i, d in enumerate(guild_duyurular[:20]):  # İlk 20
        channel = bot.get_channel(d['channel_id'])
        channel_mention = channel.mention if channel else '❌ Silinmiş Kanal'
        saat = d['time'].strftime('%H:%M')
        msg += f'🆔 **{d["id"]}** | 📅 {d["gun_adi"]} 🕐 {saat}\n📝 {d["message"][:40]}...\n\n'
        
        if len(msg) > 1800:
            await ctx.send(msg)
            msg = f'📋 **Haftalık Duyurular (Devam):**\n\n'
    
    if msg:
        await ctx.send(msg)

# ==================== TARİHLİ DUYURULAR (Bir Kez) ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_duyuru(ctx, tarih: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    """Belirli tarihte bir kez gönderilen duyuru (format: GG.AA.YYYY)"""
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
        
        await ctx.send(f'✅ **Tarihli duyuru** ayarlandı!\n🆔 ID: **{duyuru["id"]}**\n📅 Tarih: **{gun:02d}.{ay:02d}.{yil}** saat **{saat}**\n📢 Kanal: {kanal.mention}\n📝 Mesaj: {mesaj[:100]}...')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}\nDoğru kullanım: `!tarihli_duyuru 25.12.2024 20:00 #kanal Mesaj`')

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_sil(ctx, id: int):
    """Tarihli duyuru sil"""
    global tarihli_duyurular
    original_len = len(tarihli_duyurular)
    tarihli_duyurular = [d for d in tarihli_duyurular if not (d['id'] == id and d['guild_id'] == ctx.guild.id)]
    
    if len(tarihli_duyurular) < original_len:
        await ctx.send(f'✅ Tarihli duyuru ID **{id}** silindi!')
    else:
        await ctx.send('❌ Bu ID ile tarihli duyuru bulunamadı!')

@bot.command()
async def tarihli_liste(ctx):
    """Tarihli duyuruları listele"""
    guild_duyurular = [d for d in tarihli_duyurular if d['guild_id'] == ctx.guild.id and not d['sent']]
    if not guild_duyurular:
        await ctx.send('📋 Aktif tarihli duyuru yok!')
        return
    
    guild_duyurular.sort(key=lambda x: x['tarih'])
    
    msg = '📋 **Tarihli Duyurular (Bekleyen):**\n\n'
    for d in guild_duyurular:
        channel = bot.get_channel(d['channel_id'])
        channel_mention = channel.mention if channel else '❌ Silinmiş Kanal'
        saat = d['time'].strftime('%H:%M')
        durum = '✅ Gönderildi' if d['sent'] else '⏳ Bekliyor'
        msg += f'🆔 **{d["id"]}** | 📅 {d["tarih_str"]} 🕐 {saat} | {durum}\n📢 {channel_mention}\n📝 {d["message"][:50]}...\n\n'
    
    await ctx.send(msg)

# ==================== ANLIK DUYURU ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, kanal: discord.TextChannel, *, mesaj):
    """Hemen şimdi duyuru at"""
    await kanal.send(mesaj)
    await ctx.send(f'✅ Duyuru {kanal.mention} kanalına gönderildi!')

# ==================== TÜM LİSTEYİ GÖR ====================

@bot.command()
async def tum_duyurular(ctx):
    """Tüm duyuruları göster"""
    msg = '📋 **TÜM DUYURULAR:**\n\n'
    
    gunluk = [d for d in gunluk_duyurular if d['guild_id'] == ctx.guild.id]
    if gunluk:
        msg += f'🔄 **Günlük ({len(gunluk)} adet):**\n'
        for d in gunluk:
            saat = d['time'].strftime('%H:%M')
            msg += f'  🆔{d["id"]} 🕐{saat}\n'
        msg += '\n'
    
    haftalik = [d for d in haftalik_duyurular if d['guild_id'] == ctx.guild.id or d['guild_id'] is None]
    if haftalik:
        msg += f'📅 **Haftalık ({len(haftalik)} adet):**\n'
        for d in haftalik[:10]:  # İlk 10
            saat = d['time'].strftime('%H:%M')
            msg += f'  🆔{d["id"]} {d["gun_adi"]} 🕐{saat}\n'
        if len(haftalik) > 10:
            msg += f'  ... ve {len(haftalik)-10} adet daha\n'
        msg += '\n'
    
    tarihli = [d for d in tarihli_duyurular if d['guild_id'] == ctx.guild.id and not d['sent']]
    if tarihli:
        msg += f'📆 **Tarihli ({len(tarihli)} adet):**\n'
        for d in tarihli:
            saat = d['time'].strftime('%H:%M')
            msg += f'  🆔{d["id"]} {d["tarih_str"]} 🕐{saat}\n'
    
    if not gunluk and not haftalik and not tarihli:
        msg += '❌ Hiç duyuru yok!'
    
    await ctx.send(msg)

# ==================== KONTROL SİSTEMİ ====================

@tasks.loop(minutes=1)
async def check_all_announcements():
    """Tüm duyuruları kontrol et"""
    now = datetime.now()
    current_time = time(now.hour, now.minute)
    current_weekday = now.weekday()
    
    # 1. Günlük duyurular (Her gün)
    for d in gunluk_duyurular:
        if d['time'].hour == current_time.hour and d['time'].minute == current_time.minute:
            await send_announcement(d)
    
    # 2. Haftalık duyurular (Belirli gün)
    for d in haftalik_duyurular:
        if (d['gun'] == current_weekday and 
            d['time'].hour == current_time.hour and 
            d['time'].minute == current_time.minute):
            await send_announcement(d)
    
    # 3. Tarihli duyurular (Bir kez)
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
    """Duyuruyu gönder"""
    try:
        channel = bot.get_channel(duyuru['channel_id'])
        if channel:
            await channel.send(duyuru['message'])
            print(f'✅ Duyuru gönderildi: ID {duyuru.get("id", "N/A")}')
    except Exception as e:
        print(f'❌ Duyuru gönderilemedi: {e}')

# ==================== YARDIM ====================

@bot.command()
async def yardim(ctx):
    """Yardım menüsü"""
    embed = discord.Embed(title='🤖 YIKILMAZ BOT - KOMUTLAR', color=0x3498db)
    
    embed.add_field(name='🔄 Günlük Duyuru', 
                    value='`!gunluk_duyuru HH:MM #kanal mesaj`\n`!gunluk_liste` | `!gunluk_sil ID`', 
                    inline=False)
    
    embed.add_field(name='📅 Haftalık Duyuru', 
                    value='`!haftalik_duyuru Gün HH:MM #kanal mesaj`\n`!haftalik_liste` | `!haftalik_sil ID`', 
                    inline=False)
    
    embed.add_field(name='📆 Tarihli Duyuru', 
                    value='`!tarihli_duyuru GG.AA.YYYY HH:MM #kanal mesaj`\n`!tarihli_liste` | `!tarihli_sil ID`', 
                    inline=False)
    
    embed.add_field(name='📢 Anlık Duyuru', 
                    value='`!duyuru #kanal mesaj` - Hemen gönder', 
                    inline=False)
    
    embed.add_field(name='📋 Listeleme', 
                    value='`!tum_duyurular` - Hepsini gör\n`!gunluk_liste` | `!haftalik_liste` | `!tarihli_liste`', 
                    inline=False)
    
    embed.add_field(name='⚙️ Diğer', 
                    value='`!ping` - Gecikme testi\n`!yardim` - Bu menü', 
                    inline=False)
    
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
# ==================== MÜZİK SİSTEMİ ====================
import yt_dlp
import asyncio

# YouTube ayarları
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# Müzik komutları

@bot.command()
async def join(ctx):
    """Ses kanalına katıl"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'🔊 **{channel.name}** kanalına katıldım!')
    else:
        await ctx.send('❌ Önce bir ses kanalına gir!')

@bot.command()
async def leave(ctx):
    """Ses kanalından ayrıl"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('👋 Görüşürüz!')
    else:
        await ctx.send('❌ Zaten bir kanalda değilim!')

@bot.command(name='çal')
async def cal(ctx, *, url):
    """YouTube URL'si veya arama ile müzik çal"""
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.typing()
            await ctx.send('❌ Önce bir ses kanalına gir veya `!join` yaz!')
            return
    
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
            await ctx.send(f'🎵 Çalıyor: **{player.title}**')
        except Exception as e:
            await ctx.send(f'❌ Hata: {str(e)}\nYouTube linki veya arama kelimesi dene!')

@bot.command()
async def stop(ctx):
    """Müziği durdur"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send('⏹️ Müzik durduruldu!')
    else:
        await ctx.send('❌ Şu an müzik çalmıyor!')

@bot.command()
async def pause(ctx):
    """Müziği duraklat"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('⏸️ Müzik duraklatıldı!')
    else:
        await ctx.send('❌ Şu an müzik çalmıyor!')

@bot.command()
async def resume(ctx):
    """Müziği devam ettir"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('▶️ Müzik devam ediyor!')
    else:
        await ctx.send('❌ Duraklatılmış müzik yok!')
bot.run(TOKEN)
