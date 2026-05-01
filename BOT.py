# refresh
import asyncio
import discord
import os
import string
from discord.ext import commands, tasks  # Tambah tasks
import random  # Untuk fitur tambahan, jika diperlukan
import requests
from bs4 import BeautifulSoup
import json
import time
import datetime
import socket
from urllib.parse import urljoin
from discord import ui
import aiohttp
from aiohttp import web
from Brain import check_image, tanyakan_zenn, respons_scan, validate_image_with_gemini, tebak_unsur_dari_benda, fetch_wiki_data, ringkas_wikipedia_async
from dotenv import load_dotenv
from database import add_book, get_books, search_books, book_exists, get_random_book, save_conversation, get_conversation_history, clear_conversation, check_ai_limit, increment_ai_count, create_exclusive_event, check_event_status, claim_exclusive_event

# Load environment variables from .env file
load_dotenv()

WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://127.0.0.1:5000')

DEBUG_LOG_PATH = "debug-5bafde.log"
DEBUG_SESSION_ID = "5bafde"

def _debug_log(run_id, hypothesis_id, location, message, data=None):
    payload = {
        "sessionId": DEBUG_SESSION_ID,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

# Get admin Discord ID for AI limit bypass
ADMIN_DISCORD_ID = os.getenv('ADMIN_DISCORD_ID', '')

try:
    import certifi

    _HTTP_VERIFY = certifi.where()
except ImportError:
    _HTTP_VERIFY = True

def http_get(url, **kwargs):
    """GET dengan CA bundle certifi (membantu SSL di Windows); jangan blokir event loop dari coroutine."""
    if "verify" not in kwargs:
        kwargs["verify"] = _HTTP_VERIFY
    return requests.get(url, **kwargs)

# Konfigurasi intents
# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents, case_insensitive=True)

#fitur **BETA** WEB SCRAPING
def ambil_quotes_dari_web():
    url = "https://quotes.toscrape.com/"
    respon = http_get(url, timeout=20)
    soup = BeautifulSoup(respon.text, 'html.parser')
    
    daftar_kotak = soup.find_all('div', class_='quote')
    semua_data = [] # List untuk nampung hasil scrap
    
    for kotak in daftar_kotak:
        teks = kotak.find('span', class_='text').text
        penulis = kotak.find('small', class_='author').text
        semua_data.append(f"{teks} — *{penulis}*")
    
    return semua_data

def scrap_treehugger():
    # Target: Website Books to Scrape
    url = "https://books.toscrape.com/catalogue/category/books_1/index.html"
    
    try:
        respon = http_get(url, timeout=10)
        soup = BeautifulSoup(respon.text, 'html.parser')
        
        # Di website ini, judul buku ada di dalam tag <h3> lalu di dalam tag <a>
        # Kita ambil semua tag <h3>
        book_elements = soup.find_all('h3')
        
        print(f"--- DEBUG: Berhasil nemu {len(book_elements)} buku di web ---")
        
        daftar_hasil = []
        for book in book_elements:
            # Ambil teks dari tag <a> yang ada di dalam <h3>
            judul = book.find('a')['title'] 
            daftar_hasil.append(judul)
            
        return daftar_hasil
    except Exception as e:
        print(f"--- DEBUG ERROR: {e} ---")
        return []

def ambil_detail_buku_acak():
    url_utama = "https://books.toscrape.com/"
    
    try:
        # Gunakan requests langsung jika http_get adalah custom function kamu
        respon = requests.get(url_utama, timeout=10) 
        soup = BeautifulSoup(respon.text, 'html.parser')
        
        daftar_buku = soup.find_all('article', class_='product_pod')
        if not daftar_buku: return None
        
        buku_pilihan = random.choice(daftar_buku)
        link_relatif = buku_pilihan.h3.a['href']
        
        # LOGIKA LINK YANG AMAN:
        # Jika link_relatif mengandung 'catalogue/', kita gabung ke url_utama
        # Jika tidak, kita tambahkan 'catalogue/' di tengahnya
        if "catalogue/" in link_relatif:
            link_lengkap = url_utama + link_relatif
        else:
            link_lengkap = url_utama + "catalogue/" + link_relatif
        
        respon_detail = requests.get(link_lengkap, timeout=10)
        soup_detail = BeautifulSoup(respon_detail.text, 'html.parser')
        
        judul = soup_detail.find('h1').text.strip()
        harga = soup_detail.find('p', class_='price_color').text.strip()
        
        deskripsi_tag = soup_detail.find('div', id='product_description')
        deskripsi = deskripsi_tag.find_next('p').text.strip() if deskripsi_tag else "N/A"

        return {
            "judul": judul,
            "harga": harga,
            "deskripsi": deskripsi,
            "url": link_lengkap
        }
    except Exception as e:
        print(f"Error Detail Scraping: {e}")
        return None
    
def ambil_banyak_buku(jumlah=25, delay_per_buku=0.5):
    url_base = "https://books.toscrape.com/"
    url_catalogue = "https://books.toscrape.com/catalogue/"
    hasil_banyak = []
    max_pages = 50 
    pages_scraped = 0
    listing_url = url_base

    try:
        while len(hasil_banyak) < jumlah and pages_scraped < max_pages:
            pages_scraped += 1
            # Pakai requests langsung jika http_get tidak didefinisikan
            respon = requests.get(listing_url, timeout=15)
            if respon.status_code != 200:
                break
            
            soup = BeautifulSoup(respon.text, "html.parser")
            daftar_buku = soup.find_all("article", class_="product_pod")

            for b in daftar_buku:
                if len(hasil_banyak) >= jumlah:
                    break
                
                try:
                    link_relatif = b.h3.a["href"]
                    # Logika cerdas: gabungkan link relatif dengan benar
                    if "catalogue/" in link_relatif:
                        link_lengkap = url_base + link_relatif.replace("catalogue/", "catalogue/")
                    else:
                        link_lengkap = url_catalogue + link_relatif
                    
                    # Bersihkan double slash jika ada
                    link_lengkap = link_lengkap.replace("catalogue/catalogue/", "catalogue/")
                except:
                    continue

                res_detail = requests.get(link_lengkap, timeout=15)
                if res_detail.status_code != 200:
                    continue

                s_detail = BeautifulSoup(res_detail.text, "html.parser")
                h1 = s_detail.find("h1")
                if not h1: continue
                
                judul = h1.text.strip()
                price_el = s_detail.find("p", class_="price_color")
                harga = price_el.text.strip() if price_el else "N/A"
                desc_tag = s_detail.find("div", id="product_description")
                deskripsi = desc_tag.find_next("p").text.strip() if desc_tag and desc_tag.find_next("p") else "N/A"

                hasil_banyak.append({
                    "judul": judul,
                    "harga": harga,
                    "deskripsi": deskripsi,
                    "url": link_lengkap,
                })
                time.sleep(delay_per_buku)

            # Cari tombol "Next" untuk pindah halaman
            next_a = soup.select_one("ul.pager li.next a")
            if not next_a:
                break
            
            # Update URL untuk halaman berikutnya
            listing_url = urljoin(listing_url, next_a["href"])

        return hasil_banyak
    except Exception as e:
        print(f"Error scraping banyak: {e}")
        return hasil_banyak # Kembalikan apa yang sudah didapat sejauh ini

def scrape_buku_baru(jumlah=10):
    url_base = "https://books.toscrape.com/"
    url_catalogue = "https://books.toscrape.com/catalogue/"
    hasil_baru = []
    max_pages = 50  # Batas maksimal halaman untuk menghindari loop tak berujung
    pages_scraped = 0
    listing_url = url_base

    try:
        while len(hasil_baru) < jumlah and pages_scraped < max_pages:
            pages_scraped += 1
            respon = requests.get(listing_url, timeout=15)
            if respon.status_code != 200:
                break
            
            soup = BeautifulSoup(respon.text, "html.parser")
            daftar_buku = soup.find_all("article", class_="product_pod")

            for b in daftar_buku:
                if len(hasil_baru) >= jumlah:
                    break
                
                try:
                    link_relatif = b.h3.a["href"]
                    # Logika cerdas: gabungkan link relatif dengan benar
                    if "catalogue/" in link_relatif:
                        link_lengkap = url_base + link_relatif.replace("catalogue/", "catalogue/")
                    else:
                        link_lengkap = url_catalogue + link_relatif
                    
                    # Bersihkan double slash jika ada
                    link_lengkap = link_lengkap.replace("catalogue/catalogue/", "catalogue/")
                except:
                    continue

                # Scrape detail untuk mendapatkan judul lengkap
                res_detail = requests.get(link_lengkap, timeout=15)
                if res_detail.status_code != 200:
                    continue

                s_detail = BeautifulSoup(res_detail.text, "html.parser")
                h1 = s_detail.find("h1")
                if not h1: continue
                
                judul = h1.text.strip()
                
                # Cek apakah judul sudah ada di database SQLite
                if book_exists(judul):
                    continue  # Skip buku yang sudah ada
                
                # Jika belum ada, scrape detail lengkap
                price_el = s_detail.find("p", class_="price_color")
                harga = price_el.text.strip() if price_el else "N/A"
                desc_tag = s_detail.find("div", id="product_description")
                deskripsi = desc_tag.find_next("p").text.strip() if desc_tag and desc_tag.find_next("p") else "N/A"

                buku_baru = {
                    "judul": judul,
                    "harga": harga,
                    "deskripsi": deskripsi,
                    "url": link_lengkap,
                }
                hasil_baru.append(buku_baru)
                time.sleep(0.5)  # Delay antar buku

            # Cari tombol "Next" untuk pindah halaman
            next_a = soup.select_one("ul.pager li.next a")
            if not next_a:
                break
            
            # Update URL untuk halaman berikutnya
            listing_url = urljoin(listing_url, next_a["href"])

        return hasil_baru
    except Exception as e:
        print(f"Error scraping buku baru: {e}")
        return hasil_baru

# Data
emoji_list = ["😀", "😂", "🤣", "😍", "🥰", "😎", "🤔", "😴", "🤖", "👻", "🦄", "🌟", "🔥", "🎉", "🍕", "☕", "🏆", "🎮", "🚀"]

kategori_sampah = {
    "organik": ["sisa makanan", "daun", "kulit buah", "nasi basi", "ampas kopi", "tulang ayam"],
    "anorganik": ["plastik", "kaca", "kaleng", "botol", "kertas", "besi berkarat"],
    "berbahaya": ["baterai", "lampu neon", "obat kadaluarsa", "cat bekas", "pecahan kaca"]
}

aksi_sah = [
    "Menanam pohon", "Membersihkan taman", "Buang sampah", "Matikan lampu", 
    "Hemat listrik", "Hemat air", "Daur ulang", "Transportasi umum", 
    "Kurangi plastik", "Membuat kompos", "Minyak jelantah", "Bawa tas belanja",
    "Botol minum ulang", "Sedotan stainless", "Cabut charger", "Energi terbarukan", 
    "Kipas angin", "Lampu LED", "Tidak bakar sampah", "Tanaman obat", 
    "Sabun ramah lingkungan", "Shampo bar", "Eco-brick", "Pakaian bekas",
    "Sumbang baju", "Jalan kaki", "Tisu daur ulang", "Produk lokal", 
    "Makanan organik", "Air hujan", "Bersih pantai", "Kurangi daging",
    "Detergen ramah lingkungan", "Tanpa kemasan", "Alat cukur ulang", 
    "Perbaiki barang", "Tanam sayur", "Air bekas cucian", "Hemat kertas", 
    "E-book", "Kertas dua sisi", "Tanpa pestisida", "Pilah sampah", 
    "Ulang kantong plastik", "Kompor hemat energi", "Cat air", "Beli second",
    "Bersihkan rumah", "Menyapu", "4 Sehat 5 sempurna", "Matikan AC", 
    "Matikan TV", "Cabut kabel", "Bawa tumbler", "Pakai sepeda", 
    "Naik bus", "Naik kereta", "Tanam bunga", "Siram tanaman", 
    "Pupuk tanaman", "Bikin pupuk", "Jual rongsokan", "Cuci piring", 
    "Sapu lantai", "Pel lantai", "Lap meja", "Buka jendela", 
    "Matikan keran", "Makan sayur", "Makan buah", "Habiskan makanan", 
    "Bawa bekal", "Tanpa sedotan", "Hemat bensin", "Rawat barang", 
    "Cek kebocoran", "Ganti LED", "Cetak bolak balik", "Edukasi teman", 
    "Ajak keluarga", "Posting lingkungan", "Donasi bibit", "Ikut komunitas", 
    "Pungut sampah", "Gunakan pupuk", "Lestarikan alam", "Hemat energi", "Matikan mesin",
    "Membersihkan rumah", "4 sehat 5 sempurna", "Hemat energi"
]


green_tips = [
    "Matikan lampu jika tidak digunakan 💡",
    "Bawa botol minum sendiri untuk mengurangi plastik 🍼",
    "Gunakan transportasi umum atau bersepeda 🚴",
    "Kurangi makan daging untuk menghemat emisi karbon 🥦",
    "Tanam pohon atau rawat tanaman di rumah 🌳",
    "Transisi energi fosil ke energi terbarukan agar menghindari polusi 🌻"
]

LEVEL_BADGES = {
    1: "🌱 Newbie",
    5: "🍃 Fresh Starter",
    10: "🌿 Green Explorer",
    20: "🌼 Nature Supporter",
    30: "🌲 Eco Enthusiast",
    40: "🌾 Sustainable Seeker",
    50: "🌍 Environmental Hero",
    60: "🔥 Climate Advocate",
    70: "⚡ Eco Warrior",
    80: "🌀 Planet Protector",
    90: "💎 Earth Guardian",
    100: "🏆 Legendary Green Champion"
}

USER_LAST_ACTION = {}
LAST_SEARCH_TIME = {}  # Untuk menyimpan waktu terakhir user melakukan $Cari

POIN_FILE = "poin_hijau.json"
STORY_LOG_FILE = "story_log.json"
EVENT_FILE = "event_eksklusif.json"
TIPS_LOG_FILE = "tips_daily_log.json"
CACHE_FILE = "database_buku_log.json"

def muat_tips_log():
    if os.path.exists(TIPS_LOG_FILE):
        with open(TIPS_LOG_FILE, "r") as f:
            return json.load(f)
    return {}

def simpan_tips_log(data):
    with open(TIPS_LOG_FILE, "w") as f:
        json.dump(data, f)

def muat_event():
    if os.path.exists(EVENT_FILE):
        with open(EVENT_FILE, "r") as f:
            return json.load(f)
    return {"aksi_event": "", "sudah_klaim": []}

def simpan_event(data):
    with open(EVENT_FILE, "w") as f:
        json.dump(data, f)

def muat_story_log():
    if os.path.exists(STORY_LOG_FILE):
        with open(STORY_LOG_FILE, "r") as f:
            return json.load(f)
    return {}

def simpan_story_log(data):
    with open(STORY_LOG_FILE, "w") as f:
        json.dump(data, f)

def muat_poin():
    if os.path.exists(POIN_FILE):
        with open(POIN_FILE, "r") as f:
            return json.load(f)
    return {}

def simpan_poin(data):
    with open(POIN_FILE, "w") as f:
        json.dump(data, f, indent=4)

def tambah_data(user_id, xp=1, gold=1):
    data = muat_poin()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"xp": 0, "gold": 0}
    
    # Tambahkan XP dan Gold
    data[uid]["xp"] += xp
    data[uid]["gold"] += gold
    simpan_poin(data)
    
    # Emit SocketIO event for real-time update
    try:
        import requests
        requests.post(f'{WEBSITE_URL}/emit_update', json={
            'type': 'points_update',
            'user_id': uid,
            'new_xp': data[uid]["xp"],
            'new_gold': data[uid]["gold"],
            'total_users': len(data)
        }, timeout=2)
    except Exception as e:
        print(f"Failed to emit SocketIO event: {e}")

