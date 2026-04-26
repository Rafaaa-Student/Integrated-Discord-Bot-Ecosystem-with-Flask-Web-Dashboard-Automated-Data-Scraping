# Zenn' VII 🌿🤖

Bot Discord interaktif yang menggabungkan **gamifikasi aksi hijau**, **web scraping**, dan **dashboard website** untuk mendorong gaya hidup ramah lingkungan.

---

## 📋 Fitur Utama

### 🌱 Fitur Aksi Hijau (Green Action System)
Bot ini dirancang untuk memotivasi pengguna melakukan tindakan ramah lingkungan dengan sistem poin dan level:

- **$Green_Action**: Dapatkan tips hijau harian + 1 poin (max 3x sehari)
- **$Action <aksi>**: Catat aksi hijau (misal: "Menanam pohon") + 5 poin
- **$Story <cerita>**: Cerita storytelling 30+ kata tentang aktivitas hijau (poin sesuai aksi yang terdeteksi)
- **$Points**: Lihat total poin dan level badge kamu
- **$Leaderboard**: Ranking top 5 pengguna dengan poin tertinggi
- **$Levelbadge**: Lihat daftar badge dari level 1-100
- **$Add_Action <aksi>**: Usulkan aksi hijau baru
- **$Event** (Admin): Mulai event eksklusif dengan aksi spesifik
- **$Claim <cerita>**: Klaim event eksklusif (hanya 1 orang pertama) + 25 poin
- **$Reset_Tips** (Admin): Reset jatah poin harian pengguna
- **$Kategori**: Lihat kategori sampah (organik/anorganik/berbahaya)
- **$Pilah <sampah>**: Cek kategori jenis sampah
- **$Tambah_Kategori**: Tambah jenis sampah baru ke kategori
- **$Scan**: Upload gambar untuk klasifikasi AI (Target/Neutral/Distraction) + 10 poin jika confidence > 90%

### 🕸️ Fitur Web Scraping
Mengambil data dari internet untuk memberikan rekomendasi dan informasi:

- **$Quotes**: Ambil quote inspiratif acak dari website
- **$Books**: Rekomendasi buku random dengan cooldown 30 menit (+ 2 poin)
- **$BookDescription**: Buku acak dari database lokal dengan sinopsis lengkap
- **$FindBooks <keyword>**: Cari buku berdasarkan judul atau deskripsi
- **$BooksAdmin** (Admin): Mode diagnostik untuk cek status koneksi scraping
- **$TrueAdminBookDescription <jumlah>** (Owner): Scrape & simpan buku ke database JSON (hanya buku yang belum ada, cek duplikat otomatis)
- **Auto-Scraping**: Scrap otomatis 10 buku baru setiap 12 jam (hanya yang belum ada di database)

### 🎮 Fitur Hiburan Umum
Perintah tambahan untuk interaksi santai:

- **$Halo**: Sapaan dari bot
- **$Goodbye**: Emoji senyuman
- **$Emoji**: Emoji random
- **$Dadu**: Roll dadu 1-6 dengan respons unik
- **$Koin**: Lempar koin (Kepala/Ekor)
- **$Passgen <jumlah>**: Generate password acak (4-64 karakter)
- **$Menambahkan <angka1> <angka2>**: Kalkulator penjumlahan
- **$Ulang <jumlah> <kata>**: Ulangi kata N kali
- **$Bebek**: Gambar bebek random
- **$Rubah**: Gambar rubah random

### 🤖 Fitur AI Generative
AI powered by Google Gemini 2.5 Flash untuk tanya jawab:

- **$Zenn <pertanyaan>**: Tanya ke AI Zenn VII tentang lingkungan (Limit: 25/hari untuk user, unlimited untuk admin)
- **$Zenn_clear**: Hapus riwayat percakapan dengan AI
- AI mengingat 5 percakapan terakhir untuk konteks yang lebih personal
- Respon edukatif dengan gaya santai dan ramah lingkungan

### 🌐 Fitur Website Dashboard
Dashboard interaktif untuk memantau data bot:

- **Discord OAuth2 Login**: Login/logout dengan akun Discord
- **Role-based Access Control**: Guest, User, dan Admin roles
- **AI Chat Interface**: Chat dengan Zenn VII AI langsung dari web (limit 25/hari untuk user, unlimited admin)
- **Real-time Updates**: SocketIO untuk update data live tanpa refresh
- **Home**: Statistik total users, poin hijau, koleksi buku dengan grafik visual (Chart.js)
- **Leaderboard**: Ranking poin hijau users
- **Books**: Lihat koleksi buku dari database
- **Search Books**: Cari buku berdasarkan keyword
- **Admin Controls**: Kirim pesan ke bot Discord, trigger scraping buku, buat event baru
- **Dark/Light Mode Toggle**: Switch tema dengan efek 3D sphere di dark mode
- **Interactive Features**: Emoji rain, ganti background hero section, fakta random dengan efek 3D

### 🔌 Sistem API Internal
Bot menjalankan API server internal di `localhost:8080` untuk terintegrasi dengan website:

- **/send_message**: Kirim pesan ke channel Discord dari website
- **/trigger_scraping**: Trigger scraping buku dari website
- **/trigger_event**: Buat event baru dari website
- Website Flask sebagai client yang mengontrol bot Discord secara real-time

---

## 📊 Sistem Level & Badge

Bot menggunakan sistem level berbasis poin hijau:

| Level | Badge | Poin |
|-------|-------|------|
| 1 | 🌱 Newbie | 0-4 |
| 5 | 🍃 Fresh Starter | 20-24 |
| 10 | 🌿 Green Explorer | 45-49 |
| 30 | 🌲 Eco Enthusiast | 145-149 |
| 50 | 🌍 Environmental Hero | 245-249 |
| 100 | 🏆 Legendary Green Champion | 495+ |

