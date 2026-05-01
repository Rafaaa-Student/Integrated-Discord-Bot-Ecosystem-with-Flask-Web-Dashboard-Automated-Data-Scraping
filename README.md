# Zenn' VII 🌿🤖

Halo, nama saya Raffasya Azka Al-Farabi, saya adalah anak kelas 7 SMP di SMP AL Kautsar Bandar Lampung. Saya adalah pembuat proyek mandiri ini.
Saya membuat proyek ini dengan tujuan untuk mengedukasi anak-anak untuk bisa menjaga lingkungan dan menjadi pribadi yang lebih baik. 
Saya menggabungkan beberapa teknologi seperti AI, Discord Bot, dan Website khusus untuk membuat proyek ini.

Bot Discord interaktif yang menggabungkan **gamifikasi aksi hijau**, **web scraping**, dan **dashboard website** untuk mendorong gaya hidup ramah lingkungan.

---

## 📋 Fitur Utama

### 💰 Sistem Ekonomi & Gamifikasi (Dual-Currency)
Proyek ini menggunakan sistem ekonomi RPG untuk memotivasi interaksi:

- **XP (Reputation)**: Poin permanen yang menentukan Level dan Badge. Tidak bisa berkurang.
- **Gold (Currency)**: Mata uang yang bisa dibelanjakan di `$Shop` untuk membeli item atau bermain `$Gacha`.
- **$Poin**: Cek saldo Gold dan akumulasi XP kamu.
- **$Shop**: Lihat daftar item, badge eksklusif, atau booster AI yang bisa dibeli.
- **$Buy <item>**: Beli item menggunakan Gold.
- **$Gacha**: Gunakan Gold untuk mendapatkan item random (Booster, Badge, atau ampas).
- **$Select <badge>**: Gunakan badge yang sudah dibeli dari inventory untuk ditampilkan di profil.

### 🌱 Fitur Aksi Hijau (Green Action System)
Bot ini dirancang untuk memotivasi pengguna melakukan tindakan ramah lingkungan:

- **$Green_Action**: Tips hijau harian + Gold & XP (max 3x sehari)
- **$Action <aksi>**: Catat aksi hijau (misal: "Menanam pohon") + Gold & XP
- **$Story <cerita>**: Cerita storytelling 30+ kata tentang aktivitas hijau (bonus Gold & XP sesuai deteksi AI)
- **$Bug <laporan>**: (Khusus Admin Server) Laporkan bug/error langsung ke Project Admin untuk dilihat di dashboard website.
- **$Leaderboard**: Ranking top 5 pengguna dengan XP (Reputation) tertinggi.

### 🌐 Fitur Web Scraping & Data Mining 
Bot ini juga dapat melakukan web scraping dan data mining untuk mendapatkan informasi terkini tentang lingkungan dan sains.

- **Explore <topik>**: Cari artikel dari Wikipedia Indonesia dan ringkas dengan AI untuk mendapatkan informasi cepat.
- **$FindBooks <judul>**: Pencarian buku lanjutan dengan filter kategori dan hasil yang lebih detail.
- **$BookDescription <judul>**: Dapatkan rekomendasi buku random dari database untuk dibaca.
- **$Books**: Cari buku dari database dengan pencarian berdasarkan judul, penulis, atau ISBN.
- **$Quotes**: Dapatkan kutipan inspiratif dari internet.

### 🤖 Fitur AI Generative
AI powered by **Google Gemini 2.0 Flash Lite** untuk interaksi cerdas:

- **$Zenn <pertanyaan>**: Tanya ke AI Zenn VII tentang lingkungan, sains, atau umum. (Limit: 10/menit per guild untuk user biasa, unlimited admin).
- **Stardust Connect**: Visualisasi jaringan pikiran AI di website (Vis.js) dengan tema hutan yang adaptif.
- **Booster AI**: Gunakan Gold untuk membeli booster yang meningkatkan limit penggunaan AI harian.

### 🌐 Fitur Website Dashboard
Dashboard interaktif dengan desain premium untuk memantau data bot:

- **Adaptive UI Design**: 
  - **Minimalist Light Mode**: Tema bersih dan cerah yang menyatu dengan alam.
  - **Futuristic Dark Mode**: Tema Sci-Fi dengan Glassmorphism, background bintang parallax, dan efek tata surya.
- **Global Visual Effects**: 
  - **Background Stars**: Bintik-bintik putih yang berkelap-kelip dan bergerak (parallax) di semua halaman (Dark Mode).
  - **Magical Stardust Trail**: Efek partikel bintang yang mengikuti kursor mouse dengan animasi halus.
