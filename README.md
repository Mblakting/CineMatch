🎬 CineMatch: Real-Time Personalized Movie Recommender

CineMatch memberikan rekomendasi film personal secara real-time dengan mengambil data dari TMDB dan memeringkatnya menggunakan model kecerdasan buatan (AI) internal yang beradaptasi dengan selera Anda saat itu juga.

🚀 Coba Demo Live CineMatch di Sini!

✨ Fitur Utama

Pencarian & Detail Instan: Cari film berdasarkan judul dan langsung dapatkan detail lengkapnya (sinopsis, genre, pemeran, hingga cuplikan video).

Pengumpulan Kandidat Dinamis (No Local Dataset): Mengambil data film secara langsung dari The Movie Database (TMDB) melalui berbagai endpoint (recommendations, similar, discovery, dan keyword search). Aplikasi selalu mendapatkan data terbaru tanpa perlu menyimpan dataset film berukuran besar di server.

Interpretable AI Ranking Engine: Menggunakan model perankingan internal yang transparan. Fitur dihitung berdasarkan kecocokan genre, kata kunci, kesamaan cerita (menggunakan TF‑IDF dan Cosine Similarity), kesamaan pemeran/sutradara, kualitas rating, kedekatan era rilis, dan kecocokan franchise.

Online Learning & Interactive Feedback: Sistem belajar dari Anda! Berikan umpan balik 👍 Suka atau 👎 Tidak Cocok pada film. Model akan menyesuaikan bobot perankingan secara iteratif selama sesi Streamlit berjalan, sehingga rekomendasi berikutnya lebih akurat.

Watchlist Personal: Simpan film yang menarik perhatian Anda ke dalam daftar tontonan (Watchlist) sederhana selama sesi aktif.

🛠️ Cara Kerja (Technical Overview)

Alur Utama (src/main.py): Aplikasi berinteraksi dengan API TMDB menggunakan fungsi pembantu fetch_api(). Ketika pengguna mencari film atau meminta rekomendasi, sistem membangun pool kandidat melalui collect_live_candidates() atau collect_taste_candidates().

Ekstraksi Fitur & Logika Perankingan (src/engines/realtime_ai_engine.py):

Setiap kandidat dinilai terhadap film target atau profil pengguna berdasarkan fitur: tmdb_signal, genre_match, keyword_match, story_match, people_match, quality, era_match, dan franchise_match.

Setiap fitur dikalikan dengan bobot dasar (BASE_WEIGHTS).

Adaptasi Bobot (Online Learning): Saat pengguna memberikan feedback, fungsi learned_weights() dipanggil untuk memperbarui bobot secara real-time. Sinyal yang sering disukai akan mendapatkan bobot lebih tinggi.

🚀 Quickstart (Panduan Instalasi Lokal)

Ingin menjalankan atau mengembangkan CineMatch di mesin lokal Anda? Ikuti langkah-langkah berikut:

1. Kloning Repositori

git clone [https://github.com/Mblakting/CineMatch.git](https://github.com/Mblakting/CineMatch.git)
cd CineMatch


2. Buat Virtual Environment (Sangat Direkomendasikan)

python -m venv venv

# Aktivasi di Windows:
venv\Scripts\activate
# Aktivasi di Mac/Linux:
source venv/bin/activate


3. Instalasi Dependensi

pip install -r requirements.txt


4. Konfigurasi Environment Variables

Aplikasi ini membutuhkan API Key dari TMDB. Buat environment variable TMDB_API_KEY di terminal Anda:

Windows (PowerShell):

$env:TMDB_API_KEY="masukkan_api_key_tmdb_anda_di_sini"


Mac/Linux:

export TMDB_API_KEY="masukkan_api_key_tmdb_anda_di_sini"


(Catatan: Jika variabel ini tidak diatur, aplikasi akan menggunakan key default dari src/core/config.py. Jangan gunakan key default untuk environment produksi).

5. Jalankan Aplikasi Streamlit

python -m streamlit run src/main.py


Aplikasi akan berjalan dan otomatis terbuka di browser Anda pada alamat http://localhost:8501.

📂 Struktur Proyek Singkat

CineMatch/
├── src/
│   ├── main.py                          # UI Streamlit, integrasi API, & interaksi pengguna
│   ├── core/
│   │   └── config.py                    # Sentralisasi konfigurasi & default settings
│   └── engines/
│       └── realtime_ai_engine.py        # Ekstraksi fitur teks, logika TF-IDF, & ranking model
├── requirements.txt                     # Kumpulan pustaka Python
└── README.md                            # Dokumentasi Proyek


🛡️ Keamanan & Privasi

API Key Management: Untuk deployment publik, sangat disarankan untuk menghapus nilai default TMDB_API_KEY dari src/core/config.py dan menggunakan fitur manajemen rahasia dari platform hosting (seperti Streamlit Secrets).

Privasi Pengguna: CineMatch adalah aplikasi stateless dalam hal penyimpanan persisten. Aplikasi tidak menyimpan data pengguna, riwayat pencarian, atau feedback ke dalam database atau disk. Semua data interaksi hanya disimpan sementara di dalam st.session_state dan akan hilang ketika tab/sesi ditutup.

🤝 Pengembangan & Kontribusi

Kami menyambut kontribusi untuk membuat CineMatch lebih baik!

Lakukan Fork pada repositori ini.

Buat branch fitur Anda (git checkout -b fitur-baru-saya).

Lakukan commit pada perubahan Anda (git commit -m 'Menambahkan fitur XYZ').

Push ke branch tersebut (git push origin fitur-baru-saya).

Buka Pull Request (PR) di repositori utama.

Jika Anda berencana menambahkan fitur persistensi data (misal: SQLite, PostgreSQL, atau Firebase), pastikan untuk menambahkan dokumentasi migrasi database yang sesuai.

📜 Lisensi & Kredit

Pembuat: Rahmadtzy • 2026

Sumber Data: Produk ini menggunakan API TMDb namun tidak didukung atau disertifikasi oleh TMDb.

Lisensi: MIT License