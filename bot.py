import discord
import yt_dlp
from discord.ext import commands, tasks
import os
import aiosqlite
import pytz
from datetime import datetime, time
from dotenv import load_dotenv

load_dotenv()

# Türkiye saat dilimi
TR_TZ = pytz.timezone('Europe/Istanbul')

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(command_prefix='!', intents=intents)
ytdl = yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True})
ffmpeg_options = {'options': '-vn'}

# Railway'de /data dizini persistent volume olarak mount edilir
DB_PATH = os.getenv('DATABASE_PATH', '/data/announcements.db')
EVENT_CHANNEL_ID = int(os.getenv('EVENT_CHANNEL_ID', '792408594465030165'))

TURKCE_GUNLER = {
    'pazartesi': 0, 'sali': 1, 'salı': 1, 'carsamba': 2, 'çarşamba': 2,
    'persembe': 3, 'perşembe': 3, 'cuma': 4, 'cumartesi': 5, 'pazar': 6
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    await init_db()
    await load_system_events()
    check_all_announcements.start()
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif!')
    print(f'💾 Veritabanı: {DB_PATH}')

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Günlük duyurular
        await db.execute('''
            CREATE TABLE IF NOT EXISTS daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                created_by TEXT
            )
        ''')
        # Haftalık duyurular
        await db.execute('''
            CREATE TABLE IF NOT EXISTS weekly (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day INTEGER NOT NULL,
                day_name TEXT,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                guild_id INTEGER,
                created_by TEXT,
                is_system BOOLEAN DEFAULT 0
            )
        ''')
        # Tarihli duyurular
        await db.execute('''
            CREATE TABLE IF NOT EXISTS scheduled (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                created_by TEXT,
                sent BOOLEAN DEFAULT 0
            )
        ''')
        await db.commit()

async def load_system_events():
    """Otomatik etkinlikleri yükle (sadece bir kere)"""
    events = [
        # (day, hour, minute, message, day_name)
        (0, 10, 50, "📖 Kayıp Alfabe", "Pazartesi"),
        (0, 11, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 12, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren", "Pazartesi"),
        (0, 15, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 16, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 17, 50, "⚔️ Düello Turnuvası (Savaşçı)", "Pazartesi"),
        (0, 18, 30, "🐉 Antik Ejderha Kutbu", "Pazartesi"),
        (0, 18, 50, "🌐 Sanal Evren", "Pazartesi"),
        (0, 19, 20, "🛡️ Savaş Arenası", "Pazartesi"),
        (0, 20, 5, "⚔️ Grup Düello Turnuvası", "Pazartesi"),
        (0, 21, 50, "📖 Kayıp Alfabe", "Pazartesi"),
        (1, 9, 50, "🟢 Yeşil Vadi", "Salı"),
        (1, 10, 50, "🟢 Yeşil Vadi", "Salı"),
        (1, 11, 50, "📖 Kayıp Alfabe", "Salı"),
        (1, 12, 50, "🌐 Sanal Evren", "Salı"),
        (1, 15, 50, "🟢 Yeşil Vadi", "Salı"),
        (1, 16, 50, "🟢 Yeşil Vadi", "Salı"),
        (1, 17, 50, "⚔️ Düello Turnuvası (Ninja)", "Salı"),
        (1, 18, 50, "🌐 Sanal Evren", "Salı"),
        (1, 19, 20, "🛡️ Savaş Arenası", "Salı"),
        (1, 20, 5, "⚔️ Grup Düello Turnuvası", "Salı"),
        (2, 9, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 10, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 11, 50, "🌐 Sanal Evren", "Çarşamba"),
        (2, 15, 50, "📖 Kayıp Alfabe", "Çarşamba"),
        (2, 16, 50, "📖 Kayıp Alfabe", "Çarşamba"),
        (2, 17, 50, "⚔️ Düello Turnuvası (Sura)", "Çarşamba"),
        (2, 18, 30, "🐉 Antik Ejderha Kutbu", "Çarşamba"),
        (2, 18, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 19, 20, "👑 Üç İmparatorluk Savaşı", "Çarşamba"),
        (2, 21, 50, "📖 Kayıp Alfabe", "Çarşamba"),
        (3, 10, 50, "📖 Kayıp Alfabe", "Perşembe"),
        (3, 11, 50, "🟢 Yeşil Vadi", "Perşembe"),
        (3, 12, 50, "🟢 Yeşil Vadi", "Perşembe"),
        (3, 13, 50, "🌐 Sanal Evren", "Perşembe"),
        (3, 15, 50, "📖 Kayıp Alfabe", "Perşembe"),
        (3, 16, 50, "🟢 Yeşil Vadi", "Perşembe"),
        (3, 17, 50, "⚔️ Düello Turnuvası (Şaman)", "Perşembe"),
        (3, 18, 50, "🟢 Yeşil Vadi", "Perşembe"),
        (3, 19, 20, "🛡️ Savaş Arenası", "Perşembe"),
        (4, 9, 50, "📖 Kayıp Alfabe", "Cuma"),
        (4, 10, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 11, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren", "Cuma"),
        (4, 15, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 16, 50, "⚔️ Düello Turnuvası (Genel)", "Cuma"),
        (4, 17, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 18, 30, "🐉 Antik Ejderha Kutbu", "Cuma"),
        (4, 19, 0, "🛡️ Savaş Arenası", "Cuma"),
        (4, 19, 20, "🌐 Sanal Evren", "Cuma"),
        (4, 20, 5, "⚔️ Grup Düello Turnuvası", "Cuma"),
        (5, 9, 50, "📖 Kayıp Alfabe", "Cumartesi"),
        (5, 10, 50, "📖 Kayıp Alfabe", "Cumartesi"),
        (5, 11, 50, "🟢 Yeşil Vadi", "Cumartesi"),
        (5, 12, 50, "🟢 Yeşil Vadi", "Cumartesi"),
        (5, 13, 50, "🌐 Sanal Evren", "Cumartesi"),
        (5, 15, 50, "📖 Kayıp Alfabe", "Cumartesi"),
        (5, 16, 50, "📖 Kayıp Alfabe", "Cumartesi"),
        (5, 17, 50, "🟢 Yeşil Vadi", "Cumartesi"),
        (5, 18, 30, "🐉 Antik Ejderha Kutbu", "Cumartesi"),
        (5, 18, 50, "🟢 Yeşil Vadi", "Cumartesi"),
        (5, 19, 20, "👑 Üç İmparatorluk Savaşı", "Cumartesi"),
        (5, 19, 50, "🌐 Sanal Evren", "Cumartesi"),
        (5, 22, 50, "🔥 Kusursuz Cehennem", "Cumartesi"),
        (6, 9, 50, "🟢 Yeşil Vadi", "Pazar"),
        (6, 10, 50, "🟢 Yeşil Vadi", "Pazar"),
        (6, 11, 50, "📖 Kayıp Alfabe", "Pazar"),
        (6, 12, 50, "📖 Kayıp Alfabe", "Pazar"),
        (6, 13, 50, "🌐 Sanal Evren", "Pazar"),
        (6, 14, 50, "🌐 Sanal Evren", "Pazar"),
        (6, 15, 50, "🟢 Yeşil Vadi", "Pazar"),
        (6, 16, 50, "🟢 Yeşil Vadi", "Pazar"),
        (6, 17, 50, "📖 Kayıp Alfabe", "Pazar"),
        (6, 18, 30, "🐉 Antik Ejderha Kutbu", "Pazar"),
        (6, 18, 50, "📖 Kayıp Alfabe", "Pazar"),
        (6, 19, 20, "🛡️ Savaş Arenası", "Pazar"),
    ]
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT COUNT(*) FROM weekly WHERE is_system = 1')
        count = await cursor.fetchone()
        
        if count[0] == 0:
            for day, hour, minute, msg, day_name in events:
                full_msg = f"||@everyone|| 📢 10 dk sonra {msg} başlıyor!"
                await db.execute('''
                    INSERT INTO weekly (day, day_name, channel_id, message, hour, minute, is_system, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 'System')
                ''', (day, day_name, EVENT_CHANNEL_ID, full_msg, hour, minute))
            await db.commit()
            print(f'✅ {len(events)} sistem etkinliği yüklendi!')

# ==================== KOMUTLAR ====================

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_duyuru(ctx, saat: str, kanal: discord.TextChannel, *, mesaj):
    try:
        hour, minute = map(int, saat.split(':'))
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'INSERT INTO daily (channel_id, message, hour, minute, guild_id, created_by) VALUES (?, ?, ?, ?, ?, ?)',
                (kanal.id, mesaj, hour, minute, ctx.guild.id, ctx.author.name)
            )
            await db.commit()
            await ctx.send(f'✅ Günlük duyuru ayarlandı! ID: **{cursor.lastrowid}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def gunluk_sil(ctx, id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM daily WHERE id = ? AND guild_id = ?', (id, ctx.guild.id))
        await db.commit()
        await ctx.send(f'✅ Günlük duyuru ID **{id}** silindi!')

@bot.command()
async def gunluk_liste(ctx):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT id, hour, minute FROM daily WHERE guild_id = ?', (ctx.guild.id,)
        )
        rows = await cursor.fetchall()
        
        if not rows:
            return await ctx.send('📋 Günlük duyuru yok!')
        
        msg = '📋 **Günlük Duyurular:**\\n\\n'
        for row in rows:
            msg += f'🆔 **{row[0]}** | 🕐 {row[1]:02d}:{row[2]:02d}\\n'
        await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_duyuru(ctx, gun: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    gun_norm = gun.lower().replace('ç', 'c').replace('ğ', 'g').replace('ı', 'i').replace('ö', 'o').replace('ş', 's').replace('ü', 'u')
    if gun_norm not in TURKCE_GUNLER:
        return await ctx.send('❌ Geçersiz gün!')
    
    try:
        hour, minute = map(int, saat.split(':'))
        day_no = TURKCE_GUNLER[gun_norm]
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'INSERT INTO weekly (day, day_name, channel_id, message, hour, minute, guild_id, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (day_no, gun.capitalize(), kanal.id, mesaj, hour, minute, ctx.guild.id, ctx.author.name)
            )
            await db.commit()
            await ctx.send(f'✅ Haftalık duyuru ayarlandı! ID: **{cursor.lastrowid}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def haftalik_sil(ctx, id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Sistem etkinliklerini silmeyi engelle (is_system = 0 olanları sil)
        await db.execute('DELETE FROM weekly WHERE id = ? AND guild_id = ? AND is_system = 0', (id, ctx.guild.id))
        await db.commit()
        await ctx.send(f'✅ Haftalık duyuru ID **{id}** silindi!')

@bot.command(name='haftalik_liste')
async def haftalik_liste(ctx):
    embed = discord.Embed(title='📅 HAFTALIK DUYURULAR', color=0x3498db)
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Sistem etkinlikleri
        cursor = await db.execute('SELECT day_name, hour, minute, message FROM weekly WHERE is_system = 1 ORDER BY day, hour, minute')
        system_events = await cursor.fetchall()
        
        if system_events:
            days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
            text = ""
            current_day = ""
            for day_name, hour, minute, msg in system_events:
                if day_name != current_day:
                    text += f"\\n**{day_name}**\\n"
                    current_day = day_name
                clean_msg = msg.replace('||@everyone|| 📢 10 dk sonra ', '').replace(' başlıyor!', '')
                text += f"🕐 {hour:02d}:{minute:02d} → {clean_msg}\\n"
            embed.add_field(name=f"🤖 Sistem Etkinlikleri", value=text[:1000] or "Yok", inline=False)
        
        # Kullanıcı etkinlikleri
        cursor = await db.execute(
            'SELECT id, day_name, hour, minute, channel_id FROM weekly WHERE guild_id = ? AND is_system = 0 ORDER BY day, hour',
            (ctx.guild.id,)
        )
        user_events = await cursor.fetchall()
        
        if user_events:
            text = ""
            for id, day_name, hour, minute, ch_id in user_events:
                channel = bot.get_channel(ch_id)
                ch_mention = channel.mention if channel else f"ID:{ch_id}"
                text += f"🆔 **{id}** | {day_name} {hour:02d}:{minute:02d} → {ch_mention}\\n"
            embed.add_field(name="👤 Eklenen Duyurular", value=text, inline=False)
        else:
            embed.add_field(name="👤 Eklenen Duyurular", value="Henüz eklenen duyuru yok.", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_duyuru(ctx, tarih: str, saat: str, kanal: discord.TextChannel, *, mesaj):
    try:
        tarih = tarih.replace('/', '.')
        gun, ay, yil = map(int, tarih.split('.'))
        date_str = f"{yil}-{ay:02d}-{gun:02d}"
        hour, minute = map(int, saat.split(':'))
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                'INSERT INTO scheduled (date, channel_id, message, hour, minute, guild_id, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (date_str, kanal.id, mesaj, hour, minute, ctx.guild.id, ctx.author.name)
            )
            await db.commit()
            await ctx.send(f'✅ Tarihli duyuru ayarlandı! ID: **{cursor.lastrowid}**')
    except Exception as e:
        await ctx.send(f'❌ Hata: {str(e)}')

@bot.command()
@commands.has_permissions(administrator=True)
async def tarihli_sil(ctx, id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM scheduled WHERE id = ? AND guild_id = ?', (id, ctx.guild.id))
        await db.commit()
        await ctx.send(f'✅ Tarihli duyuru ID **{id}** silindi!')

@bot.command()
async def tarihli_liste(ctx):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'SELECT id, date, hour, minute FROM scheduled WHERE guild_id = ? AND sent = 0',
            (ctx.guild.id,)
        )
        rows = await cursor.fetchall()
        
        if not rows:
            return await ctx.send('📋 Aktif tarihli duyuru yok!')
        
        msg = '📋 **Tarihli Duyurular:**\\n\\n'
        for row in rows:
            msg += f'🆔 **{row[0]}** | 📅 {row[1]} 🕐 {row[2]:02d}:{row[3]:02d}\\n'
        await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, kanal: discord.TextChannel, *, mesaj):
    await kanal.send(mesaj)
    await ctx.send(f'✅ Duyuru gönderildi!')

@bot.command()
async def yardim(ctx):
    embed = discord.Embed(title='🤖 YIKILMAZ BOT - KOMUTLAR', color=0x3498db)
    embed.add_field(name='📅 Haftalık', value='`!haftalik_duyuru Gün HH:MM #kanal mesaj`\\n`!haftalik_liste` | `!haftalik_sil ID`', inline=False)
    embed.add_field(name='🔄 Günlük', value='`!gunluk_duyuru HH:MM #kanal mesaj`\\n`!gunluk_liste` | `!gunluk_sil ID`', inline=False)
    embed.add_field(name='📆 Tarihli', value='`!tarihli_duyuru GG.AA.YYYY HH:MM #kanal mesaj`\\n`!tarihli_liste` | `!tarihli_sil ID`', inline=False)
    embed.add_field(name='📢 Anlık', value='`!duyuru #kanal mesaj`', inline=False)
    await ctx.send(embed=embed)

# ==================== KONTROL SİSTEMİ ====================

@tasks.loop(minutes=1)
async def check_all_announcements():
    now = datetime.now(TR_TZ)  # Türkiye saati
    current_time = time(now.hour, now.minute)
    current_weekday = now.weekday()
    today_str = now.strftime('%Y-%m-%d')
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Günlük duyurular
        cursor = await db.execute('SELECT channel_id, message FROM daily WHERE hour = ? AND minute = ?', 
                                    (current_time.hour, current_time.minute))
        for row in await cursor.fetchall():
            await send_msg(row[0], row[1])
        
        # Haftalık duyurular
        cursor = await db.execute('SELECT channel_id, message FROM weekly WHERE day = ? AND hour = ? AND minute = ?',
                                    (current_weekday, current_time.hour, current_time.minute))
        for row in await cursor.fetchall():
            await send_msg(row[0], row[1])
        
        # Tarihli duyurular
        cursor = await db.execute('SELECT id, channel_id, message FROM scheduled WHERE date = ? AND hour = ? AND minute = ? AND sent = 0',
                                    (today_str, current_time.hour, current_time.minute))
        rows = await cursor.fetchall()
        for id, ch_id, msg in rows:
            await send_msg(ch_id, msg)
            await db.execute('UPDATE scheduled SET sent = 1 WHERE id = ?', (id,))
        
        await db.commit()

async def send_msg(channel_id, message):
    try:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(message)
            print(f'✅ Duyuru gönderildi: {message[:50]}...')
    except Exception as e:
        print(f'❌ Gönderim hatası: {e}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send('❌ Yetkin yok!')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'❌ Eksik parametre! Kullanım: `!{ctx.command.name}`')
    else:
        print(f'Hata: {error}')

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN bulunamadı! Railway Variables'a ekleyin.")

 vc = interaction.guild.voice_client

    try:
        if "http" not in sorgu:
            sorgu = f"ytsearch:{sorgu}"

        info = ytdl.extract_info(sorgu, download=False)
        if 'entries' in info:
            info = info['entries'][0]

        url = info['url']
        title = info.get('title', 'Bilinmeyen')

        source = await discord.FFmpegOpusAudio.from_probe(url, **ffmpeg_options)
        vc.play(source)

        await interaction.followup.send(f"🎵 Çalıyor: {title}")

    except Exception as e:
        await interaction.followup.send(f"❌ Hata: {str(e)}")

@bot.command()
async def cal(ctx, *, sorgu):
    if not ctx.author.voice:
        return await ctx.send("❌ Sesli kanala gir!")

    channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await channel.connect()

    vc = ctx.voice_client

    try:
        if "http" not in sorgu:
            sorgu = f"ytsearch:{sorgu}"

        info = ytdl.extract_info(sorgu, download=False)
        if 'entries' in info:
            info = info['entries'][0]

        url = info['url']
        title = info.get('title', 'Bilinmeyen')

        source = await discord.FFmpegOpusAudio.from_probe(url, options='-vn')
        vc.play(source)

        await ctx.send(f"🎵 Çalıyor: {title}")

    except Exception as e:
        await ctx.send(f"❌ Hata: {str(e)}")

bot.run(TOKEN)