---

## 🚀 Cara Setup & Menjalankan

### Prerequisites
- Python 3.12+
- pip (Python package manager)
- Discord bot token
- Git (opsional, untuk push ke GitHub)

### 1. Install Dependencies

```powershell
# Install library Python
pip install discord.py requests beautifulsoup4 certifi flask aiohttp python-dotenv tf-keras pillow

# Atau dari requirements.txt
pip install -r requirements.txt
```

### 2. Setup Environment Variable

Set environment variables di file `.env`:

```env
# Discord Bot
DISCORD_TOKEN=your_discord_bot_token

# Flask Website
FLASK_SECRET_KEY=your_flask_secret_key

# Discord OAuth2
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
ADMIN_DISCORD_ID=your_admin_discord_id

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Migrasi Data (Opsional - jika ada data JSON lama)

Jika Anda memiliki data buku lama dari versi sebelumnya (database_buku_log.json), jalankan migrasi:

```powershell
# Jalankan script migrasi (sekali saja)
python migrate_json_to_sqlite.py
```

Script ini akan:
- Membaca data dari `database_buku_log.json`
- Migrasi semua data ke SQLite (`books.db`)
- Membuat backup file `database_buku_log.json.backup`

### 4. Menjalankan Bot

```powershell
# Jalankan bot Discord
python BOT.py

# Jalankan website dashboard (di terminal terpisah)
cd website
python app.py
```

Bot akan otomatis:
- Login ke Discord
- Start API server di `localhost:8080`
- Jalankan auto-scraping setiap 12 jam
- Website akan tersedia di `http://localhost:5000`

---

## 🏗️ Arsitektur Sistem

Bot menggunakan arsitektur terintegrasi antara Discord bot dan website:

```
Discord Bot (BOT.py)           Website Dashboard (Flask)
       ↓                              ↓
  - Commands                    - Statistics
  - Auto-scraping               - Search books
  - API Server (8080)           - Admin controls
       ↓                              ↓
    Database (SQLite) ←───────→ HTTP Requests
       ↓                              ↓
  poin_hijau.json              books.db
```

### Data Flow:
1. **Bot Discord** menangani perintah users dan scraping
2. **API Server** (localhost:8080) menyediakan endpoint untuk website
3. **Website Flask** sebagai interface untuk kontrol bot dan melihat data
4. **Database SQLite** menyimpan data buku

---

## 📁 Struktur File

```
Project_VII/
├── BOT.py                    # Main bot Discord dengan API server
├── Brain.py                  # AI image classification module (TensorFlow/Keras)
├── database.py               # SQLite database module untuk buku
├── migrate_json_to_sqlite.py # Script migrasi data buku dari JSON ke SQLite
├── website/
│   ├── app.py               # Flask web application
│   ├── templates/           # HTML templates
│   │   ├── base.html
│   │   ├── home.html
│   │   ├── function.html
│   │   ├── chat.html
│   │   ├── leaderboard.html
│   │   ├── books.html
│   │   ├── search_books.html
│   │   └── search_results.html
│   └── static/
│       └── style.css
├── poin_hijau.json          # Database poin users (JSON)
├── books.db                 # Database SQLite untuk koleksi buku
├── database_buku_log.json.backup # Backup database buku lama (setelah migrasi)
├── .env                     # Environment variables (DISCORD_TOKEN)
├── keras_model.h5           # AI model untuk klasifikasi gambar
├── labels.txt               # Label classification AI
└── requirements.txt         # Python dependencies
```

---

## 🎯 Tips Penggunaan

### Untuk Admin/Pengembang:
- Gunakan `$TrueAdminBookDescription` untuk mengisi database buku awal
- Website dashboard bisa kontrol bot tanpa perlu Discord
- Auto-scraping otomatis tambah buku baru setiap 12 jam
- API internal hanya akses dari localhost (secure)

### Untuk Users:
- Dapatkan poin dengan melakukan aksi hijau
- Gunakan `$Books` untuk rekomendasi buku (cooldown 30 menit)
- Cek leaderboard untuk kompetisi ramah lingkungan
- Ikuti event eksklusif untuk poin ekstra

---

## 🐛 Troubleshooting

### Bot tidak bisa login:
- Cek DNS: Buka https://discord.com di browser
- Ganti DNS ke 8.8.8.8 atau 1.1.1.1
- Matikan VPN/hotspot yang blokir Discord

### Website tidak bisa akses API:
- Pastikan BOT.py sudah berjalan (API server di port 8080)
- Cek firewall tidak blokir localhost:8080

### Scraping gagal:
- Cek koneksi internet
- Website target (books.toscrape.com) mungkin down
- Coba lagi nanti atau kurangi jumlah buku

---

## 📝 Credits

Dibuat oleh anak kelas 7 SMP (13 tahun) dengan ilmu:
- Web Scraping (BeautifulSoup)
- Database (JSON & SQLite)
- Bot Discord (discord.py)
- API Internal (aiohttp)
- Web Dashboard (Flask + Chart.js)
- Real-time Communication (Flask-SocketIO)
- AI/ML (TensorFlow/Keras - Image Classification)
- AI Generative (Google Gemini 2.5 Flash)
- Discord OAuth2 Authentication
- Environment Variables (python-dotenv)
- Gamifikasi & Interaksi
- CSS 3D Effects & Dark Mode
- HTML/CSS/JavaScript

🌿 **Bot/AI Zenn' VII** - Membangun masa depan hijau dengan teknologi!