- **Discord OAuth2 Login**: Login aman menggunakan akun Discord kamu.
- **Profile & Achievement**: Lihat kartu pencapaian, saldo XP/Gold, dan pilih badge yang ingin dipamerkan.
- **Leaderboard**: Ranking XP (Reputation) global.
- **Chemical (Periodic Table)**: Tabel periodik interaktif dengan informasi asal-usul unsur (Big Bang, Supernova, dll) dan efek Stardust Connect.
- **Books & Search**: Jelajahi koleksi buku hasil scraping dengan UI yang modern.
- **Admin Dashboard**: Melihat laporan bug dari user, manajemen AI usage, dan kontrol bot lainnya.
- **Real-time Updates**: Integrasi SocketIO untuk sinkronisasi data instan antara bot dan website.

### 🔌 Sistem API Internal
Bot menjalankan API server internal di `localhost:8080` untuk terintegrasi dengan website:

- **/send_message**: Kirim pesan ke channel Discord dari website
- **/trigger_scraping**: Trigger scraping buku dari website
- **/trigger_event**: Buat event baru dari website
- Website Flask sebagai client yang mengontrol bot Discord secara real-time

---

## 📊 Sistem Level & Badge (XP vs Gold)

Proyek ini memisahkan antara reputasi (XP) dan daya beli (Gold):

| Level | Badge | XP Required | Deskripsi |
|-------|-------|-------------|-----------|
| 1 | 🌱 Newbie | 0 | Awal perjalanan hijau. |
| 10 | 🌿 Green Explorer | 100 | Mulai konsisten beraksi. |
| 30 | 🌲 Eco Enthusiast | 500 | Menjadi inspirasi lingkungan. |
| 50 | 🌍 Environmental Hero | 1000 | Pahlawan bumi sejati. |
| 100 | 🏆 Legendary Champion | 5000 | Legenda konservasi alam. |

- **XP**: Didapat dari `$Green_Action`, `$Action`, dan `$Story`. Digunakan untuk naik level.
- **Gold**: Didapat bersamaan dengan XP. Digunakan untuk belanja di `$Shop` atau main `$Gacha`.

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
4. **Database SQLite** menyimpan data buku, percakapan AI, dan event eksklusif

### Database Schema (SQLite):
- **books**: Koleksi buku hasil scraping (judul, harga, deskripsi, url).
- **ai_usage**: Tracking limit penggunaan AI per user dan guild.
- **bug_reports**: Laporan error dari user via command `$Bug`.
- **inventory**: Menyimpan item dan badge yang sudah dibeli oleh user.
- **ai_boosts**: Status booster AI yang aktif untuk menambah limit harian.
- **selected_badge**: Badge yang sedang aktif dipakai oleh user untuk profil.

---

## 📁 Struktur File

```
Project_VII/
├── BOT.py                    # Main bot Discord & API Server (8080)
├── Brain.py                  # Modul AI Gemini & Pembersihan Teks
├── database.py               # Definisi tabel SQLite & Database Manager
├── poin_hijau.json          # Database ekonomi (XP & Gold) - format JSON
├── books.db                 # Database utama SQLite (Buku, Bug, Inventory, dll)
├── website/
│   ├── app.py               # Flask Web Application (5000)
│   ├── templates/           # UI Premium (Adaptive Themes)
│   │   ├── base.html        # Global Stars & Cursor Trail
│   │   ├── home.html        # Dashboard Stats
│   │   ├── profile.html     # Achievement Card & Inventory
│   │   ├── chemical.html    # Periodic Table & Stardust Connect
│   │   ├── function.html    # Vis.js AI Visualization
│   │   └── ...              # Halaman pendukung lainnya
│   └── static/
│       └── style.css        # Styling Global & Glassmorphism
```

---

## 🎯 Tips Penggunaan

### Untuk Admin/Pengembang:
- Gunakan `$TrueAdminBookDescription` untuk mengisi database buku awal
- Website dashboard bisa kontrol bot tanpa perlu Discord
- Auto-scraping otomatis tambah buku baru setiap 12 jam
- API internal hanya akses dari localhost (secure)
- Gunakan `$Claim_Exclusive` untuk event berbasis gambar dengan validasi AI (first-come-first-served)

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
- **AI Generative**: Google Gemini 2.0 Flash Lite Integration.
- **Visual & UI**: Premium Adaptive Theme (Light/Dark), Glassmorphism, CSS Particles.
- **Interactive JS**: Vis.js for AI visualization & Stardust Connect.
- **Economy Engine**: Dual-Currency System (XP & Gold) via JSON.
- **Backend**: Flask (Python) with SocketIO real-time sync.
- **Bot Engine**: Discord.py with internal API server (aiohttp).
- **Database**: Advanced SQLite management (Inventory, Bug Reporting, etc).
- **Security**: Discord OAuth2 & Environment Variables.

🌿 **Bot/AI Zenn' VII** - Membangun masa depan hijau dengan teknologi!
