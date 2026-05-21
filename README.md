# CineMatch

CineMatch adalah aplikasi web rekomendasi film yang memberikan rekomendasi
personal secara real-time dengan mengambil data film dari TMDB dan
memeringkatnya menggunakan model peringkat internal yang dapat disesuaikan.

Untuk menggunakan aplikasi, cukup kunjungi:
https://cinematch-rekomendasi.streamlit.app/

## Ringkasan singkat

CineMatch menyediakan pengalaman rekomendasi film interaktif yang:

- Mengambil data film secara langsung dari The Movie Database (TMDB) — tidak
	membutuhkan dataset lokal.
- Mengumpulkan kandidat dari berbagai endpoint TMDB (recommendations, similar,
	discovery, dan pencarian kata kunci/franchise) dan memperkaya detail film
	(keywords, credits, videos) saat diperlukan.
- Menghitung fitur interpretable (genre, kata kunci, kesamaan cerita/overview,
	kesamaan pemeran/sutradara, kualitas rating, kedekatan era, sinyal popularitas,
	dan kecocokan franchise) lalu menggabungkannya dengan bobot untuk memberi
	skor akhir rekomendasi.
- Menerapkan learning sederhana secara online: umpan balik pengguna (👍/👎)
	mempengaruhi bobot perankingan selama sesi Streamlit berjalan.

## Demo

Demo publik dan cara termudah untuk mencoba CineMatch:

https://cinematch-rekomendasi.streamlit.app/

## Fitur Utama

- Pencarian film cepat (query judul) dan tampilan detail film lengkap.
- Pengumpulan kandidat real-time dari TMDB (rekomendasi, similar, discover).
- Model peringkat interpretable yang menggabungkan beberapa sinyal fitur.
- Umpan balik interaktif: pengguna dapat menandai film `Suka` atau `Tidak Cocok`.
- Rekomendasi berbasis selera (taste-based) setelah pengguna memberi beberapa
	tanda suka.

## Cara Kerja (singkat, teknis)

- Alur utama berada di [src/main.py](src/main.py#L1). Aplikasi mengambil data
	dari TMDB lewat helper `fetch_api()` dan membangun pool kandidat dengan
	`collect_live_candidates()` / `collect_taste_candidates()`.
- Logika perankingan dan konstruksi fitur ada di
	[src/engines/realtime_ai_engine.py](src/engines/realtime_ai_engine.py#L1).
	- Fitur yang dihitung meliputi: `tmdb_signal`, `genre_match`, `keyword_match`,
		`story_match` (cosine TF‑IDF), `people_match`, `quality`, `era_match`, dan
		`franchise_match`.
	- Bobot dasar didefinisikan sebagai `BASE_WEIGHTS` dan dapat diupdate secara
		iteratif dari sampel feedback selama sesi melalui metode `learned_weights()`.
- Konfigurasi API dan UI tersentral di
	[src/core/config.py](src/core/config.py#L1) (termasuk `TMDB_API_KEY` default
	yang saat ini diisi langsung — lihat bagian keamanan di bawah).

## Quickstart — Jalankan Secara Lokal

Langkah singkat untuk menjalankan aplikasi pada mesin pengembang:

1. (Opsional) Buat virtual environment dan aktifkan.
2. Install dependency:

```bash
pip install -r requirements.txt
```

3. Set environment variable `TMDB_API_KEY` (rekomendasi):

Windows (PowerShell):
```powershell
setx TMDB_API_KEY "your_api_key_here"
```

4. Jalankan Streamlit:

```bash
python -m streamlit run src/main.py
```

Catatan: jika `TMDB_API_KEY` tidak diset, aplikasi akan menggunakan nilai
default yang ada di [src/core/config.py](src/core/config.py#L1). Untuk
publikasi/produksi, jangan gunakan API key default tersebut.

## Contoh Penggunaan

- Ketik judul film favorit pada kotak pencarian untuk melihat detail dan
	daftar rekomendasi.
- Klik `👍 Suka` atau `👎 Tidak Cocok` pada tiap rekomendasi untuk memberikan
	feedback; setelah beberapa feedback, aktifkan `🎯 Rekomendasikan Film untuk Saya!`
	untuk rekomendasi berbasis selera.
- Gunakan `❤️ Simpan ke Tontonan` untuk membuat watchlist sederhana per-sesi.

## Struktur Kode (ringkas)

- `src/main.py`: UI Streamlit, integrasi TMDB, pengumpulan kandidat, dan
	interaksi pengguna. ([buka file](src/main.py#L1))
- `src/engines/realtime_ai_engine.py`: pembuatan fitur, model perankingan,
	logika online learning ringan, dan utility teks (tokenize, idf, cosine).
	([buka file](src/engines/realtime_ai_engine.py#L1))
- `src/core/config.py`: konfigurasi aplikasi (API key, UI defaults, dan
	parameter rekomendasi). ([buka file](src/core/config.py#L1))

## Pengembangan & Kontribusi

- Untuk fitur baru, jalankan aplikasi lokal seperti bagian Quickstart di atas
	dan kerjakan cabang (branch) terpisah.
- Ikuti praktik pengembangan Python standar: gunakan virtualenv, jalankan
	perubahan kecil, dan uji interaksi Streamlit secara manual.
- Jika Anda ingin menambahkan persistensi (mis. SQLite atau remote DB),
	perhatikan bahwa saat ini semua feedback disimpan hanya di `st.session_state`.

## Keamanan & Privasi

- Hati‑hati dengan `TMDB_API_KEY`: saat ini repo memiliki nilai default di
	[src/core/config.py](src/core/config.py#L1). Untuk rilis publik atau
	kolaborasi, pindahkan kunci ke environment variable `TMDB_API_KEY` dan hapus
	nilai default dari kode.
- Aplikasi tidak menyimpan data pengguna ke disk atau DB; semua feedback
	hanya bertahan selama sesi Streamlit berjalan.

## Penjelasan Rekomendasi (singkat)

- Sistem menghitung beberapa fitur yang mudah dijelaskan dari metadata
	TMDB (genre, keywords, overview, credits).
- Fitur dikombinasikan dengan bobot dasar untuk menghasilkan `ai_score`.
- Jika pengguna memberi feedback, bobot disesuaikan secara online sehingga
	rekomendasi berikutnya lebih mencerminkan preferensi saat itu.

## Lisensi & Kredit

- Pembuat: Rahmadtzy • 2026
- Lisensi: sesuaikan dengan kebutuhan Anda (file lisensi terpisah jika
	diperlukan).

---

Jika Anda mau, saya bisa:

- Menyempurnakan bagian “Penjelasan Rekomendasi” dengan contoh konkret dari
	keluaran model (contoh `ai_score` + reasons), atau
- Menambahkan `CONTRIBUTING.md` dan `SECURITY.md` singkat untuk panduan
	kolaborator.

Beritahu saya bagian mana yang ingin Anda perkuat atau jika mau langsung saya
commit perubahan ini ke README di repo.

