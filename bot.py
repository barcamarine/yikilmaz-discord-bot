import discord
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

# Railway'de /data dizini persistent volume olarak mount edilir
DB_PATH = os.getenv('DATABASE_PATH', '/data/announcements.db')
EVENT_CHANNEL_ID = int(os.getenv('EVENT_CHANNEL_ID', '792408594465030165'))

TURKCE_GUNLER = {
    'pazartesi': 0, 'sali': 1, 'salı': 1, 'carsamba': 2, 'çarşamba': 2,
    'persembe': 3, 'perşembe': 3, 'cuma': 4, 'cumartesi': 5, 'pazar': 6
}

@bot.event
async def on_ready():
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
    """Görseldeki etkinlik saatlerine göre 10 dk önce duyuru"""
    
    # Her etkinlik (day, hour, minute, message, day_name)
    # 10 dk önce duyuru için etkinlik saatinden 10 dk çıkarıyoruz
    
    events = [
        # ========== PAZARTESİ ==========
        # 14:00 Kayıp Alfabe → 13:50 duyuru
        (0, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Pazartesi"),
        # 15:00 Kusursuz Cehennem → 14:50 duyuru
        (0, 14, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        # 16:00 Kusursuz Cehennem & Sanal Evren → 15:50 duyuru
        (0, 15, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği", "Pazartesi"),
        # 19:00 Kusursuz Cehennem → 18:50 duyuru
        (0, 18, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        # 20:00 Kusursuz Cehennem → 19:50 duyuru
        (0, 19, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
        # 21:00 Düello Turnuvası (Savaşçı) → 20:50 duyuru
        (0, 20, 50, "⚔️ Düello Turnuvası (Savaşçı)", "Pazartesi"),
        # 21:40 Antik Ejderha Kutbu → 21:30 duyuru
        (0, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Pazartesi"),
        # 22:00 Sanal Evren → 21:50 duyuru
        (0, 21, 50, "🌐 Sanal Evren Etkinliği", "Pazartesi"),
        # 22:30 Savaş Arenası → 22:20 duyuru
        (0, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Pazartesi"),
        # 23:15 Jotun Etkinliği → 23:05 duyuru
        (0, 23, 5, "❄️ Jotun Etkinliği", "Pazartesi"),
        # 01:00 (ertesi gün) Kayıp Alfabe → 00:50 duyuru
        (0, 0, 50, "📖 Kayıp Alfabe Etkinliği", "Pazartesi"),
        
        # ========== SALI ==========
        # 13:00 Yeşil Vadi → 12:50 duyuru
        (1, 12, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        # 14:00 Yeşil Vadi → 13:50 duyuru
        (1, 13, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        # 15:00 Kayıp Alfabe → 14:50 duyuru
        (1, 14, 50, "📖 Kayıp Alfabe Etkinliği", "Salı"),
        # 16:00 Sanal Evren → 15:50 duyuru
        (1, 15, 50, "🌐 Sanal Evren Etkinliği", "Salı"),
        # 19:00 Yeşil Vadi → 18:50 duyuru
        (1, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        # 20:00 Yeşil Vadi → 19:50 duyuru
        (1, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Salı"),
        # 21:00 Düello Turnuvası (Ninja) → 20:50 duyuru
        (1, 20, 50, "⚔️ Düello Turnuvası (Ninja)", "Salı"),
        # 22:00 Sanal Evren → 21:50 duyuru
        (1, 21, 50, "🌐 Sanal Evren Etkinliği", "Salı"),
        # 22:30 Savaş Arenası → 22:20 duyuru
        (1, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Salı"),
        # 23:15 Grup Düello Turnuvası → 23:05 duyuru
        (1, 23, 5, "⚔️ Grup Düello Turnuvası", "Salı"),
        
        # ========== ÇARŞAMBA ==========
        # 13:00 Kusursuz Cehennem → 12:50 duyuru
        (2, 12, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        # 14:00 Kusursuz Cehennem → 13:50 duyuru
        (2, 13, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        # 15:00 Sanal Evren → 14:50 duyuru
        (2, 14, 50, "🌐 Sanal Evren Etkinliği", "Çarşamba"),
        # 18:00 Kayıp Alfabe → 17:50 duyuru
        (2, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        # 19:00 Kayıp Alfabe → 18:50 duyuru
        (2, 18, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        # 21:00 Düello Turnuvası (Sura) → 20:50 duyuru
        (2, 20, 50, "⚔️ Düello Turnuvası (Sura)", "Çarşamba"),
        # 21:40 Antik Ejderha Kutbu → 21:30 duyuru
        (2, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Çarşamba"),
        # 22:00 Kusursuz Cehennem → 21:50 duyuru
        (2, 21, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
        # 22:30 Üç İmparatorluk Savaşı → 22:20 duyuru
        (2, 22, 20, "👑 Üç İmparatorluk Savaşı Etkinliği", "Çarşamba"),
        # 01:00 (ertesi gün) Kayıp Alfabe → 00:50 duyuru
        (2, 0, 50, "📖 Kayıp Alfabe Etkinliği", "Çarşamba"),
        
        # ========== PERŞEMBE ==========
        # 14:00 Kayıp Alfabe → 13:50 duyuru
        (3, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Perşembe"),
        # 15:00 Yeşil Vadi → 14:50 duyuru
        (3, 14, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        # 16:00 Yeşil Vadi → 15:50 duyuru
        (3, 15, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        # 17:00 Sanal Evren → 16:50 duyuru
        (3, 16, 50, "🌐 Sanal Evren Etkinliği", "Perşembe"),
        # 18:00 Kayıp Alfabe → 17:50 duyuru
        (3, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Perşembe"),
        # 19:00 Yeşil Vadi → 18:50 duyuru
        (3, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        # 21:00 Düello Turnuvası (Şaman) → 20:50 duyuru
        (3, 20, 50, "⚔️ Düello Turnuvası (Şaman)", "Perşembe"),
        # 22:00 Yeşil Vadi → 21:50 duyuru
        (3, 21, 50, "🟢 Yeşil Vadi Etkinliği", "Perşembe"),
        # 22:30 Savaş Arenası → 22:20 duyuru
        (3, 22, 20, "🛡️ Savaş Arenası Etkinliği", "Perşembe"),
        
        # ========== CUMA ==========
        # 13:00 Kayıp Alfabe → 12:50 duyuru
        (4, 12, 50, "📖 Kayıp Alfabe Etkinliği", "Cuma"),
        # 14:00 Kusursuz Cehennem → 13:50 duyuru
        (4, 13, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        # 15:00 Kusursuz Cehennem & Sanal Evren → 14:50 duyuru
        (4, 14, 50, "🔥 Kusursuz Cehennem & 🌐 Sanal Evren Etkinliği", "Cuma"),
        # 19:00 Kusursuz Cehennem → 18:50 duyuru
        (4, 18, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        # 20:00 Düello Turnuvası (Genel) → 19:50 duyuru
        (4, 19, 50, "⚔️ Düello Turnuvası (Genel)", "Cuma"),
        # 21:00 Kusursuz Cehennem → 20:50 duyuru
        (4, 20, 50, "🔥 Kusursuz Cehennem", "Cuma"),
        # 21:40 Antik Ejderha Kutbu → 21:30 duyuru
        (4, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Cuma"),
        # 22:00 Savaş Arenası → 21:50 duyuru
        (4, 21, 50, "🛡️ Savaş Arenası Etkinliği", "Cuma"),
        # 22:20 Sanal Evren → 22:10 duyuru
        (4, 22, 10, "🌐 Sanal Evren Etkinliği", "Cuma"),
        # 23:15 Grup Düello Turnuvası → 23:05 duyuru
        (4, 23, 5, "⚔️ Grup Düello Turnuvası", "Cuma"),
        
        # ========== CUMARTESİ ==========
        # 13:00 Kayıp Alfabe → 12:50 duyuru
        (5, 12, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        # 14:00 Kayıp Alfabe → 13:50 duyuru
        (5, 13, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        # 15:00 Yeşil Vadi → 14:50 duyuru
        (5, 14, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        # 16:00 Yeşil Vadi → 15:50 duyuru
        (5, 15, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        # 17:00 Sanal Evren → 16:50 duyuru
        (5, 16, 50, "🌐 Sanal Evren Etkinliği", "Cumartesi"),
        # 18:00 Kayıp Alfabe → 17:50 duyuru
        (5, 17, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        # 19:00 Kayıp Alfabe → 18:50 duyuru
        (5, 18, 50, "📖 Kayıp Alfabe Etkinliği", "Cumartesi"),
        # 20:00 Yeşil Vadi → 19:50 duyuru
        (5, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        # 21:40 Antik Ejderha Kutbu → 21:30 duyuru
        (5, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Cumartesi"),
        # 22:00 Yeşil Vadi → 21:50 duyuru
        (5, 21, 50, "🟢 Yeşil Vadi Etkinliği", "Cumartesi"),
        # 22:30 Üç İmparatorluk Savaşı → 22:20 duyuru
        (5, 22, 20, "👑 Üç İmparatorluk Savaşı Etkinliği", "Cumartesi"),
        # 23:00 Sanal Evren → 22:50 duyuru
        (5, 22, 50, "🌐 Sanal Evren Etkinliği", "Cumartesi"),
        # 02:00 (ertesi gün) Kusursuz Cehennem → 01:50 duyuru
        (5, 1, 50, "🔥 Kusursuz Cehennem", "Cumartesi"),
        
        # ========== PAZAR ==========
        # 13:00 Yeşil Vadi → 12:50 duyuru
        (6, 12, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        # 14:00 Yeşil Vadi → 13:50 duyuru
        (6, 13, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        # 15:00 Kayıp Alfabe → 14:50 duyuru
        (6, 14, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        # 16:00 Kayıp Alfabe → 15:50 duyuru
        (6, 15, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        # 17:00 Sanal Evren → 16:50 duyuru
        (6, 16, 50, "🌐 Sanal Evren Etkinliği", "Pazar"),
        # 18:00 Sanal Evren → 17:50 duyuru
        (6, 17, 50, "🌐 Sanal Evren Etkinliği", "Pazar"),
        # 19:00 Yeşil Vadi → 18:50 duyuru
        (6, 18, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        # 20:00 Yeşil Vadi → 19:50 duyuru
        (6, 19, 50, "🟢 Yeşil Vadi Etkinliği", "Pazar"),
        # 21:00 Kayıp Alfabe → 20:50 duyuru
        (6, 20, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        # 21:40 Antik Ejderha Kutbu → 21:30 duyuru
        (6, 21, 30, "🐉 Antik Ejderha Kutbu Etkinliği", "Pazar"),
        # 22:00 Kayıp Alfabe → 21:50 duyuru
        (6, 21, 50, "📖 Kayıp Alfabe Etkinliği", "Pazar"),
        # 22:30 Savaş Arenası → 22:20 duyuru
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
