import discord
from discord.ext import commands, tasks
import os
import aiosqlite
import pytz
from datetime import datetime, time
from dotenv import load_dotenv
import yt_dlp
import asyncio

load_dotenv()

# Türkiye saat dilimi
TR_TZ = pytz.timezone('Europe/Istanbul')

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Railway'de /data dizini persistent volume olarak mount edilir
DB_PATH = os.getenv('DATABASE_PATH', '/data/announcements.db')
EVENT_CHANNEL_ID = int(os.getenv('EVENT_CHANNEL_ID', '792408594465030165'))

TURKCE_GUNLER = {
    'pazartesi': 0, 'sali': 1, 'salı': 1, 'carsamba': 2, 'çarşamba': 2,
    'persembe': 3, 'perşembe': 3, 'cuma': 4, 'cumartesi': 5, 'pazar': 6
}

# ==================== MÜZİK SİSTEMİ ====================

# Müzik kuyrukları {guild_id: [song_info, ...]}
music_queues = {}
# Şu an çalan {guild_id: song_info}
currently_playing = {}

yt_dlp_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'default_search': 'ytsearch',
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 64k'
}

class Song:
    def __init__(self, title, url, webpage_url, duration, thumbnail, requester):
        self.title = title
        self.url = url
        self.webpage_url = webpage_url
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

    def format_duration(self):
        if self.duration:
            minutes, seconds = divmod(self.duration, 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            return f"{minutes}:{seconds:02d}"
        return "Bilinmiyor"

def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]

async def extract_info(query):
    """YouTube'dan video bilgisi çek"""
    with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
        try:
            # Eğer direkt URL ise
            if query.startswith(('http://', 'https://', 'www.', 'youtube.com', 'youtu.be')):
                info = ydl.extract_info(query, download=False)
            else:
                # Arama yap
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info and info['entries']:
                    info = info['entries'][0]
                else:
                    return None
            
            return Song(
                title=info.get('title', 'Bilinmiyor'),
                url=info.get('url') or info.get('formats', [{}])[0].get('url'),
                webpage_url=info.get('webpage_url', ''),
                duration=info.get('duration'),
                thumbnail=info.get('thumbnail', ''),
                requester=None
            )
        except Exception as e:
            print(f"Video bilgisi çekme hatası: {e}")
            return None

def play_next_song(guild_id, voice_client):
    """Sıradaki şarkıyı çal"""
    queue = get_queue(guild_id)
    
    if queue:
        song = queue.pop(0)
        currently_playing[guild_id] = song
        
        def after_playing(error):
            if error:
                print(f"Çalma hatası: {error}")
            asyncio.run_coroutine_threadsafe(
                play_next_song_async(guild_id, voice_client), 
                bot.loop
            )
        
        audio_source = discord.FFmpegPCMAudio(song.url, **ffmpeg_opts)
        voice_client.play(audio_source, after=after_playing)
    else:
        currently_playing.pop(guild_id, None)
        # 5 dakika sonra kanaldan ayrıl
        asyncio.run_coroutine_threadsafe(
            disconnect_after_delay(voice_client), 
            bot.loop
        )

async def play_next_song_async(guild_id, voice_client):
    """Async wrapper for play_next_song"""
    play_next_song(guild_id, voice_client)

async def disconnect_after_delay(voice_client, delay=300):
    """Belirli süre sonra kanaldan ayrıl"""
    await asyncio.sleep(delay)
    if voice_client and not voice_client.is_playing() and voice_client.is_connected():
        await voice_client.disconnect()

# ==================== BOT EVENTS ====================