def tambah_data_random(user_id, base_amount):
    """Tambah XP atau Gold secara random (50:50 chance)"""
    data = muat_poin()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"xp": 0, "gold": 0}
    
    # Random choice: 50% XP, 50% Gold
    is_xp = random.choice([True, False])
    if is_xp:
        data[uid]["xp"] += base_amount
        reward_type = "XP"
        reward_emoji = "⭐"
    else:
        data[uid]["gold"] += base_amount
        reward_type = "Gold"
        reward_emoji = "💰"
    
    simpan_poin(data)
    
    # Emit SocketIO event for real-time update
    try:
        import requests
        requests.post(f'{WEBSITE_URL}/emit_update', json={
            'type': 'points_update',
            'user_id': uid,
            'new_xp': data[uid]["xp"],
            'new_gold': data[uid]["gold"],
            'total_users': len(data)
        }, timeout=2)
    except Exception as e:
        print(f"Failed to emit SocketIO event: {e}")
    
    return reward_type, reward_emoji

def ambil_xp(user_id):
    data = muat_poin()
    return data.get(str(user_id), {"xp": 0})["xp"]

def ambil_gold(user_id):
    data = muat_poin()
    return data.get(str(user_id), {"gold": 0})["gold"]

def hitung_level(xp):
    return min(xp // 5 + 1, 100)  

def ambil_badge(xp):
    level = hitung_level(xp)
    badge = ""
    for batas, nama in sorted(LEVEL_BADGES.items()):
        if level >= batas:
            badge = nama
        else:
            break
    return badge

def kurangi_gold(user_id, jumlah):
    data = muat_poin()
    uid = str(user_id)
    if uid in data and data[uid]["gold"] >= jumlah:
        data[uid]["gold"] -= jumlah
        simpan_poin(data)
        
        # Emit SocketIO event for real-time update
        try:
            import requests
            requests.post(f'{WEBSITE_URL}/emit_update', json={
                'type': 'points_update',
                'user_id': uid,
                'new_xp': data[uid]["xp"],
                'new_gold': data[uid]["gold"],
                'total_users': len(data)
            }, timeout=2)
        except Exception as e:
            print(f"Failed to emit SocketIO event: {e}")
        return True
    return False

def has_item(user_id, item_name):
    """Check if user has a specific item in inventory"""
    from database import get_inventory
    items = get_inventory(user_id)
    return any(i['item_name'] == item_name for i in items)

# Scheduled Task untuk Auto-Scraping
@tasks.loop(hours=12)  # Jalankan setiap 12 jam
async def auto_scraping_buku():
    print("🔄 Memulai auto-scraping buku...")
    try:
        # Scrape hanya 10 buku baru yang belum ada di database
        buku_baru_list = await asyncio.to_thread(scrape_buku_baru, 10)
        
        if not buku_baru_list:
            print("ℹ️ Auto-scraping: Semua buku yang di-scrape sudah ada di database atau tidak ada data baru.")
            return

        # Simpan buku baru ke SQLite
        buku_ditambahkan = 0
        for buku in buku_baru_list:
            add_book(buku["judul"], buku["harga"], buku["deskripsi"], buku["url"])
            buku_ditambahkan += 1

        print(f"✅ Auto-scraping selesai: Ditambahkan {buku_ditambahkan} buku baru ke SQLite.")

        # --- DISINI TEMPAT LAPORAN KE DISCORD ---
        # Ganti angka di bawah dengan ID Channel Discord kamu (tanpa tanda kutip)
        ID_CHANNEL_LOG = 123456789012345678 
        channel = bot.get_channel(ID_CHANNEL_LOG)
        
        if channel:
            await channel.send(
                f"🤖 **Laporan Auto-Scraping**\n"
                f"✅ Berhasil menambahkan: **{buku_ditambahkan}** buku baru (hanya data unik).\n"
                f"📚 Total koleksi di database: **{buku_ditambahkan}** buku."
            )
        # ---------------------------------------
        
    except Exception as e:
        print(f"❌ Error auto-scraping: {e}")
        
# Bot Event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    # Mulai task auto-scraping saat bot ready
    if not auto_scraping_buku.is_running():
        auto_scraping_buku.start()
    
    # Start local API server
    asyncio.create_task(start_api_server())

async def start_api_server():
    async def send_message_handler(request):
        try:
            data = await request.json()
            channel_id = data.get('channel_id')
            message = data.get('message')
            
            if not channel_id or not message:
                return web.json_response({'error': 'Missing channel_id or message'}, status=400)
            
            channel = bot.get_channel(int(channel_id))
            if not channel:
                return web.json_response({'error': 'Channel not found'}, status=404)
            
            await channel.send(message)
            return web.json_response({'status': 'Message sent successfully'})
        except Exception as e:
            print(f"Error sending message: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def trigger_scraping_handler(request):
        try:
            data = await request.json()
            jumlah = data.get('jumlah', 10)
            
            if jumlah < 1 or jumlah > 100:
                return web.json_response({'error': 'Jumlah harus antara 1-100'}, status=400)
            
            # Jalankan scraping di background dengan cek duplikat
            buku_baru_list = await asyncio.to_thread(scrape_buku_baru, jumlah)
            
            if not buku_baru_list:
                return web.json_response({'error': 'Gagal scraping'}, status=500)
            
            # Simpan buku baru ke SQLite
            buku_ditambahkan = 0
            for buku in buku_baru_list:
                add_book(buku["judul"], buku["harga"], buku["deskripsi"], buku["url"])
                buku_ditambahkan += 1
            
            return web.json_response({'status': f'Berhasil tambah {buku_ditambahkan} buku ke SQLite'})
        except Exception as e:
            print(f"Error triggering scraping: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def trigger_event_handler(request):
        try:
            aksi = random.choice(aksi_sah)
            event_data = {"aksi_event": aksi, "sudah_klaim": []}
            simpan_event(event_data)
            
            return web.json_response({'status': f'Event dibuat: {aksi}'})
        except Exception as e:
            print(f"Error triggering event: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    app = web.Application()
    app.router.add_post('/send_message', send_message_handler)
    app.router.add_post('/trigger_scraping', trigger_scraping_handler)
    app.router.add_post('/trigger_event', trigger_event_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    await site.start()
    print("Local API server started on http://localhost:8080")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Parameter kurang: {error}")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(f"⚠️ Tipe parameter salah: {error}")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Kamu tidak punya izin untuk menjalankan perintah ini.")
        return
    if isinstance(error, commands.NotOwner):
        await ctx.send("⛔ Perintah ini khusus untuk pemilik bot.")
        return

    # Log error ke console supaya bisa dilihat di terminal
    print(f"[ERROR] Command '{ctx.command}' gagal: {error}")
    await ctx.send(f"❌ Terjadi kesalahan saat mengeksekusi perintah: {error}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # Kurangi probabilitas dan tambah kondisi agar tidak bentrok dengan command lain
    if random.random() < 0.005 and len(message.content) > 20:  # 0.5% kemungkinan, hanya untuk pesan panjang
        reminder = random.choice(green_tips)
        await message.channel.send(f"🌍 {reminder}")
    await bot.process_commands(message)

# Commands
@bot.command()
async def Start(ctx):
    await ctx.send(
"""📌 **Daftar Perintah Bot** 📌
Bot ini memiliki berbagai perintah seru yang bisa kamu coba! Berikut adalah daftar perintah yang tersedia:

1. `$Halo` - Menyapa bot.
2. `$Goodbye` - Balasan emot 😊.
3. `$Apalah` - Mengulang "he" sesuai jumlah yang diberikan.
4. `$Passgen <jumlah>` - Membuat password acak dengan simbol.
5. `$Menambahkan <angka1> <angka2>` - Menjumlahkan dua angka.
6. `$Dadu` - Mengocok dadu 1-6 dan beri respons acak.
7. `$Ulang <jumlah> <kata>` - Mengulang kata beberapa kali.
8. `$Emoji` - Memberi emoji acak.
9. `$Koin` - Melempar koin (Kepala/Ekor).
10. `$Bebek` - Mengirimkan gambar bebek random 🦆.
11. `$Rubah` - Mengirimkan gambar rubah random 🦊.
12. `$Website` - Kunjungi website dashboard bot untuk info lebih lengkap.
13. `$FungsiHijau` - Menampilkan daftar perintah terkait fitur hijau.
14. `$FungsiScraping` - Menampilkan daftar perintah terkait fitur web scraping.
15. `$Zenn <pertanyaan>` - Tanya ke AI Zenn VII tentang lingkungan! AI akan mengingat percakapanmu.

� **Fitur Ekonomi & Shop:**
16. `$Shop` - Lihat daftar item keren yang bisa dibeli pakai poin!
17. `$Buy <id>` - Beli item impianmu dari toko.
18. `$Gacha` - Uji keberuntunganmu dapatkan badge langka (15 Poin).
19. `$Inventory` - Cek barang-barang koleksi dan booster kamu.
20. `$Has_Item <nama_item>` - Cek apakah kamu punya item tertentu.

📝 Catatan:
- Untuk `$Ulang`, contoh: `$Ulang 3 Halo` → Maka akan mengulang "Halo" sebanyak 3 kali.
- Untuk `$Zenn`, contoh: `$Zenn apa itu global warming?` → AI akan menjawab dengan gaya santai dan edukatif.
- Untuk `$Explore`, contoh: `$Explore global warming` → Akan mencari di Wikipedia dan meringkas dengan AI.
- Untuk `$Has_Item`, contoh: `$Has_Item badge` → Cek apakah kamu punya item "badge".
- Untuk `$Inventory`, contoh: `$Inventory` → Cek barang-barang koleksi dan booster kamu.
- Untuk `$Buy`, contoh: `$Buy 1` → Beli item dengan ID 1.
- Untuk `$Gacha`, contoh: `$Gacha` → Uji keberuntunganmu dapatkan badge langka (15 Poin)..
"""
)

@bot.command()
async def FungsiHijau(ctx):
    await ctx.send(
"""📌 **Daftar Perintah Bot** 📌

♻️ **Fitur Aksi Hijau:**
1. `$Green_Action` - Menampilkan daftar Rekomendasi aksi ramah lingkungan.
2. `$Action <nama aktivitas>` - Melakukan aksi ramah lingkungan (misal: menanam pohon) dan dapat poin hijau. (Hanya aksi yang terdaftar akan diterima!)
3. `$Points` - Melihat jumlah poin hijau kamu.
4. `$Leaderboard` - Melihat pengguna dengan poin tertinggi dalam aksi hijau.
5. `$Add_Action <nama aksi>` - Mengusulkan aksi hijau baru ke daftar aksi yang sah.
6. `$Event` - Menambah event eksklusif.
7. `$Claim <cerita>` - Membuat Aktivitas sesuai yang berada dalam event(HANYA 1 ORANG PERTAMA YANG BISA KLAIM!).
8. `$Levelbadge` - Menampilkan List badge yang bisa didapat di permainan.
9. `$Story <cerita>` - Storytelling tentang aktivitas menghijaukan lingkungan yang kamu lakukan.
10. `$Pilah <nama_sampah>` - Mengetahui kategori sampah (organik/anorganik/berbahaya).
11. `$Kategori` - Melihat isi kategori sampah.
12. `$Tambah_Kategori <kategori> <nama_sampah>` - Menambahkan sampah baru ke kategori.
13. `$Hijau` - Menjelaskan apa itu fitur aksi hijau dan bagaimana cara kerjanya di bot.
14. `$Scan` - Menganalisis gambar sampah dan memberikan rekomendasi kategori.
15. `$Exclusive_Event <nama_event>` - Menambahkan event eksklusif (ADMIN ONLY).
16. `$Unsur <nama_benda>` - Mengetahui unsur-unsur yang terkandung dalam benda.

📝 Catatan:
- Untuk `$Tambah_Kategori`, contoh: `$Tambah_Kategori organik pisang` → Menambahkan "pisang" ke kategori "organik".
- Untuk `$Claim`, contoh: `$Claim hari ini saya menanam pohon di halaman rumah` → Cerita harus minimal 20 kata dan sesuai aksi event.
- Untuk `$Scan`, upload gambar sampah lalu ketik `$Scan` → AI akan menganalisis dan memberikan kategori.
- Untuk `$Exclusive_Event`, contoh: `$Exclusive_Event Hari Lingkungan Sedunia` → Hanya admin yang bisa menambahkan event.
- Untuk `$Unsur`, contoh: `$Unsur plastik` → Akan menampilkan unsur-unsur yang terkandung dalam plastik.
"""
)

@bot.command()
async def FungsiScraping(ctx):
    await ctx.send(
"""📌 **Daftar Perintah Bot** 📌

🕸️ **Fitur Web Scraping:**
1. `$Quotes` - Mengambil dan menampilkan kata-kata mutiara dari website.
2. `$Books` - Mencari rekomendasi buku dari website Books to Scrape (dengan cooldown 30 menit).
3. `$BookDescription` - Buku acak **cepat** dari database SQLite dengan deskripsi lengkap.
4. `$FindBooks <keyword>` - Cari buku dari database lokal berdasarkan keyword (judul/deskripsi).
5. `$WebScraping` - Menjelaskan apa itu web scraping dan bagaimana fitur ini bekerja di bot.
6. `$Explore <topik>` - Jelajahi topik dari Wikipedia dengan ringkasan AI.

📝 Catatan:
- Untuk `$FindBooks`, contoh: `$FindBooks python` → Akan menampilkan daftar buku yang mengandung kata "python".
- Untuk `$Explore`, contoh: `$Explore global warming` → Akan mencari di Wikipedia dan meringkas dengan AI.
"""
)

@bot.command()
async def Halo(ctx):
    await ctx.send(f'Hi! Aku bot dari ciptaan kak Raffasya yaituu: {bot.user}!')

@bot.command()
async def Yoga(ctx):
    await ctx.send(f'Woi lu goblok atau gimana sih? haha tolol lu')

@bot.command()
async def Goodbye(ctx):
    await ctx.send("\U0001f642")

@bot.command()
async def Apalah(ctx, count_heh: int = 5):
    await ctx.send("he" * count_heh)

@bot.command()
async def Passgen(ctx, jumlah: int = 12):
    if jumlah < 4 or jumlah > 64:
        await ctx.send("⚠️ Panjang password harus antara **4** dan **64**.")
        return
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    sandi = "".join(random.choice(chars) for _ in range(jumlah))
    await ctx.send(f"🔐 Password acak ({jumlah} karakter):\n`{sandi}`")

@bot.command()
async def Menambahkan(ctx, left: int, right: int):
    await ctx.send(left + right)

@bot.command()
async def Dadu(ctx):
    d = random.randint(1, 6)
    if d >= 4:
        await ctx.send(f"Kamu beruntung SEKALI mendapatkan angka dadu: {d}")
    else:
        await ctx.send(f"Kamu KURANG beruntung mendapatkan angka dadu: {d}")

@bot.command()
async def Ulang(ctx, times: int, content: str = "Mengulang...."):
    for _ in range(times):
        await ctx.send(content)

@bot.command()
async def Emoji(ctx):
    await ctx.send(f"Kamu mendapatkan emoji: {random.choice(emoji_list)}")

@bot.command()
async def Koin(ctx):
    await ctx.send(f"Hasil lemparan koin: ***{random.choice(['Kepala', 'Ekor'])}***")

def get_duck_image_url():
    res = http_get("https://random-d.uk/api/random", timeout=15)
    return res.json()["url"]

@bot.command(name='Bebek')
async def Bebek(ctx):
    url = await asyncio.to_thread(get_duck_image_url)
    await ctx.send(url)

def get_fox_image():
    res = http_get("https://randomfox.ca/floof", timeout=15)
    return res.json()["image"]

@bot.command(name='Rubah')
async def Rubah(ctx):
    url = await asyncio.to_thread(get_fox_image)
    await ctx.send(url)

@bot.command()
async def Website(ctx):
    await ctx.send(f"🌐 Kunjungi website dashboard bot kami untuk info lebih lengkap dan interaktif!\nLink: {WEBSITE_URL}/\n\nDi sana kamu bisa lihat leaderboard, koleksi buku, dan statistik bot. 🚀")

@bot.command()
async def Unsur(ctx, *, nama_benda: str):
    """Analisis unsur kimia dari sebuah benda dan berikan link ke tabel periodik"""
    await ctx.send(f"🔬 **Menganalisis {nama_benda}...**")
    
    # Use AI to guess elements
    elements = await tebak_unsur_dari_benda(nama_benda)
    
    if not elements:
        await ctx.send(f"⚠️ Maaf, tidak bisa menebak unsur dari '{nama_benda}'. Coba nama benda yang lebih spesifik.")
        return
    
    # Create URL with element parameters
    elements_param = ','.join(elements)
    website_url = f"{WEBSITE_URL}/chemical?highlight={elements_param}"
    
    # Format element symbols nicely
    elements_display = ', '.join([f"**{e}**" for e in elements])
    
    await ctx.send(
        f"🧪 **Analisis Unsur: {nama_benda}**\n"
        f"Unsur utama: {elements_display}\n\n"
        f"🔗 Lihat di tabel periodik (unsur akan bercahaya!):\n"
        f"{website_url}"
    )

@bot.command()
async def Explore(ctx, *, topik: str):
    """Jelajahi topik dari Wikipedia dengan ringkasan AI"""
    await ctx.send(f"🔍 **Mencari di Wikipedia: {topik}...**")
    
    # Fetch data from Wikipedia
    wiki_data = fetch_wiki_data(topik)
    
    if not wiki_data:
        await ctx.send(f"⚠️ Maaf, topik '{topik}' tidak ditemukan di Wikipedia Indonesia.")
        return
    
    # Summarize with Gemini
    if wiki_data.get("summary"):
        ringkasan = await ringkas_wikipedia_async(wiki_data["summary"])
    else:
        ringkasan = "Tidak ada ringkasan tersedia."
    
    # Build response
    response = f"📚 **{wiki_data.get('title', topik)}**\n\n"
    response += f"📝 {ringkasan}\n\n"
    
    if wiki_data.get("url"):
        response += f"🔗 Baca selengkapnya: {wiki_data['url']}"
    
    await ctx.send(response)

@bot.command()
async def Hijau(ctx):
    user_id = str(ctx.author.id)
    hari_ini = str(datetime.date.today()) 
    
    tips_log = muat_tips_log()
    
    # Ambil data user untuk hari ini, kalau belum ada set ke 0
    if hari_ini not in tips_log:
        tips_log[hari_ini] = {}
    
    jumlah_pakai = tips_log[hari_ini].get(user_id, 0)

    tip = random.choice(green_tips)

    if jumlah_pakai < 3: # Batas maksimal 3 kali sehari
        reward_type, reward_emoji = tambah_data_random(ctx.author.id, 1)
        tips_log[hari_ini][user_id] = jumlah_pakai + 1
        simpan_tips_log(tips_log)
        
        await ctx.send(
            f"🌱 **Tips Hijau Hari Ini:**\n{tip}\n\n"
            f"🎁 Kamu dapat **+1 {reward_type}!** {reward_emoji} (Jatah hari ini: {jumlah_pakai + 1}/3)"
        )
    else:
        # Tetap kasih tips, tapi poin tidak bertambah
        await ctx.send(
            f"🌱 **Tips Hijau Hari Ini:**\n{tip}\n\n"
            f"⚠️ Jatah poin harianmu sudah habis (3/3). Besok balik lagi ya untuk poin tambahan! 🌿"
        )

@bot.command()
async def Action(ctx, *, aktivitas: str):
    aktivitas = aktivitas.lower()
    user_id = str(ctx.author.id)
    waktu_sekarang = time.time()

    for aksi in aksi_sah:
        if aksi.lower() in aktivitas:
            terakhir = USER_LAST_ACTION.get(user_id)

            if terakhir and terakhir["aksi"] == aksi.lower():
                selisih = waktu_sekarang - terakhir["waktu"]
                if selisih < 3600:
                    sisa_menit = int((3600 - selisih) / 60) # Pakai int agar tidak ada .0
                    await ctx.send(
                        f"⏳ Kamu sudah melakukan aksi **{aksi}** sebelumnya.\n"
                        f"Tunggu **{sisa_menit} menit** sebelum mengulang aksi yang sama."
                    )
                    return

            reward_type, reward_emoji = tambah_data_random(ctx.author.id, 5)
            USER_LAST_ACTION[user_id] = {"aksi": aksi.lower(), "waktu": waktu_sekarang}
            await ctx.send(
                f"✅ Aksi tercatat: _{aktivitas}_\n"
                f"(Kecocokan: **{aksi}**)\n"
                f"Kamu mendapat **+5 {reward_type}!** {reward_emoji} 🌱"
            )
            return

    await ctx.send(f"⚠️ Maaf, aksi _{aktivitas}_ belum dikenali sebagai aksi hijau sah.")

@bot.command()
async def Points(ctx):
    user_id = str(ctx.author.id)
    xp = ambil_xp(user_id)
    gold = ambil_gold(user_id)
    level = hitung_level(xp)
    badge = ambil_badge(xp)
    
    embed = discord.Embed(title=f"📊 Statistik {ctx.author.display_name}", color=discord.Color.green())
    embed.add_field(name="🌟 Experience (XP)", value=f"**{xp} XP**", inline=True)
    embed.add_field(name="💰 Saldo Gold", value=f"**{gold} Gold**", inline=True)
    embed.add_field(name="📈 Level", value=f"**Level {level}**", inline=True)
    embed.add_field(name="🏅 Badge Rank", value=badge, inline=True)
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)


@bot.command()
async def Leaderboard(ctx):
    data = muat_poin()
    if not data:
        await ctx.send("Belum ada pahlawan lingkungan tercatat 🌱")
        return
        
    # Urutkan berdasarkan XP
    sorted_users = sorted(data.items(), key=lambda x: x[1]["xp"], reverse=True)[:5]
    
    pesan = "**� Top 5 Pahlawan Lingkungan (XP)**\n"
    for i, (uid, stats) in enumerate(sorted_users, 1):
        try:
            user = await bot.fetch_user(int(uid))
            name = user.name
        except:
            name = f"User {uid[-4:]}"
            
        level = hitung_level(stats["xp"])
        badge = ambil_badge(stats["xp"])
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        pesan += f"{medal} **{name}** - {stats['xp']} XP | Level {level} {badge}\n"
    
    await ctx.send(pesan)

@bot.command()
async def Add_Action(ctx, *, usulan: str):
    usulan = usulan.lower()
    if usulan in [a.lower() for a in aksi_sah]:
        await ctx.send("✅ Aksi itu sudah ada di daftar.")
    else:
        aksi_sah.append(usulan)
        await ctx.send(f"🌱 Aksi '{usulan}' telah ditambahkan ke daftar aksi hijau! Terima kasih!")

@bot.command()
async def Story(ctx, *, cerita: str):
    kata = cerita.split()
    if len(kata) < 30:
        await ctx.send(f"⚠️ Cerita kamu terlalu pendek! Harus minimal **30 kata**, baru bisa dicek.")
        return

    user_id = str(ctx.author.id)
    story_log = muat_story_log()

    # Cek apakah sudah pernah mengirim cerita yang sama
    if user_id in story_log and story_log[user_id] == cerita:
        await ctx.send("⚠️ Cerita yang sama sudah kamu kirim sebelumnya. Hindari spam untuk mendapatkan poin ya 🌱")
        return

    kata_unik = {k.lower() for k in kata}
    if len(kata_unik) < (len(kata) * 0.6):
        await ctx.send("⚠️ Ceritanya jangan cuma copy-paste atau mengulang kata yang sama terus ya! Ayo lebih kreatif.")
        return

    cerita_lower = cerita.lower()
    cocok_aksi = []
    for aksi in aksi_sah:
        if aksi.lower() in cerita_lower:
            cocok_aksi.append(aksi)

    if cocok_aksi:
        poin_didapat = 5 * len(cocok_aksi)
        reward_type, reward_emoji = tambah_data_random(ctx.author.id, poin_didapat)
        story_log[user_id] = cerita
        simpan_story_log(story_log)
        aksi_terdeteksi = "\n- " + "\n- ".join(cocok_aksi)
        await ctx.send(
            f"📘 Cerita kamu:\n_{cerita}_\n\n✅ Ditemukan **{len(cocok_aksi)} aksi hijau**:{aksi_terdeteksi}\n"
            f"🎉 Kamu mendapat **+{poin_didapat} {reward_type}!** {reward_emoji}"
        )
        return

    await ctx.send(
        f"📘 Cerita kamu:\n_{cerita}_\n\n❌ Belum ditemukan aksi hijau dari daftar yang sah.\n"
        f"Coba ceritakan aktivitas yang berkaitan dengan pelestarian lingkungan ya 🍀"
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def Event(ctx):
    aksi = random.choice(aksi_sah)
    event_data = {"aksi_event": aksi, "sudah_klaim": []}
    simpan_event(event_data)

    await ctx.send(
        f"🌿 **Event Eksklusif Telah Dimulai!** 🌿\n"
        f"Tugas eksklusif yang bisa dikerjakan: **{aksi}**\n"
        f"Jika kamu melakukannya, gunakan `$Claim <Action>` dan dapatkan **+25 XP & +25 Gold!** 🎉"
        f" **Minimal 20 kata** \n"
    )

@Event.error
async def event_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Waduh, cuma **Admin** yang bisa mulai event lingkungan!")    

@bot.command()
async def Claim(ctx, *, cerita: str):
    event = muat_event()
    aksi = event.get("aksi_event", "")
    sudah = event.get("sudah_klaim", [])

    if not aksi:
        await ctx.send("⚠️ Belum ada event eksklusif yang aktif.")
        return

    if len(cerita.split()) < 20:
        await ctx.send("⚠️ Ceritamu terlalu pendek! Harus minimal **20 kata** agar bisa diklaim.")
        return

    if sudah:
        await ctx.send("🚫 Klaim untuk event eksklusif ini sudah diambil oleh orang lain. Tunggu event berikutnya!")
        return

    if aksi.lower() in cerita.lower():
        event["aksi_event"] = "" 
        simpan_event(event) 
    
        reward_type, reward_emoji = tambah_data_random(ctx.author.id, 25)
        event["sudah_klaim"].append(str(ctx.author.id)) 
        simpan_event(event)
        await ctx.send(
            f"✅ Cerita kamu cocok dengan event eksklusif ini: _{aksi}_\n"
            f"🎉 Selamat {ctx.author.mention}, kamu ORANG PERTAMA🥇 yang mengklaim dan mendapat **+25 {reward_type}!** {reward_emoji}"
        )
    else:
        await ctx.send(
            f"⚠️ Cerita kamu belum mencantumkan aksi event eksklusif ini (**{aksi}**).\n"
            f"Pastikan kamu benar-benar melakukan aksi tersebut!"
        )

@bot.command()
async def Levelbadge(ctx):
    pesan = "**🏅 Level Badges List**\n"
    for level, badge in sorted(LEVEL_BADGES.items()):
        pesan += f"Level {level}: {badge}\n"
    await ctx.send(pesan)

@bot.command()
@commands.has_permissions(administrator=True) # Hanya yang punya role Admin di server
async def AdminBoost(ctx):
    tambah_data(ctx.author.id, 10000, 10000)
    
    xp_sekarang = ambil_xp(ctx.author.id)
    gold_sekarang = ambil_gold(ctx.author.id)
    level = hitung_level(xp_sekarang)
    badge = ambil_badge(xp_sekarang)

    await ctx.send(
        f"⚡ **Admin Boost Berhasil!** ⚡\n"
        f"XP: **{xp_sekarang}** | Gold: **{gold_sekarang}**\n"
        f"Level: **{level}** (MAX)\n"
        f"Badge: **{badge}**"
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def CreateShopRoles(ctx):
    """Membuat semua role untuk shop secara otomatis"""
    roles_created = []
    roles_failed = []
    
    for item_id, item in SHOP_ITEMS.items():
        if 'role_name' in item:
            role_name = item['role_name']
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            
            if role:
                roles_failed.append(f"{role_name} (sudah ada)")
            else:
                try:
                    await ctx.guild.create_role(
                        name=role_name,
                        colour=discord.Color.green(),
                        reason="Created by Zenn VII Shop System"
                    )
                    roles_created.append(role_name)
                except Exception as e:
                    roles_failed.append(f"{role_name} (error: {e})")
    
    if roles_created:
        await ctx.send(f"✅ **Role Berhasil Dibuat:**\n" + "\n".join(f"• {r}" for r in roles_created))
    if roles_failed:
        await ctx.send(f"⚠️ **Role Gagal:**\n" + "\n".join(f"• {r}" for r in roles_failed))
    
    if not roles_created and not roles_failed:
        await ctx.send("ℹ️ Tidak ada role yang perlu dibuat untuk shop items.")

# Biar keren, kasih pesan kalau ada member biasa yang coba-coba
@AdminBoost.error
async def admin_boost_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Akses ditolak! Command ini khusus untuk **Petingi Lingkungan**.")

@CreateShopRoles.error
async def create_shop_roles_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Akses ditolak! Command ini khusus untuk **Petingi Lingkungan**.")

@bot.command()
@commands.has_permissions(administrator=True) # Hanya yang punya role Admin di server
async def Reset_Tips(ctx, member: discord.Member = None):
    hari_ini = str(datetime.date.today())
    tips_log = muat_tips_log()

    if hari_ini not in tips_log:
        await ctx.send("⚠️ Belum ada data penggunaan tips untuk hari ini.")
        return

    if member:
        # Reset jatah untuk satu orang spesifik
        user_id = str(member.id)
        if user_id in tips_log[hari_ini]:
            tips_log[hari_ini][user_id] = 0
            simpan_tips_log(tips_log)
            await ctx.send(f"✅ Jatah poin `$Green_Action` untuk {member.mention} telah direset ke 0!")
        else:
            await ctx.send(f"⚠️ {member.display_name} memang belum mengambil jatah poin hari ini.")
    else:
        # Reset jatah untuk SEMUA orang di hari ini
        tips_log[hari_ini] = {}
        simpan_tips_log(tips_log)
        await ctx.send("♻️ **Global Reset!** Jatah poin harian `$Green_Action` untuk semua user telah direset!")

@Reset_Tips.error
async def reset_tips_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 Cuma **Admin** yang punya kunci untuk mereset jatah poin!")

#WEB SCRAPING FUNCTION
@bot.command()
async def WebScraping(ctx):
    await ctx.send(
        "**Web Scraping** adalah teknik mengambil data otomatis dari website. "
        "Di bot ini: `$Quotes` dan `$Books` mengambil langsung dari web; "
        "koleksi buku lengkap disimpan di JSON oleh pemilik bot (`$TrueAdminBookDescription`), "
        "lalu `$BookDescription` membaca dari file itu supaya responsnya ringan dan cepat. 🌐✨"
    )

@bot.command()
async def Quotes(ctx):
    await ctx.send("🔎 Lagi nyari kata-kata mutiara di internet... tunggu ya!")
    
    try:
        hasil = await asyncio.to_thread(ambil_quotes_dari_web)
        
        # Pilih satu quote secara acak dari 10 hasil scraping
        quote_pilihan = random.choice(hasil)
        
        # Kirim ke Discord
        await ctx.send(quote_pilihan)
        
    except Exception as e:
        await ctx.send(f"Waduh, gagal ngambil data karena: {e}")

@bot.command()
async def Books(ctx):
    global LAST_SEARCH_TIME
    user_id = str(ctx.author.id)
    waktu_sekarang = time.time()
    
    # Cek Cooldown Reducer
    durasi_cooldown = 1800 # Default 30 menit
    if has_item(user_id, "Cooldown Reducer"):
        durasi_cooldown = 900 # Jadi 15 menit
        bonus_text = "⚡ **(Cooldown Reducer Aktif: 15 Menit)**"
    else:
        bonus_text = ""

    # 1. Cek Cooldown
    if user_id in LAST_SEARCH_TIME:
        selisih = waktu_sekarang - LAST_SEARCH_TIME[user_id]
        if selisih < durasi_cooldown:
            menit = int((durasi_cooldown - selisih) / 60)
            detik = int((durasi_cooldown - selisih) % 60)
            return await ctx.send(f"⏳ **Sabar, Kawan!** Bot lagi istirahat. Tunggu **{menit} menit {detik} detik** lagi ya. {bonus_text}")

    await ctx.send("📚 **Membuka Perpustakaan Digital...** Mencari buku keren untukmu!")

    data_buku = await asyncio.to_thread(scrap_treehugger)
    
    if data_buku:
        pilihan_buku = random.choice(data_buku)
        
        # 3. Tambah Poin (+2 XP or Gold random)
        reward_type, reward_emoji = tambah_data_random(ctx.author.id, 2)
        
        # 4. Simpan Waktu
        LAST_SEARCH_TIME[user_id] = waktu_sekarang
        
        msg = f"📖 **Rekomendasi Buku Hari Ini:**\n"
        msg += f"> **{pilihan_buku}**\n\n"
        msg += f"✨ Wah, kamu baru saja mengeksplorasi literatur! Dapat **+2 {reward_type}!** {reward_emoji} 🌟\n"
        msg += f"*Sumber: Books to Scrape*"
        
        await ctx.send(msg)
    else:
        await ctx.send("❌ Gagal terhubung ke perpustakaan. Coba lagi nanti!")

@bot.command()
@commands.has_permissions(administrator=True) # Hanya kamu (Admin) yang bisa panggil
async def BooksAdmin(ctx):
    """
    Mode Rahasia: Ngecek apakah website Books to Scrape masih lancar
    tanpa harus nunggu cooldown 30 menit.
    """
    await ctx.send("🛠️ **[ADMIN MODE]** Menghubungkan ke Perpustakaan Books to Scrape...")

    try:
        data_buku = await asyncio.to_thread(scrap_treehugger)
        
        if data_buku:
            # Admin bisa lihat berapa banyak buku yang berhasil ditarik totalnya
            total_buku = len(data_buku)
            pilihan = random.choice(data_buku)
            
            msg = f"🔍 **Hasil Diagnosa Sistem:**\n"
            msg += f"> Berhasil menarik **{total_buku}** judul buku hari ini.\n"
            msg += f"> Contoh judul: **{pilihan}**\n\n"
            msg += f"✅ **Status:** Koneksi Stabil. Fitur multifungsi siap digunakan user!"
            
            await ctx.send(msg)
        else:
            await ctx.send("❌ **Status:** Gagal! Website merespon tapi data kosong. Cek struktur HTML!")

    except Exception as e:
        await ctx.send(f"⚠️ **Sistem Error:** {e}")

# Pesan otomatis kalau ada user biasa (bukan admin) yang sotoy mau pake perintah ini
@BooksAdmin.error
async def books_admin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ **Akses Ditolak!** Perintah ini hanya untuk developer bot.")

@bot.command()
async def BookDescription(ctx):
    """Buku acak dari database SQLite."""
    buku = get_random_book()
    
    if not buku:
        await ctx.send(
            "📚 **Perpustakaan masih kosong.**\n"
            "Pemilik bot bisa mengisi dengan `$TrueAdminBookDescription <jumlah>` "
            "(scraping ke web, lalu simpan ke SQLite). Setelah ada data, perintah ini jadi instan."
        )
        return

    await ctx.send("📖 **Membuka entri acak dari perpustakaan…**")
    sumber = "Database SQLite"

    judul = buku.get("judul", "Tanpa Judul")
    harga = buku.get("harga", "N/A")
    sinopsis = buku.get("deskripsi", "Tidak ada sinopsis.")
    url = buku.get("url", "https://books.toscrape.com/")

    if len(sinopsis) > 500:
        sinopsis = sinopsis[:500] + "..."

    msg = f"📖 **Informasi Buku Lengkap** 📖\n"
    msg += f"*(Sumber: {sumber})*\n\n"
    msg += f"**Judul:** {judul}\n"
    msg += f"**Harga:** {harga}\n"
    msg += f"**Sinopsis:**\n> {sinopsis}\n\n"
    msg += f"🔗 **Link Lengkap:** <{url}>"
    await ctx.send(msg)

@bot.command()
@commands.cooldown(15, 60, commands.BucketType.guild)
async def Zenn(ctx, *, pertanyaan: str):
    """
    Tanya ke AI Zenn VII - asisten lingkungan yang keren dan santai! 🌿
    AI akan mengingat percakapan sebelumnya untuk jawaban yang lebih personal.
    Limit: 10 pertanyaan per hari (Admin: unlimited)
    Cooldown: 15 kali per menit per server (Admin bypass cooldown)
    """
    if not pertanyaan.strip():
        await ctx.send("⚠️ **Masukkan pertanyaan kamu!** Contoh: `$zenn apa itu global warming?")
        return
    
    user_id = str(ctx.author.id)
    
    # Bypass cooldown for Admin
    if user_id == ADMIN_DISCORD_ID:
        ctx.command.reset_cooldown(ctx)
    
    # Check AI usage limit (The Guard System) - Discord platform with 10 limit
    can_use, remaining, message = check_ai_limit(user_id, ADMIN_DISCORD_ID, daily_limit=10, platform='discord')
    
    if not can_use:
        await ctx.send(f"🚫 **Limit Harian Tercapai!**\n\n{message}")
        return
    
    # Increment AI usage count
    increment_ai_count(user_id, platform='discord')
    
    # Show remaining uses to user
    if remaining != float('inf'):
        await ctx.send(f"📊 **Sisa Kuota AI Hari Ini:** {int(remaining)}/10")
    
    # Simpan pesan user ke database (memory)
    save_conversation(user_id, 'user', pertanyaan)
    
    # Ambil riwayat percakapan untuk context
    history = get_conversation_history(user_id, limit=5)
    
    # Kirim pesan "sedang berpikir"
    thinking_msg = await ctx.send("🤖 **Zenn VII sedang berpikir...** 🌿")
    
    try:
        # Panggil AI dengan history
        jawaban = await tanyakan_zenn(pertanyaan, conversation_history=history)
        
        # Simpan jawaban AI ke database (memory)
        save_conversation(user_id, 'assistant', jawaban)
        
        # Hapus pesan "sedang berpikir"
        try:
            await thinking_msg.delete()
        except discord.NotFound:
            # Message already deleted, ignore
            pass
        
        # Kirim jawaban
        msg = f"🌿 **Zenn VII berkata:**\n\n{jawaban}"
        await ctx.send(msg)
        
    except Exception as e:
        try:
            await thinking_msg.delete()
        except discord.NotFound:
            # Message already deleted, ignore
            pass
        await ctx.send(f"❌ **Error:** Terjadi masalah saat memproses pertanyaan. Coba lagi nanti ya!")
        print(f"AI Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

@bot.command()
async def Zenn_clear(ctx):
    """Hapus riwayat percakapan dengan Zenn VII."""
    user_id = str(ctx.author.id)
    # #region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H1",
        location="BOT.py:Zenn_clear:entry",
        message="Zenn_clear command invoked",
        data={"userIdLength": len(user_id)},
    )
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H2",
        location="BOT.py:Zenn_clear:pre-call",
        message="Checking clear_conversation symbol",
        data={
            "isDefinedInGlobals": "clear_conversation" in globals(),
            "callableInGlobals": callable(globals().get("clear_conversation")),
        },
    )
    # #endregion
    try:
        clear_conversation(user_id)
    except Exception as e:
        # #region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H3",
            location="BOT.py:Zenn_clear:exception",
            message="Exception while clearing conversation",
            data={"errorType": type(e).__name__, "errorMessage": str(e)},
        )
        # #endregion
        raise
    await ctx.send("🗑️ **Riwayat percakapan dengan Zenn VII telah dihapus!** Zenn akan mulai fresh dari awal.")

@Zenn.error
async def zenn_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        # Memberitahu sisa waktu tunggu dengan 1 angka di belakang koma
        await ctx.send(f"Sabar ya! Fitur $Zenn lagi ramai. Coba lagi dalam {error.retry_after:.1f} detik.")

class BookSelect(ui.Select):
    def __init__(self, books, ctx):
        self.books = books
        self.ctx = ctx
        options = []
        for i, book in enumerate(books[:25]):  # Limit to 25 options for Discord
            judul = book.get("judul", "Tanpa Judul")[:100]  # Truncate title
            option = ui.SelectOption(label=f"{i+1}. {judul}", value=str(i))
            options.append(option)
        super().__init__(placeholder="Pilih buku untuk detail...", options=options)

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        book = self.books[index]
        judul = book.get("judul", "Tanpa Judul")
        harga = book.get("harga", "N/A")
        sinopsis = book.get("deskripsi", "Tidak ada sinopsis.")
        url = book.get("url", "https://books.toscrape.com/")
        if len(sinopsis) > 500:
            sinopsis = sinopsis[:500] + "..."
        msg = f"📖 **Detail Buku** 📖\n\n"
        msg += f"**Judul:** {judul}\n"
        msg += f"**Harga:** {harga}\n"
        msg += f"**Sinopsis:**\n> {sinopsis}\n\n"
        msg += f"🔗 **Link Lengkap:** <{url}>"
        await interaction.response.send_message(msg, ephemeral=True)

class BookView(ui.View):
    def __init__(self, books, ctx):
        super().__init__(timeout=300)  # 5 minutes
        self.add_item(BookSelect(books, ctx))

@bot.command()
async def FindBooks(ctx, *, keyword: str):
    """Cari buku berdasarkan keyword di judul atau deskripsi."""
    if not keyword.strip():
        await ctx.send("⚠️ Masukkan keyword untuk pencarian!")
        return

    hasil_cari = search_books(keyword)

    if not hasil_cari:
        await ctx.send(f"❌ Tidak ada buku yang cocok dengan keyword **'{keyword}'**.")
        return

    jumlah_hasil = len(hasil_cari)
    max_tampil = min(jumlah_hasil, 10)  # Tampilkan maksimal 10 buku
    msg = f"📚 **Hasil Pencarian untuk '{keyword}'** 📚\n\n"
    for i, book in enumerate(hasil_cari[:max_tampil], 1):
        judul = book.get("judul", "Tanpa Judul")
        msg += f"{i}. **{judul}**\n"
    if jumlah_hasil > max_tampil:
        msg += f"\n... dan {jumlah_hasil - max_tampil} buku lainnya (hanya 10 pertama yang ditampilkan)."
    msg += f"\n\n✨ Ditemukan **{jumlah_hasil}** buku. Balas dengan nomor (1-{max_tampil}) untuk detail buku!"
    sent_msg = await ctx.send(msg)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and 1 <= int(m.content) <= max_tampil

    try:
        reply = await bot.wait_for('message', check=check, timeout=60.0)
        index = int(reply.content) - 1
        book = hasil_cari[index]
        judul = book.get("judul", "Tanpa Judul")
        harga = book.get("harga", "N/A")
        sinopsis = book.get("deskripsi", "Tidak ada sinopsis.")
        url = book.get("url", "https://books.toscrape.com/")
        if len(sinopsis) > 500:
            sinopsis = sinopsis[:500] + "..."
        detail_msg = f"📖 **Detail Buku** 📖\n\n"
        detail_msg += f"**Judul:** {judul}\n"
        detail_msg += f"**Harga:** {harga}\n"
        detail_msg += f"**Sinopsis:**\n> {sinopsis}\n\n"
        detail_msg += f"🔗 **Link Lengkap:** <{url}>"
        await ctx.send(detail_msg)
    except asyncio.TimeoutError:
        await ctx.send("⏳ Waktu habis. Gunakan `$FindBooks <keyword>` lagi jika perlu.")

@bot.command()
@commands.is_owner()
async def TrueAdminBookDescription(ctx, jumlah: int = 25):
    if jumlah < 1:
        await ctx.send("⚠️ Jumlah minimal **1**.")
        return
    if jumlah > 100: # Batasi 100 dulu ya biar gak kena ban/spam
        await ctx.send("⚠️ Maksimal **100** buku per perintah biar bot gak kecapekan.")
        return

    await ctx.send(f"🚀 **True Admin Mode:** Mengambil **{jumlah}** buku. Proses ini berjalan di *background thread*...")

    try:
        # Menjalankan fungsi scraping dengan cek duplikat seperti auto-scraping
        buku_baru_list = await asyncio.to_thread(scrape_buku_baru, jumlah)
        
        if not buku_baru_list:
            await ctx.send("ℹ️ **Scraping Selesai:** Semua buku yang ditemukan sudah ada di database atau tidak ada data baru.")
            return

        # Simpan buku baru ke SQLite
        buku_ditambahkan = 0
        for buku in buku_baru_list:
            add_book(buku["judul"], buku["harga"], buku["deskripsi"], buku["url"])
            buku_ditambahkan += 1

        msg = f"✅ **Update Selesai!**\n"
        msg += f"Baru ditambahkan: **{buku_ditambahkan}** buku ke SQLite."
        
        await ctx.send(msg)

    except Exception as e:
        await ctx.send(f"❌ Terjadi error sistem: {e}")

# ... rest of the code remains the same ...
# Pesan Error jika yang memanggil bukan Admin
@TrueAdminBookDescription.error
async def true_admin_book_description_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("⛔ **Akses Ditolak!** Perintah ini hanya bisa digunakan oleh Pengembang Bot (True_Admin).")

@bot.command()
async def Scan(ctx):
    if ctx.message.attachments:
        # 1. Simpan gambar dari Discord
        await ctx.send("🔍 Memproses gambar...")
        await ctx.message.attachments[0].save("temp.jpg")
        
        try:
            # 2. Tanya ke si "Otak" (brain.py)
            label, score = check_image("temp.jpg")
            
            # Debug: print hasil prediksi
            print(f"DEBUG: Label={label}, Score={score}")
            
            # 3. Logika Poin + respons variatif dari Gemini
            if "Target" in label and score > 0.90:
                # Tambah poin ke user
                user_id = str(ctx.author.id)
                if os.path.exists(POIN_FILE):
                    with open(POIN_FILE, "r", encoding="utf-8") as f:
                        poin_data = json.load(f)
                else:
                    poin_data = {}
                
                poin_data[user_id] = poin_data.get(user_id, 0) + 10
                
                with open(POIN_FILE, "w", encoding="utf-8") as f:
                    json.dump(poin_data, f, indent=4, ensure_ascii=False)
                
                # Kirim pesan "sedang berpikir" untuk penjelasan AI
                thinking_msg = await ctx.send("🤖 **Zenn VII sedang menganalisis...** 🌿")
                
                try:
                    # Gemini "buka suara" berdasarkan hasil Keras
                    penjelasan = await respons_scan(label, score, "", True)
                    
                    # Hapus pesan "sedang berpikir"
                    try:
                        await thinking_msg.delete()
                    except discord.NotFound:
                        # Message already deleted, ignore
                        pass
                    
                    # Kirim penjelasan dari Gemini + info poin
                    msg = f"{penjelasan}\n\n✅ **+10 Poin!** 🌿"
                    await ctx.send(msg)
                    
                except Exception as e:
                    try:
                        await thinking_msg.delete()
                    except discord.NotFound:
                        # Message already deleted, ignore
                        pass
                    # Fallback jika Gemini error
                    await ctx.send(f"✅ AI Yakin ini {label} sampahnya ({score*100:.0f}%). +10 Poin! 🌿")
                    print(f"AI Error: {e}")
            else:
                # Tetap minta Gemini kasih respons variatif walau belum lolos target
                thinking_msg = await ctx.send("🤖 **Zenn VII sedang menganalisis...** 🌿")
                try:
                    penjelasan = await respons_scan(label, score, "", False)
                    try:
                        await thinking_msg.delete()
                    except discord.NotFound:
                        pass
                    await ctx.send(penjelasan)
                except Exception as e:
                    try:
                        await thinking_msg.delete()
                    except discord.NotFound:
                        pass
                    await ctx.send(f"❌ AI tidak yakin ini sampah (Label: {label}, Confidence: {score*100:.0f}%). Coba foto lebih dekat!")
                    print(f"AI Error: {e}")
        except Exception as e:
            await ctx.send(f"❌ Error saat memproses gambar: {e}")
    else:
        await ctx.send("⚠️ Tolong kirim gambar dengan command ini! Upload gambar lalu ketik $scan")

@bot.command(name='Exclusive_Event')
async def exclusive_event(ctx, *, target_object: str):
    """Create exclusive event (ADMIN ONLY)"""
    # Check if user is admin
    if str(ctx.author.id) != str(ADMIN_DISCORD_ID):
        await ctx.send("⛔ **Waduh!** Perintah ini khusus Admin aja ya! Kamu gak punya akses nih! 🚫")
        return
    
    if not target_object:
        await ctx.send("🤔 **Hmm...** Kamu lupa tentukan objek targetnya! Contoh: `$Exclusive_Event botol plastik` 📸")
        return
    
    # Create event in database
    success = create_exclusive_event(target_object)
    
    if success:
        await ctx.send(f"@everyone 🚨 **EXCLUSIVE EVENT DIMULAI!** 🎉 Siapa cepat dia dapat! Gunakan command `$Claim_Exclusive` dan sertakan foto **{target_object}** untuk mendapatkan +20 poin! 🌟💚")
    else:
        await ctx.send("❌ **Yah!** Gagal bikin event nih. Coba lagi nanti ya! 🛠️")

@bot.command(name='Claim_Exclusive')
async def claim_exclusive(ctx):
    """Claim exclusive event with image validation"""
    if not ctx.message.attachments:
        await ctx.send("📸 **Yah!** Kamu lupa upload gambar nih! Kirim foto dulu, baru ketik `$Claim_Exclusive` ya! 🌿")
        return
    
    # Check event status
    event = check_event_status()
    
    if not event:
        await ctx.send("😔 **Hmm...** Sepertinya belum ada event eksklusif yang aktif saat ini. Tunggu info dari Admin ya! 🎯")
        return
    
    # Check if already claimed (database handles this now)
    if event['winner_id']:
        # Let the database function handle the time check
        await ctx.send("😅 **Ups!** Event ini baru saja diklaim oleh orang lain! Jangan sedih, nanti ada event lain lagi kok! 🎁")
        return
    
    # Save image
    await ctx.send("🔍 **Wih!** Zenn lagi cek fotonya nih... Tunggu sebentar ya! 🤖")
    await ctx.message.attachments[0].save("temp_exclusive.jpg")
    
    # Validate with Gemini
    target_object = event['target_object']
    validation_result = await validate_image_with_gemini("temp_exclusive.jpg", target_object)
    
    if validation_result == "VALID":
        # Claim the event
        user_id = str(ctx.author.id)
        success, message = claim_exclusive_event(user_id)
        
        if success:
            # Add XP or Gold (+25 random for event)
            reward_type, reward_emoji = tambah_data_random(user_id, 25)
            
            await ctx.send(f"🎉 **SELAMAT!** Kamu berhasil klaim event eksklusif! Foto **{target_object}** kamu keren banget! +25 {reward_type} untukmu! {reward_emoji} 🌟💚")
        elif message == "recently_claimed":
            await ctx.send("😅 **Ups!** Event ini baru saja diklaim oleh orang lain! Jangan sedih, nanti ada event lain lagi kok! 🎁")
        elif message == "no_event":
            await ctx.send("😔 **Hmm...** Sepertinya belum ada event eksklusif yang aktif saat ini. Tunggu info dari Admin ya! 🎯")
        else:
            await ctx.send("❌ **Yah!** Terjadi error sistem. Coba lagi nanti ya! 🛠️")
    else:
        await ctx.send(f"🤔 **Hmm...** Kayaknya fotonya bukan **{target_object}** deh. Coba foto yang lebih jelas ya! 📸")

# ==================== SHOP, BUY, & GACHA COMMANDS ====================

SHOP_ITEMS = {
    "1": {"name": "Exclusive Discord Role", "price": 125, "rarity": "Rare", "desc": "Role khusus & warna nama keren di Discord!", "role_name": "🌿 Eco Warrior"},
    "2": {"name": "Cooldown Reducer", "price": 250, "rarity": "Epic", "desc": "Potong waktu tunggu fitur $Books & $Explore!"},
    "3": {"name": "AI Recharge Ticket", "price": 500, "rarity": "Legendary", "desc": "Tambah +5 jatah nanya $Zenn per hari!"}
}

GACHA_POOL = [
    {"name": "💾 Junk Data", "rarity": "Common", "weight": 35},
    {"name": "🔋 Low Battery", "rarity": "Common", "weight": 35},
    {"name": "📡 Signal Booster", "rarity": "Rare", "weight": 12},
    {"name": "📟 Vintage Circuit", "rarity": "Rare", "weight": 12},
    {"name": "🌀 Solar Core", "rarity": "Epic", "weight": 2.5},
    {"name": "⚡ Kinetic Engine", "rarity": "Epic", "weight": 2.5},
    {"name": "🌌 Zenn Quantum Chip", "rarity": "Legendary", "weight": 1}
]

@bot.command(name='Shop')
async def shop(ctx):
    """Menampilkan daftar item di Toko Hijau"""
    embed = discord.Embed(title="🏪 Toko Hijau Zenn VII", color=discord.Color.green())
    embed.description = "Tukarkan poin hijau kamu dengan fitur keren! 🌿"
    
    for item_id, info in SHOP_ITEMS.items():
        embed.add_field(
            name=f"[{item_id}] {info['name']} ({info['rarity']})",
            value=f"💰 Harga: **{info['price']} Poin**\n📝 {info['desc']}",
            inline=False
        )
    
    embed.add_field(
        name="🎲 Gacha Koleksi Badge",
        value="💰 Harga: **15 Gold**\n📝 Dapatkan badge acak untuk profilmu!\nCommand: `$Gacha`",
        inline=False
    )
    
    embed.set_footer(text=f"XP: {ambil_xp(ctx.author.id)} | Gold: {ambil_gold(ctx.author.id)} | Gunakan $Buy <id> untuk membeli")
    await ctx.send(embed=embed)

@bot.command(name='Buy')
async def buy(ctx, item_id: str = None):
    """Membeli item dari shop"""
    if not item_id or item_id not in SHOP_ITEMS:
        await ctx.send("⚠️ Masukkan ID item yang bener dong! Contoh: `$Buy 1` (cek ID di `$Shop`)")
        return
    
    item = SHOP_ITEMS[item_id]
    user_id = str(ctx.author.id)
    
    if kurangi_gold(user_id, item['price']):
        from database import add_to_inventory, add_ai_boost, get_inventory
        
        # Logika khusus per item
        if item_id == "3": # AI Recharge
            add_ai_boost(user_id, 5)
            await ctx.send(f"✅ **Berhasil!** Kamu membeli **{item['name']}**! Jatah $Zenn harianmu bertambah +5! 🎫✨")
        else:
            # Check if user already has this item
            existing_items = get_inventory(user_id)
            already_has = any(existing_item['item_id'] == item_id for existing_item in existing_items)
            
            if already_has:
                # Refund gold
                data = muat_poin()
                data[user_id]["gold"] += item['price']
                simpan_poin(data)
                await ctx.send(f"⚠️ Kamu sudah punya **{item['name']}** di inventory! Gold sudah dikembalikan.")
                return
            
            # Add to inventory
            added = add_to_inventory(user_id, item_id, item['name'], item['rarity'])
            
            if not added:
                # Refund gold if add failed (shouldn't happen with our check above)
                data = muat_poin()
                data[user_id]["gold"] += item['price']
                simpan_poin(data)
                await ctx.send(f"⚠️ Gagal menambahkan item ke inventory. Gold sudah dikembalikan.")
                return
            
            # Auto assign role for item 1
            if item_id == "1":
                role_name = item.get('role_name', '🌿 Elite Donator')
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                
                if not role:
                    # Create role if it doesn't exist
                    try:
                        role = await ctx.guild.create_role(
                            name=role_name,
                            colour=discord.Color.green(),
                            reason="Auto-created by Zenn VII Shop"
                        )
                        await ctx.send(f"✅ Role **{role_name}** berhasil dibuat!")
                    except Exception as e:
                        await ctx.send(f"⚠️ Gagal membuat role: {e}")
                        await ctx.send(f"✅ **Berhasil!** Kamu membeli **{item['name']}**! Item sudah masuk ke `$Inventory`. 🎁")
                        return
                
                # Assign role to user
                try:
                    await ctx.author.add_roles(role)
                    await ctx.send(f"✅ **Berhasil!** Kamu membeli **{item['name']}**! Role **{role_name}** sudah ditambahkan ke profilmu! 🎭✨")
                except Exception as e:
                    await ctx.send(f"⚠️ Gagal menambahkan role: {e}")
                    await ctx.send(f"✅ **Berhasil!** Kamu membeli **{item['name']}**! Item sudah masuk ke `$Inventory`. 🎁")
            else:
                await ctx.send(f"✅ **Berhasil!** Kamu membeli **{item['name']}**! Item sudah masuk ke `$Inventory`. 🎁")
    else:
        await ctx.send(f"❌ **Gold Gak Cukup!** Kamu butuh **{item['price']} Gold**, tapi saldomu cuma **{ambil_gold(user_id)} Gold**. Ayo kumpulin lagi! 💪")

@bot.command(name='Gacha')
async def gacha(ctx):
    """Gacha badge koleksi (15 Gold) - No Refund, Pure Gacha!"""
    user_id = str(ctx.author.id)
    biaya = 15
    
    # 1. Cek dan potong gold di awal
    if not kurangi_gold(user_id, biaya):
        await ctx.send(f"❌ **Gold Gak Cukup!** Gacha butuh **{biaya} Gold**. Saldomu: {ambil_gold(user_id)} Gold")
        return
    
    # 2. Animasi gacha sederhana
    msg = await ctx.send("🎰 **Memutar Gacha...** 🤞")
    await asyncio.sleep(2)
    
    # 3. Logic gacha dengan weight
    items = GACHA_POOL
    names = [i['name'] for i in items]
    weights = [i['weight'] for i in items]
    
    result = random.choices(items, weights=weights, k=1)[0]
    
    from database import add_to_inventory
    
    # 4. Langsung masukkan ke inventory (Tanpa cek duplikat)
    added = add_to_inventory(user_id, "gacha_badge", result['name'], result['rarity'])
    
    # Safeguard jika database error (opsional)
    if not added:
        data = muat_poin()
        data[user_id]["gold"] += biaya
        simpan_poin(data)
        await msg.edit(content=f"⚠️ Sistem error saat menyimpan item. Gold dikembalikan.")
        return
    
    # 5. Tampilan Embed Hasil
    color = {
        "Common": discord.Color.light_grey(),
        "Rare": discord.Color.blue(),
        "Epic": discord.Color.purple(),
        "Legendary": discord.Color.gold()
    }.get(result['rarity'], discord.Color.green())
    
    embed = discord.Embed(title="✨ HASIL GACHA! ✨", color=color)
    embed.add_field(name="Item Didapat:", value=f"**{result['name']}**", inline=False)
    embed.add_field(name="Rarity:", value=result['rarity'], inline=True)
    embed.set_footer(text=f"Berhasil ditambahkan ke inventory {ctx.author.name}")
    
    await msg.edit(content=None, embed=embed)

class BadgeSelect(ui.Select):
    def __init__(self, user_id, options):
        super().__init__(placeholder="Pilih badge untuk ditampilkan...", options=options)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ini bukan menu kamu!", ephemeral=True)
            return
            
        badge_name = self.values[0]
        from database import set_selected_badge
        if set_selected_badge(self.user_id, badge_name):
            await interaction.response.send_message(f"✅ Berhasil! **{badge_name}** sekarang ditampilkan di profilmu! 🎭", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Gagal menyimpan pilihan. Coba lagi nanti.", ephemeral=True)

class BadgeSelectView(ui.View):
    def __init__(self, user_id, options):
        super().__init__()
        self.add_item(BadgeSelect(user_id, options))

@bot.command(name='Select')
async def select_badge(ctx):
    """Memilih badge dari gacha untuk ditampilkan di profil"""
    from database import get_inventory
    user_id = str(ctx.author.id)
    items = get_inventory(user_id)
    
    # Filter hanya item hasil gacha
    gacha_badges = [i['item_name'] for i in items if i['item_id'] == "gacha_badge"]
    
    if not gacha_badges:
        await ctx.send("❌ Kamu belum punya badge hasil gacha! Yuk `$Gacha` dulu (15 Poin).")
        return
        
    # Ambil unik badge saja
    unique_badges = sorted(list(set(gacha_badges)))
    
    options = []
    for badge in unique_badges[:25]: # Limit 25 untuk Discord Select Menu
        options.append(discord.SelectOption(label=badge, description="Pasang badge ini di profilmu"))
        
    view = BadgeSelectView(user_id, options)
    await ctx.send("🎭 **Pilih Badge Gacha-mu:**\nBadge yang kamu pilih akan muncul sebagai 'Badge Aktif' di profile website!", view=view)

@bot.command(name='Inventory')
async def inventory(ctx):
    from database import get_inventory, get_ai_boost
    user_id = str(ctx.author.id)
    items = get_inventory(user_id)
    extra_ai = get_ai_boost(user_id)
    
    embed = discord.Embed(title=f"🎒 Inventory {ctx.author.display_name}", color=discord.Color.blue())
    
    if extra_ai > 0:
        embed.add_field(name="⚡ AI Boost Active", value=f"Total: +{extra_ai} jatah harian", inline=False)
    
    if not items:
        embed.description = "Inventory kamu masih kosong melompong. Yuk belanja di `$Shop`! 🛒"
    else:
        # --- PERBAIKAN DI SINI ---
        # Gunakan set() untuk membuang duplikat secara otomatis
        # Kita simpan dalam format string yang unik
        unique_items = set()
        for i in items:
            unique_items.add(f"• **{i['item_name']}** ({i['rarity']})")
        
        # Ubah kembali menjadi list agar bisa digabung
        inv_list = list(unique_items)
        
        # Gabungkan item menjadi teks tunggal
        full_text = "\n".join(inv_list)
        
        # Tetap jaga limit karakter agar tidak error 400 Bad Request
        if len(full_text) > 1024:
            # Gunakan description karena limitnya 4096 karakter
            embed.description = full_text[:4095] 
        else:
            # Jika aman di bawah 1024, masukkan ke field
            embed.add_field(name="📦 Daftar Barang (Unik):", value=full_text, inline=False)
        
    await ctx.send(embed=embed)
    
@bot.command(name='Bug')
@commands.has_permissions(administrator=True)
async def bug_report(ctx, *, laporan: str = None):
    """Melaporkan bug atau kesalahan bot (Khusus Admin Server)"""
    if not laporan:
        await ctx.send("⚠️ Tolong masukkan isi laporannya, bro! Contoh: `$Bug Fitur gacha gambarnya pecah`")
        return
    
    from database import save_bug_report
    user_id = str(ctx.author.id)
    username = str(ctx.author)
    guild_name = ctx.guild.name if ctx.guild else "Direct Message"
    
    if save_bug_report(user_id, username, guild_name, laporan):
        embed = discord.Embed(title="✅ Laporan Terkirim!", color=discord.Color.green())
        embed.description = f"Terima kasih **{ctx.author.display_name}**! Laporan kamu sudah masuk ke database pusat untuk dicek oleh Admin Proyek. 🛠️"
        embed.add_field(name="Isi Laporan:", value=f"_{laporan}_", inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Waduh, gagal nyimpen laporan ke database. Coba lagi nanti ya!")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit(
        "Set environment variable DISCORD_TOKEN to your bot token before running.\n"
        "If your token was ever pasted into code or chat, revoke it in the Discord "
        "Developer Portal and create a new one."
    )

def cek_dns_discord():
    """Discord pakai hostname discord.com; kalau DNS gagal, bot tidak akan bisa login."""
    try:
        socket.getaddrinfo("discord.com", 443, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SystemExit(
            "\n=== Gagal DNS / jaringan (bukan bug kode bot) ===\n"
            "PC tidak bisa menerjemahkan alamat discord.com (getaddrinfo gagal).\n\n"
            "Coba urut ini:\n"
            "  1) Buka https://discord.com di browser — kalau tidak bisa, masalahnya jaringan/DNS.\n"
            "  2) Ganti DNS Windows ke 8.8.8.8 dan 8.8.4.4, atau 1.1.1.1.\n"
            "  3) Matikan VPN / hotspot sekolah yang memblokir Discord; coba hotspot HP.\n"
            "  4) Restart router; matikan sementara 'HTTPS scanning' di antivirus.\n\n"
            f"Detail: {e}\n"
        ) from e

cek_dns_discord()

def catat_log_nyala():
    waktu_sekarang = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("bot_history.txt", "a") as f:
        f.write(f"Bot dinyalakan pada: {waktu_sekarang}\n")

if __name__ == "__main__":
    cek_dns_discord()
    catat_log_nyala()
    bot.run(TOKEN)
