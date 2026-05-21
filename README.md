# CineMatch

CineMatch adalah aplikasi web rekomendasi film realtime berbasis Streamlit
yang mengambil data film langsung dari TMDB dan memberi peringkat kandidat
menggunakan model peringkat custom yang dibuat di dalam proyek.

Demo live: https://cinematch-rekomendasi.streamlit.app/
Repo: https://github.com/Mblakting/CineMatch

---

## Ringkasan singkat (untuk dosen / penguji)

- Mengambil data film secara realtime dari TMDB (no local dataset).
- Mengumpulkan kandidat dari endpoints TMDB (recommendations, similar,
  discovery, search by keywords/franchise).
- Mengekstrak fitur film (genre, keywords, story/overview, people, quality,
  era, franchise) dan menghitung kesamaan menggunakan metrik interpretable
  (Jaccard, token overlap, TF-IDF cosine, heuristics).
- Peringkat akhir dibuat dari kombinasi bobot fitur (base weights) yang dapat
  disesuaikan secara online selama sesi dari feedback pengguna (👍 / 👎).

Kode utama:
- UI & integrasi TMDB: `src/main.py`
- Konfigurasi: `src/core/config.py`
- Engine peringkat / taste model: `src/engines/realtime_ai_engine.py`

---

## Cara menjalankan secara lokal (untuk penguji)

Persyaratan: Python 3.10 atau lebih baru.

1. Clone repo dan masuk folder:

```bash
git clone https://github.com/Mblakting/CineMatch.git
cd CineMatch
```

2. (Disarankan) buat virtualenv dan aktifkan.

3. Install dependency:

```bash
pip install -r requirements.txt
```

4. (Opsional) tambahkan API key TMDB milik Anda. Jika tidak, aplikasi akan
   menggunakan API key yang ada di `src/core/config.py` (untuk keperluan tugas).

Windows (PowerShell):
```powershell
setx TMDB_API_KEY "your_api_key_here"
```

5. Jalankan aplikasi:

```bash
python -m streamlit run src/main.py
```

6. Buka browser ke alamat yang ditampilkan oleh Streamlit (mis. http://localhost:8501).

---

## Cara menggunakan (untuk orang awam)

1. Ketik judul film yang Anda suka di kotak pencarian (mis. "Inception").
2. Aplikasi akan menampilkan detail film dan daftar rekomendasi mirip.
3. Jika Anda suka rekomendasi, klik tombol "👍 Suka"; jika tidak cocok, klik
   "👎 Tidak Cocok". Pilihan ini membantu CineMatch menyesuaikan rekomendasi
   selama sesi Anda.
4. Untuk menyimpan film agar tidak lupa, klik "❤️ Simpan ke Tontonan" (watchlist).
5. Setelah memberi tanda suka pada minimal 2 film, Anda bisa menekan tombol
   "🎯 Rekomendasikan Film untuk Saya!" di sidebar untuk rekomendasi personal.

Catatan: semua pembelajaran terjadi hanya selama sesi Streamlit saat itu—jika
halaman direfresh, data feedback tidak persist.

---

## Penjelasan teknis singkat (untuk dokumentasi tugas)

- Fitur yang dihitung per kandidat: `tmdb_signal` (popularitas dari pool),
  `genre_match` (Jaccard pada genre IDs), `keyword_match` (overlap token),
  `story_match` (cosine similarity TF-IDF pada token cerita/overview),
  `people_match` (overlap aktor/sutradara), `quality` (fungsi rating + vote
  confidence), `era_match` (kedekatan tahun rilis), `franchise_match`.
- Base weights default disimpan di engine; bobot ini dapat diupdate tiap kali
  pengguna memberikan feedback lewat fungsi `learned_weights()`.
- Fungsi penjelasan hasil rekomendasi: `explain_recommendation()` — menghasilkan
  alasan yang mudah dibaca untuk tiap rekomendasi.

Referensi file:
- UI & alur: [src/main.py](src/main.py#L1)
- Engine dan model: [src/engines/realtime_ai_engine.py](src/engines/realtime_ai_engine.py#L1)
- Konfigurasi API: [src/core/config.py](src/core/config.py#L1)

---

## Catatan keamanan & pengembangan

- Saat ini ada `API_KEY` default di `src/core/config.py`. Untuk deployment
  publik sebaiknya gunakan environment variable `TMDB_API_KEY` dan hapus/acak
  value default agar tidak mengekspos kunci.
- Aplikasi tidak menyimpan data ke database—semua feedback hanya tersimpan di
  `st.session_state` selama sesi. Untuk menyimpan preferensi antar sesi,
  tambahkan persistence (SQLite / file JSON / remote DB).

---

## Kelebihan & keterbatasan (untuk presentasi tugas)

- Kelebihan:
  - Interaksi realtime dengan TMDB (tidak perlu dataset lokal).
  - Model peringkat interpretable dengan penjelasan rekomendasi.
  - Online learning sederhana dari feedback pengguna.

- Keterbatasan:
  - Tidak ada persistensi antar sesi.
  - Bergantung pada ketersediaan & rate-limit TMDB.
  - Bukan model deep-learning pre-trained; ini heuristik klasik + TF-IDF.

---

## Checklist pengumpulan tugas (saran)

- [x] Kode bersih & terstruktur di `src/`.
- [x] Demo live: https://cinematch-rekomendasi.streamlit.app/
- [x] Instruksi jalankan lokal tercantum di atas.
- [ ] (Opsional) Hapus API key default sebelum publikasi final.
- [ ] (Opsional) Tambahkan screenshot / video singkat antarmuka untuk lampiran.

---

Jika Anda ingin, saya bisa:
- menambahkan screenshot dan contoh penggunaan lengkap untuk lampiran tugas, atau
- membuat file `SUBMISSION.md` singkat untuk bahan presentasi.

Terakhir: tidak ada fungsi dalam kode yang saya ubah—README ini hanya dokumentasi.