@bot.event
async def on_ready():
    await init_db()
    await load_system_events()
    check_all_announcements.start()
    print(f'✅ {bot.user} olarak giriş yapıldı!')
    print(f'📊 {len(bot.guilds)} sunucuda aktif!')
    print(f'💾 Veritabanı: {DB_PATH}')
    print(f'🎵 Müzik sistemi aktif!')

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
    """Görseldeki etkinlik saatlerine göre 10 dk önce duyuru"""
    
    # Her etkinlik (day, hour, minute, message, day_name)
    # 10 dk önce duyuru için etkinlik saatinden 10 dk çıkarıyoruz
    
    events = [
        # ========== PAZARTESİ ==========
        (0, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Pazartesi"),
        (0, 14, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 15, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği", "Pazartesi"),
        (0, 18, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 19, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        (0, 20, 50, "⚔️ Düello Turnuvası (Savaşçı)", "Pazartesi"),
        (0, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Pazartesi"),
        (0, 21, 50, "🌐 Sanal Evren Etkinliği", "Pazartesi"),
        (0, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Pazartesi"),
        (0, 23, 5, "❄️ Jotun Etkinliği", "Pazartesi"),
        (0, 0, 50, "📖 Kayıp Alfabe Etkinliği", "Pazartesi"),
        
        # ========== SALI ==========
        (1, 12, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        (1, 13, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        (1, 14, 50, "📖 Kayıp Alfabe Etkinliği", "Salı"),
        (1, 15, 50, "🌐 Sanal Evren Etkinliği", "Salı"),
        (1, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        (1, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        (1, 20, 50, "⚔️ Düello Turnuvası (Ninja)", "Salı"),
        (1, 21, 50, "🌐 Sanal Evren Etkinliği", "Salı"),
        (1, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Salı"),
        (1, 23, 5, "⚔️ Grup Düello Turnuvası", "Salı"),
        
        # ========== ÇARŞAMBA ==========
        (2, 12, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 13, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 14, 50, "🌐 Sanal Evren Etkinliği", "Çarşamba"),
        (2, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        (2, 18, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        (2, 20, 50, "⚔️ Düello Turnuvası (Sura)", "Çarşamba"),
        (2, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Çarşamba"),
        (2, 21, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        (2, 22, 20, "👑 Üç İmparatorluk Savaşı Etkinliği", "Çarşamba"),
        (2, 0, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        
        # ========== PERŞEMBE ==========
        (3, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Perşembe"),
        (3, 14, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        (3, 15, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        (3, 16, 50, "🌐 Sanal Evren Etkinliği", "Perşembe"),
        (3, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Perşembe"),
        (3, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        (3, 20, 50, "⚔️ Düello Turnuvası (Şaman)", "Perşembe"),
        (3, 21, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        (3, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Perşembe"),
        
        # ========== CUMA ==========
        (4, 12, 50, "📖 Kayıp Alfabe Etkinliği", "Cuma"),
        (4, 13, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 14, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği", "Cuma"),
        (4, 18, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 19, 50, "⚔️ Düello Turnuvası (Genel)", "Cuma"),
        (4, 20, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        (4, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Cuma"),
        (4, 21, 50, "🛡️ Savaş Arenası Etkinliği", "Cuma"),
        (4, 22, 10, "🌐 Sanal Evren Etkinliği", "Cuma"),
        (4, 23, 5, "⚔️ Grup Düello Turnuvası", "Cuma"),
        
        # ========== CUMARTESİ ==========
        (5, 12, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        (5, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        (5, 14, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        (5, 15, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        (5, 16, 50, "🌐 Sanal Evren Etkinliği", "Cumartesi"),
        (5, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        (5, 18, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        (5, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        (5, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Cumartesi"),
        (5, 21, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        (5, 22, 20, "👑 Üç İmparatorluk Savaşı Etkinliği", "Cumartesi"),
        (5, 22, 50, "🌐 Sanal Evren Etkinliği", "Cumartesi"),
        (5, 1, 50, "🔥 Kusursuz Cehennem", "Cumartesi"),
        
        # ========== PAZAR ==========
        (6, 12, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        (6, 13, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        (6, 14, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        (6, 15, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        (6, 16, 50, "🌐 Sanal Evren Etkinliği", "Pazar"),
        (6, 17, 50, "🌐 Sanal Evren Etkinliği", "Pazar"),
        (6, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        (6, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        (6, 20, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        (6, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Pazar"),
        (6, 21, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        (6, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Pazar"),
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

# ==================== MÜZİK KOMUTLARI ====================

@bot.command(name='çal', aliases=['play', 'p'])
async def play(ctx, *, query):
    """YouTube'dan müzik çal"""
    
    # Kullanıcı ses kanalında mı?
    if not ctx.author.voice:
        return await ctx.send("❌ Önce bir ses kanalına girin!")
    
    voice_channel = ctx.author.voice.channel
    
    # Bot zaten bir kanalda mı?
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_connected():
        if voice_client.channel != voice_channel:
            return await ctx.send("❌ Bot başka bir kanalda! Önce `!ayrıl` komutunu kullanın.")
    else:
        # Kanala bağlan
        voice_client = await voice_channel.connect()
    
    # YouTube araması veya link
    await ctx.send(f"🔍 Aranıyor: `{query}`")
    song = await extract_info(query)
    
    if not song:
        return await ctx.send("❌ Şarkı bulunamadı!")
    
    # Şarkı bilgisini güncelle
    song.requester = ctx.author.mention
    
    # Sıraya ekle veya hemen çal
    guild_id = ctx.guild.id
    queue = get_queue(guild_id)
    
    if voice_client.is_playing():
        queue.append(song)
        embed = discord.Embed(
            title="🎵 Sıraya Eklendi",
            description=f"**{song.title}**",
            color=0xFF0000
        )
        embed.add_field(name="Süre", value=song.format_duration(), inline=True)
        embed.add_field(name="Sıra", value=str(len(queue)), inline=True)
        embed.set_thumbnail(url=song.thumbnail)
        embed.set_footer(text=f"İsteyen: {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)
    else:
        currently_playing[guild_id] = song
        play_next_song(guild_id, voice_client)
        
        embed = discord.Embed(
            title="▶️ Şimdi Çalıyor",
            description=f"**{song.title}**",
            color=0xFF0000
        )
        embed.add_field(name="Süre", value=song.format_duration(), inline=True)
        embed.set_thumbnail(url=song.thumbnail)
        embed.set_footer(text=f"İsteyen: {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await ctx.send(embed=embed)

@bot.command(name='sıra', aliases=['queue', 'q'])
async def show_queue(ctx):
    """Çalma listesini göster"""
    guild_id = ctx.guild.id
    queue = get_queue(guild_id)
    current = currently_playing.get(guild_id)
    
    embed = discord.Embed(title="🎵 Çalma Listesi", color=0x3498db)
    
    if current:
        embed.add_field(
            name="▶️ Şimdi Çalıyor",
            value=f"**{current.title}** | {current.format_duration()} | {current.requester}",
            inline=False
        )
    else:
        embed.add_field(name="▶️ Şimdi Çalıyor", value="Şu an çalan yok", inline=False)
    
    if queue:
        queue_text = ""
        for i, song in enumerate(queue[:10], 1):
            queue_text += f"`{i}.` {song.title} | {song.format_duration()}\n"
        if len(queue) > 10:
            queue_text += f"\n...ve {len(queue) - 10} şarkı daha"
        embed.add_field(name="📋 Sıradaki Şarkılar", value=queue_text, inline=False)
    else:
        embed.add_field(name="📋 Sıradaki Şarkılar", value="Sıra boş", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='atla', aliases=['skip', 's'])
async def skip(ctx):
    """Şarkıyı atla"""
    voice_client = ctx.guild.voice_client
    
    if not voice_client or not voice_client.is_playing():
        return await ctx.send("❌ Şu an çalan şarkı yok!")
    
    voice_client.stop()
    await ctx.send("⏭️ Şarkı atlandı!")

@bot.command(name='dur', aliases=['pause'])
async def pause(ctx):
    """Müziği duraklat"""
    voice_client = ctx.guild.voice_client
    
    if not voice_client or not voice_client.is_playing():
        return await ctx.send("❌ Şu an çalan şarkı yok!")
    
    voice_client.pause()
    await ctx.send("⏸️ Müzik duraklatıldı!")

@bot.command(name='devam', aliases=['resume'])
async def resume(ctx):
    """Müziği devam ettir"""
    voice_client = ctx.guild.voice_client
    
    if not voice_client or not voice_client.is_paused():
        return await ctx.send("❌ Duraklatılmış müzik yok!")
    
    voice_client.resume()
    await ctx.send("▶️ Müzik devam ediyor!")

@bot.command(name='ayrıl', aliases=['leave', 'disconnect', 'dc'])
async def leave(ctx):
    """Ses kanalından ayrıl"""
    voice_client = ctx.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        return await ctx.send("❌ Bot bir kanalda değil!")
    
    # Sırayı temizle
    guild_id = ctx.guild.id
    music_queues.pop(guild_id, None)
    currently_playing.pop(guild_id, None)
    
    await voice_client.disconnect()
    await ctx.send("👋 Görüşürüz!")

@bot.command(name='temizle', aliases=['clear'])
async def clear_queue(ctx):
    """Çalma listesini temizle"""
    guild_id = ctx.guild.id
    
    if guild_id in music_queues:
        music_queues[guild_id] = []
        await ctx.send("🗑️ Çalma listesi temizlendi!")
    else:
        await ctx.send("❌ Çalma listesi zaten boş!")

@bot.command(name='şarkı', aliases=['np', 'nowplaying'])
async def now_playing(ctx):
    """Şu an çalan şarkıyı göster"""
    guild_id = ctx.guild.id
    current = currently_playing.get(guild_id)
    
    if not current:
        return await ctx.send("❌ Şu an çalan şarkı yok!")
    
    embed = discord.Embed(
        title="▶️ Şimdi Çalıyor",
        description=f"**[{current.title}]({current.webpage_url})**",
        color=0xFF0000
    )
    embed.add_field(name="Süre", value=current.format_duration(), inline=True)
    embed.add_field(name="İsteyen", value=current.requester, inline=True)
    embed.set_thumbnail(url=current.thumbnail)
    
    await ctx.send(embed=embed)

# ==================== DUYURU KOMUTLARI ====================

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
        
        msg = '📋 **Günlük Duyurular:**\n\n'
        for row in rows:
            msg += f'🆔 **{row[0]}** | 🕐 {row[1]:02d}:{row[2]:02d}\n'
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
                    text += f"\n**{day_name}**\n"
                    current_day = day_name
                clean_msg = msg.replace('||@everyone|| 📢 10 dk sonra ', '').replace(' başlıyor!', '')
                text += f"🕐 {hour:02d}:{minute:02d} → {clean_msg}\n"
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
                text += f"🆔 **{id}** | {day_name} {hour:02d}:{minute:02d} → {ch_mention}\n"
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
        
        msg = '📋 **Tarihli Duyurular:**\n\n'
        for row in rows:
            msg += f'🆔 **{row[0]}** | 📅 {row[1]} 🕐 {row[2]:02d}:{row[3]:02d}\n'
        await ctx.send(msg)

@bot.command()
@commands.has_permissions(administrator=True)
async def duyuru(ctx, kanal: discord.TextChannel, *, mesaj):
    await kanal.send(mesaj)
    await ctx.send(f'✅ Duyuru gönderildi!')

@bot.command()
async def yardim(ctx):
    embed = discord.Embed(title='🤖 YIKILMAZ BOT - KOMUTLAR', color=0x3498db)
    
    # Müzik komutları
    embed.add_field(
        name='🎵 Müzik',
        value='`!çal <şarkı/link>` - YouTube\'dan müzik çal\n'
              '`!sıra` - Çalma listesi\n'
              '`!atla` - Şarkıyı atla\n'
              '`!dur` - Duraklat\n'
              '`!devam` - Devam ettir\n'
              '`!şarkı` - Şu an çalan\n'
              '`!temizle` - Sırayı temizle\n'
              '`!ayrıl` - Kanaldan ayrıl',
        inline=False
    )
    
    embed.add_field(name='📅 Haftalık', value='`!haftalik_duyuru Gün HH:MM #kanal mesaj`\n`!haftalik_liste` | `!haftalik_sil ID`', inline=False)
    embed.add_field(name='🔄 Günlük', value='`!gunluk_duyuru HH:MM #kanal mesaj`\n`!gunluk_liste` | `!gunluk_sil ID`', inline=False)
    embed.add_field(name='📆 Tarihli', value='`!tarihli_duyuru GG.AA.YYYY HH:MM #kanal mesaj`\n`!tarihli_liste` | `!tarihli_sil ID`', inline=False)
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

bot.run(TOKEN)
=False)
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

bot.run(TOKEN)
