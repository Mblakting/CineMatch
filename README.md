# 🎬 CineMatch

**CineMatch** adalah aplikasi rekomendasi film real-time berbasis Streamlit yang mengambil data langsung dari TMDB dan menyajikan rekomendasi personal dengan model perankingan yang dapat beradaptasi dari umpan balik pengguna.

[Live Demo](https://cinematch-rekomendasi.streamlit.app/) • [Repository](https://github.com/Mblakting/CineMatch)

---

## ✨ Ringkasan

CineMatch menghasilkan rekomendasi film yang relevan dengan cara:

- Menarik data langsung dari TMDB tanpa dataset lokal.
- Mengumpulkan kandidat dari berbagai sumber: rekomendasi TMDB, film serupa, discovery, dan pencarian franchise/kata kunci.
- Menghitung fitur interpretable seperti genre, keyword, cerita, pemeran/sutradara, kualitas rating, era rilis, dan franchise.
- Menggabungkan fitur ini ke dalam skor rekomendasi yang transparan.
- Memperbarui bobot rekomendasi berdasarkan feedback `👍 Suka` dan `👎 Tidak Cocok` selama sesi Streamlit.

---

## 🚀 Fitur Utama

- **Pencarian film cepat** berdasarkan judul.
- **Tampilan detail film lengkap**: sinopsis, genre, rating, runtime, poster, dan trailer.
- **Rekomendasi film live** yang diambil langsung dari TMDB.
- **Model ranking AI yang dapat dijelaskan** (interpretable scoring).
- **Online learning**: adaptasi bobot berdasarkan feedback pengguna dalam sesi yang sama.
- **Watchlist sederhana** untuk menyimpan film favorit selama sesi.

---

## 🧠 Bagaimana CineMatch Bekerja

### Alur Utama

- `src/main.py` mengatur antarmuka Streamlit, mengambil data dari TMDB, dan menampilkan rekomendasi.
- `src/engines/realtime_ai_engine.py` membangun profil film, mengekstrak fitur, dan menghitung skor rekomendasi.
- `src/core/config.py` menyimpan konfigurasi UI, parameter rekomendasi, dan API key.

### Mesin Rekomendasi

Setiap kandidat dievaluasi terhadap film sumber atau profil selera pengguna menggunakan fitur berikut:

- `tmdb_signal` (popularitas / bobot sumber)
- `genre_match` (kesamaan genre)
- `keyword_match` (kesamaan kata kunci)
- `story_match` (kesamaan cerita menggunakan TF-IDF + cosine similarity)
- `people_match` (kesamaan pemeran / sutradara)
- `quality` (rating dan kepercayaan vote)
- `era_match` (kedekatan tahun rilis)
- `franchise_match` (film dalam franchise atau seri yang sama)

Bobot dasar rekomendasi disesuaikan secara dinamis oleh fungsi `learned_weights()` berdasarkan feedback pengguna.

---

## 💻 Instalasi Lokal

1. Clone repository:

```bash
git clone https://github.com/Mblakting/CineMatch.git
cd CineMatch
```

2. Buat virtual environment dan aktifkan:

```bash
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

3. Install dependency:

```bash
pip install -r requirements.txt
```

4. Set environment variable `TMDB_API_KEY`:

Windows (PowerShell):

```powershell
setx TMDB_API_KEY "your_tmdb_api_key"
```

Mac/Linux:

```bash
export TMDB_API_KEY="your_tmdb_api_key"
```

5. Jalankan aplikasi:

```bash
python -m streamlit run src/main.py
```

6. Buka browser ke http://localhost:8501.

> Jika `TMDB_API_KEY` tidak diatur, aplikasi akan fallback ke nilai default di `src/core/config.py`. Untuk penggunaan produksi, selalu gunakan environment variable.

---

## 📂 Struktur Proyek

```
CineMatch/
├── src/
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   └── engines/
│       └── realtime_ai_engine.py
├── requirements.txt
└── README.md
```

---

## 🔒 Keamanan

- Jangan menyimpan kunci TMDB ke dalam repository.
- Gunakan environment variable `TMDB_API_KEY` saat deploy.
- Aplikasi tidak menyimpan data pengguna secara persisten.

---

## 🤝 Kontribusi

1. Fork repository.
2. Buat branch fitur baru.
3. Commit perubahan.
4. Push ke remote.
5. Buat Pull Request.

Jika menambahkan penyimpanan persistensi, sertakan dokumentasi konfigurasi dan migrasi.

---

## 📜 Lisensi

MIT License

---

## 📌 Demo

https://cinematch-rekomendasi.streamlit.app/
