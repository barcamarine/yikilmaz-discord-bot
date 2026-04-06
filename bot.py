import discord
import random
from discord.ext import commands, tasks
import os
from openai import AsyncOpenAI
import aiosqlite
import pytz
from datetime import datetime, time
from dotenv import load_dotenv

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ZARVS_LAFLAR = [
    "💀 ağzına sıçıldı",
    "😂 bu kadar kötü zar mı atılır kolsuz",
    "👀 biraz daha çalışman lazım",
    "🔥 bir dahaki sefere belki",
    "😏 çok basitsin be olum",
    "⚰️ yallah mezara",
    "🤡 patatez oldun",
    "💀 cenaze namazını kılıyoruz",
    "🚪 al kendini git burdan",
    "🦁 aslanparçası kaybol",
    "⌛ söz vermedik ama elbet bir gün",
    "🤨 kudurdun mu sen?",
    "🗑️ çöp poşeti",
    "🦾 sana n11.com'dan kol alalım", 
]

ZAR_GIF = "https://www.hareketligifler.net/data/media/710/zar-hareketli-resim-0016.gif"

# Türkiye saat dilimi
TR_TZ = pytz.timezone('Europe/Istanbul')

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
ZARVS_CHANNEL_ID = 1490414678118105119

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

    # eski eventleri temizle
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM weekly WHERE is_system = 1")
        await db.commit()

    # 🔥 EVENTLERİ YÜKLE (EN ÖNEMLİ)
    await load_system_events()

    # 🔄 DUYURU LOOP BAŞLAT
    if not check_all_announcements.is_running():
        check_all_announcements.start()

    await bot.tree.sync()

    print(f'✅ {bot.user} aktif!')

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
    # ================= PAZARTESİ =================
    (0, 00, 50, "📖 Kayıp Alfabe", "Pazartesi"),
    (0, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ**  :pray: :heart:", "Pazartesi"),
    (0, 13, 50, "📖 Kayıp Alfabe", "Pazartesi"),
    (0, 14, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
    (0, 18, 50, "🔥 Kusursuz Cehennem", "Pazartesi"),
    (0, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Pazartesi"),
    (0, 20, 50, "⚔️ Düello Turnuvası (Savaşçı)", "Pazartesi"),
    (0, 21, 30, "🐉 Antik Ejderha Kutbu", "Pazartesi"),
    (0, 22, 20, "🛡️ Savaş Arenası", "Pazartesi"),

    # ================= SALI =================
    (1, 12, 50, "🟢 Yeşil Vadi", "Salı"),
    (1, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Salı"),
    (1, 14, 50, "📖 Kayıp Alfabe", "Salı"),
    (1, 18, 50, "🟢 Yeşil Vadi", "Salı"),
    (1, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Salı"),
    (1, 20, 50, "⚔️ Düello Turnuvası (Ninja) - Kayıp Alfabe Etkinliği", "Salı"),
    (1, 22, 20, "🛡️ Savaş Arenası", "Salı"),
    (1, 23, 5, "⚔️ 8v8 Lonca Savaşı", "Salı"),

    # ================= ÇARŞAMBA =================
    (2, 12, 50, "🔥 Kusursuz Cehennem", "Çarşamba"),
    (2, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Çarşamba"),
    (2, 18, 50, "📖 Kayıp Alfabe", "Çarşamba"),
    (2, 19, 51, "🔥 *DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Çarşamba"),
    (2, 20, 50, "⚔️ Düello Turnuvası (Sura) - Kusursuz Cehennem", "Çarşamba"),
    (2, 21, 30, "🐉 Antik Ejderha Kutbu", "Çarşamba"),
    (2, 22, 20, "👑 Üç İmparatorluk Savaşı", "Çarşamba"),

    # ================= PERŞEMBE =================
    (3, 00, 50, "📖 Kayıp Alfabe", "Perşembe"),
    (3, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Perşembe"),
    (3, 12, 50, "📖 Kayıp Alfabe", "Perşembe"),
    (3, 13, 50, "🟢 Yeşil Vadi", "Perşembe"),
    (3, 18, 50, "📖 Kayıp Alfabe", "Perşembe"),
    (3, 19, 50, "🟢 Yeşil Vadi", "Perşembe"),
    (3, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Perşembe"),
    (3, 20, 50, "⚔️ Düello Turnuvası (Şaman)", "Perşembe"),
    (3, 22, 20, "🛡️ Savaş Arenası", "Perşembe"),

    # ================= CUMA =================
    (4, 00, 50, "📖 Kayıp Alfabe", "Cuma"),
    (4, 14, 50, "🔥 Kusursuz Cehennem", "Cuma"),
    (4, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Cuma"),
    (4, 19, 50, "🔥 Kusursuz Cehennem", "Cuma"),
    (4, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Cuma"),
    (4, 20, 50, "⚔️ Düello Turnuvası (Genel)", "Cuma"),
    (4, 21, 30, "🐉 Antik Ejderha Kutbu", "Cuma"),
    (4, 22, 20, "🛡️ Savaş Arenası", "Cuma"),
    (4, 23, 5, "⚔️ 8v8 Lonca Savaşı", "Cuma"),

    # ================= CUMARTESİ =================
    (5, 00, 50, "🔥 Kusursuz Cehennem", "Cumartesi"),
    (5, 12, 50, "📖 Kayıp Alfabe", "Cumartesi"),
    (5, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Cumartesi"),
    (5, 14, 50, "🟢 Yeşil Vadi", "Cumartesi"),
    (5, 18, 50, "📖 Kayıp Alfabe", "Cumartesi"),
    (5, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Cumartesi"),
    (5, 20, 50, "🟢 Yeşil Vadi", "Cumartesi"),
    (5, 21, 30, "🐉 Antik Ejderha Kutbu", "Cumartesi"),
    (5, 22, 20, "👑 Üç İmparatorluk Savaşı", "Cumartesi"),

    # ================= PAZAR =================
    (6, 12, 50, "🟢 Yeşil Vadi", "Pazar"),
    (6, 12, 51, "📖 **UYANAN EVDE OLAN BİLGİSAYAR BAŞINDA OYUNDA  OLAN MÜSAİT DURUMDA OLAN HERKESİ <#1175190408846913597> 'NA BEKLİYORUZ** :pray: :heart:", "Pazar"),
    (6, 14, 50, "📖 Kayıp Alfabe", "Pazar"),
    (6, 18, 50, "🟢 Yeşil Vadi", "Pazar"),
    (6, 19, 50, "🟢 Yeşil Vadi", "Pazar"),
    (6, 19, 51, "🔥 **DEĞERLİ ABİLERİM KARDEŞLERİM İŞTEN GELEN OKULDAN GELEN MÜSAİT DURUMA GEÇEN *HERKESİ BİRLİKTELİĞİMİZİN DEVAMI İÇİN 20:00 İLE 00:00 ARASI LÜTFEN DİSCORDA GELMEYE ÖZEN GÖSTERELİM**", "Pazar"),
    (6, 20, 50, "📖 Kayıp Alfabe", "Pazar"),
    (6, 21, 30, "🐉 Antik Ejderha Kutbu", "Pazar"),
    (6, 22, 20, "🛡️ Savaş Arenası", "Pazar"),
]
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT COUNT(*) FROM weekly WHERE is_system = 1')
        count = await cursor.fetchone()
        
        if count[0] == 0:
            for day, hour, minute, msg, day_name in events:
                if "UYANAN EVDE OLAN" in msg or "DEĞERLİ ABİLERİM KARDEŞLERİM" in msg:
                    full_msg = f"@everyone {msg}"
                else:
                    full_msg = f"||@everyone|| 📢 10 dk sonra {msg} başlıyor!"
                    
                await db.execute('''
                    INSERT INTO weekly (day, day_name, channel_id, message, hour, minute, is_system, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, 1, 'System')
                ''', (day, day_name, EVENT_CHANNEL_ID, full_msg, hour, minute))
            await db.commit()
            print(f'✅ {len(events)} sistem etkinliği yüklendi!')

# ==================== KOMUTLAR ====================

@bot.command()
async def sor(ctx, *, soru):
    msg = await ctx.send("🔍 Araştırıyorum...")

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Kısa ve net cevap ver, Türkçe konuş."},
                {"role": "user", "content": soru}
            ]
        )

        cevap = response.choices[0].message.content

        await msg.edit(
            content=f"🧠 {ctx.author.mention} sordu:\n**{soru}**\n\n📌 Cevap:\n{cevap}"
        )

    except Exception as e:
        await msg.edit(content=f"❌ Hata: {e}")

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
    embed.add_field(name='📅 Haftalık', value='`!haftalik_duyuru Gün SAAT:DAKİKA #kanal mesaj`\\n`!haftalik_liste` | `!haftalik_sil ID`', inline=False)
    embed.add_field(name='🔄 Günlük', value='`!gunluk_duyuru SAAT:DAKİKA #kanal mesaj`\\n`!gunluk_liste` | `!gunluk_sil ID`', inline=False)
    embed.add_field(name='📆 Tarihli', value='`!tarihli_duyuru GÜN.AY.YIL SAAT:DAKİKA #kanal mesaj`\\n`!tarihli_liste` | `!tarihli_sil ID`', inline=False)
    embed.add_field(name='📢 Anlık', value='`!duyuru #kanal mesaj`', inline=False)
    await ctx.send(embed=embed)

@bot.tree.command(name="ping", description="Bot aktif mi kontrol et")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"{interaction.user.mention} 7/24 nöbetteyim komutanım! 🫡")

@bot.command()
@commands.has_permissions(administrator=True)
async def sil(ctx, miktar: int):
    if miktar < 1:
        return await ctx.send("❌ Geçerli sayı gir!")

    try:
        silinen = await ctx.channel.purge(limit=miktar + 1)
        sonuc = await ctx.send(f"🧹 {ctx.author.mention} {len(silinen)-1} mesaj silindi.")
        
        import asyncio
        await asyncio.sleep(5)
        await sonuc.delete()

    except Exception as e:
        await ctx.send(f"❌ Hata: {e}")

@bot.command()
async def zarvs(ctx, uye: discord.Member):
    if uye.bot:
        return await ctx.send("🤖 Botlarla oynayamazsın!")

    if uye == ctx.author:
        return await ctx.send("😅 Kendinle oynayamazsın!")

    import random
    import asyncio

    # 🎬 GIF ile başlangıç
    embed = discord.Embed(title="🎲 Zar atılıyor...")
    embed.set_image(url=ZAR_GIF)

    msg = await ctx.send(embed=embed)

    await asyncio.sleep(4)

    # 🎲 zarlar
    sen = random.randint(1, 6)
    rakip = random.randint(1, 6)

    sonuc = f"🎲 {ctx.author.mention} vs {uye.mention}\n\n"
    sonuc += f"{ctx.author.mention} → 🎲 {sen}\n"
    sonuc += f"{uye.mention} → 🎲 {rakip}\n\n"

    if sen > rakip:
        kazanan = ctx.author
        kaybeden = uye
    elif rakip > sen:
        kazanan = uye
        kaybeden = ctx.author
    else:
        return await msg.edit(content=sonuc + "🤝 Berabere! Tekrar deneyin.")

    laf = random.choice(ZARVS_LAFLAR)

    sonuc += f"🏆 Kazanan: {kazanan.mention}\n"
    sonuc += f"💀 Kaybeden: {kaybeden.mention}\n\n"
    sonuc += f"{kaybeden.mention} {laf}"

    embed = discord.Embed(description=sonuc)
    await msg.edit(embed=embed)

# ==================== KONTROL SİSTEMİ ====================

@tasks.loop(minutes=1)
async def check_all_announcements():
    now = datetime.now(TR_TZ)
    current_time = time(now.hour, now.minute)
    current_weekday = now.weekday()
    today_str = now.strftime('%Y-%m-%d')

    async with aiosqlite.connect(DB_PATH) as db:

        # Günlük
        cursor = await db.execute(
            'SELECT channel_id, message FROM daily WHERE hour = ? AND minute = ?',
            (current_time.hour, current_time.minute)
        )
        for row in await cursor.fetchall():
            await send_msg(row[0], row[1])

        # Haftalık
        cursor = await db.execute(
            'SELECT channel_id, message FROM weekly WHERE day = ? AND hour = ? AND minute = ?',
            (current_weekday, current_time.hour, current_time.minute)
        )
        for row in await cursor.fetchall():
            await send_msg(row[0], row[1])

        # Tarihli
        cursor = await db.execute(
            'SELECT id, channel_id, message FROM scheduled WHERE date = ? AND hour = ? AND minute = ? AND sent = 0',
            (today_str, current_time.hour, current_time.minute)
        )
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

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == ZARVS_CHANNEL_ID:

        # sadece !zarvs komutu izinli
        if not message.content.lower().startswith("!zarvs"):
            try:
                await message.delete()

                warn = await message.channel.send("❌ Bu kanalda sadece !zarvs komutu kullanılabilir!")

                import asyncio
                await asyncio.sleep(5)
                await warn.delete()

            except:
                pass
            return

    await bot.process_commands(message)

TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("DISCORD_TOKEN bulunamadı! Railway Variables'a ekleyin.")

bot.run(TOKEN)
