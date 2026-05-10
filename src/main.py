# -*- coding: utf-8 -*-
"""
CineMatch
Realtime movie recommendations with a custom online-learning ranker.
"""

from __future__ import annotations

import random
import re
from html import escape

import requests
import streamlit as st

from src.core.config import API_KEY, RECOMMENDATION_CONFIG, UI_CONFIG
from src.engines.realtime_ai_engine import (
    RealtimeMovieAI,
    TasteProfile,
    build_taste_profile,
    explain_recommendation,
    extract_genres,
    safe_float,
)


LIVE_CACHE_TTL = RECOMMENDATION_CONFIG["live_cache_ttl"]
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE = "https://image.tmdb.org/t/p/original"


st.set_page_config(
    page_title=UI_CONFIG["app_title"],
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "Gelap"

st.markdown("""
<style>
body, .stApp { background: #0f172a !important; color: #e2e8f0 !important; }
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important; }
.stSidebar { background: #111827 !important; }
.stButton>button { border-radius: 8px !important; font-weight: 600 !important; font-size: 0.85rem !important; }

/* ── Layout utama ── */
.block-container { background: transparent !important; padding: 4rem 1rem 2rem !important; max-width: 1200px; }
/* Kurangi gap default antar elemen */
.stVerticalBlock > div { margin-bottom: 0 !important; }
/* Beri jarak yang cukup antara elemen */
[data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }

/* ── Header Streamlit ── */
header[data-testid="stHeader"] {
    background: #0f172a !important;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}
/* Sembunyikan semua konten header kecuali tombol sidebar */
header[data-testid="stHeader"] > div > div:not(:has([data-testid*="Sidebar"])) {
    visibility: hidden !important;
}
/* Semua tombol di header dan sidebar header — sembunyikan teks, tampilkan emoji */
[data-testid="stSidebarCollapseButton"] button,
header[data-testid="stHeader"] button {
    text-indent: -9999px !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    position: relative !important;
    background: #1e293b !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 8px !important;
    min-width: 2rem !important;
    min-height: 2rem !important;
}
[data-testid="stSidebarCollapseButton"] button::before,
header[data-testid="stHeader"] button::before {
    content: "☰" !important;
    text-indent: 0 !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1rem !important;
    color: #e2e8f0 !important;
    pointer-events: none !important;
}
/* Padding top konten — cukup besar agar tidak tertutup header */

.hero-banner {
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    height: 300px;
    margin-bottom: 1rem;
    display: block;
}
.hero-banner img {
    width: 100%; height: 100%;
    object-fit: cover; object-position: center 30%;
    display: block;
    position: absolute; inset: 0;
}
.hero-banner-fallback {
    background: linear-gradient(135deg, #1a1f2e 0%, #0f172a 100%);
    display: flex; align-items: center;
    padding: 2rem;
    height: auto !important;
    min-height: 160px;
}
.hero-banner-overlay {
    position: absolute; inset: 0;
    background: linear-gradient(to right, rgba(0,0,0,0.85) 50%, rgba(0,0,0,0.1) 100%);
    display: flex; align-items: center;
    padding: 1.5rem 2rem;
    z-index: 1;
}
.hero-title { font-size: 1.9rem; font-weight: 800; color: #fff; margin: 0 0 6px; line-height: 1.2; }
.hero-meta { font-size: 0.85rem; color: #94a3b8; margin: 0 0 8px; }
.hero-overview { font-size: 0.85rem; color: #cbd5e1; line-height: 1.6; max-width: 520px;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.hero-badge { display: inline-block; background: rgba(229,9,20,0.85); color: #fff;
    border-radius: 4px; padding: 3px 10px; font-size: 0.72rem; font-weight: 700;
    margin-bottom: 8px; letter-spacing: 0.5px; }

.stat-row { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.5rem 0 0.75rem; }
.stat-item { background: #1e293b; border-radius: 8px; padding: 6px 12px; text-align: center; min-width: 70px; }
.stat-label { font-size: 0.65rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { font-size: 0.95rem; font-weight: 700; color: #e2e8f0; }

.movie-card {
    background: #1a1f2e;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 100%;
}
.movie-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(229,9,20,0.12); }
.poster-wrap { position: relative; width: 100%; height: 200px; overflow: hidden; }
.poster-wrap img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.poster-grad {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.92) 0%, transparent 65%);
    padding: 10px 8px 6px;
}
.poster-title { font-size: 0.8rem; font-weight: 700; color: #fff; margin: 0; line-height: 1.2; }
.poster-rating { font-size: 0.7rem; color: #fbbf24; font-weight: 600; margin-top: 2px; }
.card-body { padding: 7px 9px 6px; }
.card-stat { color: #94a3b8; font-size: 0.7rem; margin: 1px 0; }
.card-badge {
    display: inline-block; background: rgba(229,9,20,0.2); color: #ff6b6b;
    border-radius: 4px; padding: 2px 6px; font-size: 0.68rem; font-weight: 600; margin: 2px 2px 4px 0;
}
.card-badge.green { background: rgba(34,197,94,0.2); color: #22c55e; }
.card-badge.red { background: rgba(239,68,68,0.2); color: #ef4444; }
.card-verdict { font-size: 0.72rem; color: #94a3b8; margin-bottom: 4px; font-weight: 600; }
.card-reason { font-size: 0.7rem; color: #64748b; margin: 2px 0; line-height: 1.4; }

/* ── Spacing & layout utama ── */
.stVerticalBlock { gap: 0.4rem !important; }
/* Flash message */
div[data-testid="stAlert"] { margin-bottom: 0.5rem !important; border-radius: 8px !important; }
/* Search bar row — sejajar vertikal, jarak bawah rapat ke banner */
div[data-testid="stHorizontalBlock"]:has(input[type="text"]) { margin-bottom: 0.5rem !important; align-items: center !important; }
div[data-testid="stHorizontalBlock"]:has(input[type="text"]) > div { display: flex !important; align-items: center !important; }
/* Action bar bawah banner — sejajar vertikal */
div[data-testid="stHorizontalBlock"]:has(.stLinkButton) > div,
div[data-testid="stHorizontalBlock"]:has(.stLinkButton) { align-items: center !important; }
div[data-testid="stHorizontalBlock"]:has(.stLinkButton) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(.stLinkButton) .stLinkButton > a { margin-top: 0 !important; }
/* Divider */
hr { margin: 0.6rem 0 !important; border-color: rgba(255,255,255,0.08) !important; }
/* Subheader section rekomendasi */
h2, h3 { margin-top: 0.25rem !important; margin-bottom: 0.25rem !important; }
/* Kolom kartu film */
div[data-testid="stColumns"] { gap: 1rem !important; }
/* Tombol di bawah kartu */
.stButton { margin-top: 0.2rem !important; }
/* Success/info box */
div[data-testid="stSuccessMessage"], div[data-testid="stInfoMessage"] {
    border-radius: 8px !important;
    margin-bottom: 0.4rem !important;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=LIVE_CACHE_TTL)
def fetch_api(endpoint: str, params: dict | None = None):
    request_params = dict(params or {})
    request_params["api_key"] = API_KEY
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/{endpoint}",
            params=request_params,
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success") is False:
            return None
        return data
    except requests.RequestException:
        return None


@st.cache_data(ttl=LIVE_CACHE_TTL)
def fetch_movie_details(movie_id: int, append: str = "keywords,credits,videos"):
    return fetch_api(f"movie/{movie_id}", {"append_to_response": append})


def format_runtime(minutes):
    if not minutes:
        return "N/A"
    return f"{minutes // 60}h {minutes % 60}m"


def keyword_ids(movie: dict) -> list[int]:
    keyword_data = movie.get("keywords") or {}
    keywords = keyword_data.get("keywords") or keyword_data.get("results") or []
    return [
        int(keyword["id"])
        for keyword in keywords
        if isinstance(keyword, dict) and keyword.get("id") is not None
    ]


def add_to_pool(pool: dict[int, dict], movies: list[dict], source: str, weight: float):
    for rank, movie in enumerate(movies[:RECOMMENDATION_CONFIG["tmdb_pool"]]):
        movie_id = int(movie.get("id") or 0)
        if not movie_id:
            continue

        position_score = max(0.66, 1 - (rank * 0.018))
        signal = max(0.35, min(weight * position_score, 1.0))
        entry = pool.setdefault(movie_id, {
            "movie": movie,
            "signal": 0.0,
            "sources": [],
        })

        if signal > entry["signal"]:
            entry["movie"] = movie
            entry["signal"] = signal
        if source not in entry["sources"]:
            entry["sources"].append(source)


def collect_live_candidates(source_movie: dict) -> list[dict]:
    source_id = int(source_movie["id"])
    genre_ids, _ = extract_genres(source_movie)
    pool: dict[int, dict] = {}

    source_title = source_movie.get("title") or ""
    base_name = re.sub(r"\s*(?:part|chapter|episode)?\s*(\d+)?$", "", source_title, flags=re.IGNORECASE).strip()

    recommendation_sources = [
        (f"movie/{source_id}/recommendations", {"page": 1}, "TMDB recommendations", 1.00),
        (f"movie/{source_id}/similar", {"page": 1}, "TMDB similar", 0.88),
    ]

    for endpoint, params, source, weight in recommendation_sources:
        data = fetch_api(endpoint, params)
        add_to_pool(pool, (data or {}).get("results", []), source, weight)

    if base_name:
        data = fetch_api("search/movie", {
            "query": base_name,
            "include_adult": "false",
            "page": 1,
        })
        add_to_pool(pool, (data or {}).get("results", []), "Franchise search", 0.82)

        data = fetch_api("search/movie", {
            "query": f"{base_name} 2",
            "include_adult": "false",
            "page": 1,
        })
        add_to_pool(pool, (data or {}).get("results", []), "Franchise sequel search", 0.85)

        data = fetch_api("search/movie", {
            "query": f"{base_name} Part",
            "include_adult": "false",
            "page": 1,
        })
        add_to_pool(pool, (data or {}).get("results", []), "Franchise part search", 0.80)

    if genre_ids:
        data = fetch_api("discover/movie", {
            "include_adult": "false",
            "page": 1,
            "sort_by": "vote_count.desc",
            "vote_count.gte": 250,
            "with_genres": "|".join(str(genre_id) for genre_id in sorted(genre_ids)[:3]),
        })
        add_to_pool(pool, (data or {}).get("results", []), "Live genre discovery", 0.70)

    source_keyword_ids = keyword_ids(source_movie)
    if source_keyword_ids:
        data = fetch_api("discover/movie", {
            "include_adult": "false",
            "page": 1,
            "sort_by": "vote_count.desc",
            "vote_count.gte": 120,
            "with_keywords": "|".join(str(keyword_id) for keyword_id in source_keyword_ids[:4]),
        })
        add_to_pool(pool, (data or {}).get("results", []), "Live keyword discovery", 0.78)

    pool.pop(source_id, None)
    top_candidates = sorted(
        pool.items(),
        key=lambda item: item[1]["signal"],
        reverse=True,
    )[:RECOMMENDATION_CONFIG["candidate_pool"]]

    enriched = []
    for movie_id, entry in top_candidates:
        details = fetch_movie_details(movie_id, append="keywords,credits")
        movie = details or entry["movie"]
        movie["_tmdb_signal"] = entry["signal"]
        movie["_sources"] = tuple(entry["sources"])
        enriched.append(movie)

    return enriched


def record_feedback(source_id: int, recommendation: dict, label: str):
    sample = {
        "source_id": int(source_id),
        "movie_id": int(recommendation["id"]),
        "label": label,
        "features": recommendation["features"],
    }
    st.session_state.feedback_samples = [
        item
        for item in st.session_state.feedback_samples
        if not (
            item["source_id"] == sample["source_id"]
            and item["movie_id"] == sample["movie_id"]
        )
    ]
    st.session_state.feedback_samples.append(sample)

    # Cache movie details for taste profile building
    movie_id = int(recommendation["id"])
    if not any(int(m.get("id") or 0) == movie_id for m in st.session_state.liked_movie_details):
        details = fetch_movie_details(movie_id, append="keywords,credits")
        if details:
            st.session_state.liked_movie_details.append(details)


def status_for_feedback(source_id: int, movie_id: int) -> str | None:
    for sample in st.session_state.feedback_samples:
        if sample["source_id"] == source_id and sample["movie_id"] == movie_id:
            return sample["label"]
    return None


@st.cache_data(ttl=LIVE_CACHE_TTL)
def collect_taste_candidates(top_genre_ids: tuple[int, ...], top_keyword_tokens: tuple[str, ...]) -> list[dict]:
    """Collect live TMDB candidates based on user's top liked genres and keywords."""
    pool: dict[int, dict] = {}

    if top_genre_ids:
        data = fetch_api("discover/movie", {
            "include_adult": "false",
            "page": 1,
            "sort_by": "vote_count.desc",
            "vote_count.gte": 300,
            "with_genres": "|".join(str(g) for g in top_genre_ids[:3]),
        })
        add_to_pool(pool, (data or {}).get("results", []), "Genre favorit", 1.0)

        data = fetch_api("discover/movie", {
            "include_adult": "false",
            "page": 2,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
            "with_genres": "|".join(str(g) for g in top_genre_ids[:2]),
        })
        add_to_pool(pool, (data or {}).get("results", []), "Genre favorit (rated)", 0.90)

    if top_keyword_tokens:
        # Search by top keyword terms
        for kw in top_keyword_tokens[:3]:
            data = fetch_api("search/keyword", {"query": kw})
            kw_results = (data or {}).get("results", [])
            if kw_results:
                kw_id = kw_results[0].get("id")
                if kw_id:
                    disc = fetch_api("discover/movie", {
                        "include_adult": "false",
                        "page": 1,
                        "sort_by": "vote_count.desc",
                        "vote_count.gte": 150,
                        "with_keywords": str(kw_id),
                    })
                    add_to_pool(pool, (disc or {}).get("results", []), f"Kata kunci: {kw}", 0.85)

    top_candidates = sorted(pool.items(), key=lambda x: x[1]["signal"], reverse=True)[:RECOMMENDATION_CONFIG["candidate_pool"]]
    enriched = []
    for movie_id, entry in top_candidates:
        details = fetch_movie_details(movie_id, append="keywords,credits")
        movie = details or entry["movie"]
        movie["_tmdb_signal"] = entry["signal"]
        movie["_sources"] = tuple(entry["sources"])
        enriched.append(movie)
    return enriched


if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "search_query" not in st.session_state:
    st.session_state.search_query = UI_CONFIG["default_search"]
if "feedback_samples" not in st.session_state:
    st.session_state.feedback_samples = []
if "liked_movie_details" not in st.session_state:
    st.session_state.liked_movie_details = []
if "show_taste_recs" not in st.session_state:
    st.session_state.show_taste_recs = False
if "flash_message" not in st.session_state:
    st.session_state.flash_message = None


def flash(message: str):
    st.session_state.flash_message = message
    st.rerun()

ai_engine = RealtimeMovieAI()


with st.sidebar:
    st.title("🎬 CineMatch")
    st.caption("Temukan film yang cocok untukmu dengan mudah.")

    st.divider()
    st.subheader("🎛️ Filter Film")
    min_year = st.slider("Tahun paling awal", 1970, 2026, UI_CONFIG["default_min_year"])
    min_rating = st.slider("Rating minimal", 0.0, 10.0, UI_CONFIG["default_min_rating"], 0.5)

    st.divider()
    feedback_count = len(st.session_state.feedback_samples)
    st.subheader("🎯 Selera Kamu")
    if feedback_count == 0:
        st.caption("CineMatch belum mengenal seleramu. Beri tanda 👍 atau 👎 pada film agar rekomendasi makin pas!")
        st.progress(0.0)
        st.caption("Belum ada pendapat")
    else:
        pos = sum(1 for s in st.session_state.feedback_samples if s["label"] == "positive")
        neg = feedback_count - pos
        st.caption(f"CineMatch sudah mengenal seleramu dari **{feedback_count}** film.")
        st.progress(min(feedback_count / 10, 1.0))
        st.caption(f"👍 {pos} disukai  •  👎 {neg} kurang cocok")
        if feedback_count >= 3:
            st.success("CineMatch mulai mengenal seleramu!")
        if feedback_count >= 7:
            st.success("Rekomendasi makin akurat untukmu 🎯")

    if feedback_count > 0:
        learned = ai_engine.learned_weights(st.session_state.feedback_samples)
        label_map = {
            "genre_match": "Genre",
            "story_match": "Cerita",
            "keyword_match": "Tema",
            "people_match": "Aktor/Sutradara",
            "quality": "Kualitas Film",
            "era_match": "Era Film",
            "franchise_match": "Satu Seri",
            "tmdb_signal": "Popularitas",
        }
        if "show_learned" not in st.session_state:
            st.session_state.show_learned = False
        lbl_learn = "🔼 Sembunyikan" if st.session_state.show_learned else "📊 Apa yang CineMatch pelajari?"
        if st.button(lbl_learn, use_container_width=True, key="btn_learn"):
            st.session_state.show_learned = not st.session_state.show_learned
            st.rerun()
        if st.session_state.show_learned:
            for key, val in sorted(learned.items(), key=lambda x: -x[1]):
                label = label_map.get(key, key)
                st.caption(f"{label}: {val*100:.0f}%")
                st.progress(float(val))

    st.divider()
    liked_count = sum(1 for s in st.session_state.feedback_samples if s["label"] == "positive")
    if liked_count >= 2:
        btn_label = "✨ Sembunyikan Pilihan Untukku" if st.session_state.show_taste_recs else "🎯 Rekomendasikan Film untuk Saya!"
        if st.button(btn_label, use_container_width=True):
            st.session_state.show_taste_recs = not st.session_state.show_taste_recs
            st.rerun()
        st.caption(f"Berdasarkan {liked_count} film yang kamu suka 👍")
    else:
        remaining = 2 - liked_count
        st.info(f"Suka {remaining} film lagi (👍) untuk aktifkan rekomendasi personal!")

    if st.session_state.watchlist:
        if "show_watchlist" not in st.session_state:
            st.session_state.show_watchlist = False
        wl_count = len(st.session_state.watchlist)
        lbl_wl = f"🔼 Sembunyikan Tontonan" if st.session_state.show_watchlist else f"📌 Tontonan Saya ({wl_count} film)"
        if st.button(lbl_wl, use_container_width=True, key="btn_watchlist"):
            st.session_state.show_watchlist = not st.session_state.show_watchlist
            st.rerun()
        if st.session_state.show_watchlist:
            to_remove = None
            for idx, item in enumerate(st.session_state.watchlist[-6:][::-1]):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.caption(f"• {item}")
                with col_b:
                    if st.button("✕", key=f"rm_wl_{idx}", help="Hapus dari tontonan"):
                        to_remove = item
            if to_remove and to_remove in st.session_state.watchlist:
                st.session_state.watchlist.remove(to_remove)
                st.rerun()

    st.divider()
    if "confirm_reset" not in st.session_state:
        st.session_state.confirm_reset = False

    if st.session_state.confirm_reset:
        st.warning("Yakin ingin menghapus semua data seleramu?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Ya, hapus", use_container_width=True):
                st.session_state.feedback_samples = []
                st.session_state.liked_movie_details = []
                st.session_state.show_taste_recs = False
                st.session_state.confirm_reset = False
                st.session_state.flash_message = "Data seleramu sudah dihapus. Mulai dari awal yuk!"
                st.rerun()
        with col_no:
            if st.button("Batal", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()
    else:
        if st.button("🗑️ Reset Selera", use_container_width=True):
            st.session_state.confirm_reset = True
            st.rerun()

    if st.button("🔄 Perbarui Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


if st.session_state.flash_message:
    st.success(st.session_state.flash_message)
    st.session_state.flash_message = None

# ── Halaman sambutan (tampil saat belum ada pencarian) ───────────────────────
if not st.session_state.search_query or not st.session_state.search_query.strip():
    st.markdown(
        '<div style="text-align:center;padding:2.5rem 1rem 1.5rem;">'
        '<div style="font-size:3rem;margin-bottom:0.5rem;">🎬</div>'
        '<h1 style="font-size:2.2rem;font-weight:800;color:#e2e8f0;margin:0 0 0.5rem;">CineMatch</h1>'
        '<p style="font-size:1.05rem;color:#94a3b8;margin:0 0 1.5rem;max-width:500px;margin-left:auto;margin-right:auto;">'
        'Temukan film yang cocok untukmu! Ketik judul film yang kamu suka, dan kami akan carikan film-film serupa yang mungkin kamu sukai juga.'
        '</p></div>'
        '<div style="display:flex;justify-content:center;gap:1.5rem;flex-wrap:wrap;margin-bottom:2rem;">'
        '<div style="text-align:center;background:#1a1f2e;border-radius:12px;padding:1.2rem 1.5rem;min-width:130px;border:1px solid rgba(255,255,255,0.06);">'
        '<div style="font-size:1.8rem;">🔍</div>'
        '<div style="font-weight:700;color:#e2e8f0;margin:0.4rem 0 0.2rem;">1. Cari Film</div>'
        '<div style="font-size:0.8rem;color:#64748b;">Ketik judul film yang kamu suka</div>'
        '</div>'
        '<div style="text-align:center;background:#1a1f2e;border-radius:12px;padding:1.2rem 1.5rem;min-width:130px;border:1px solid rgba(255,255,255,0.06);">'
        '<div style="font-size:1.8rem;">🎯</div>'
        '<div style="font-weight:700;color:#e2e8f0;margin:0.4rem 0 0.2rem;">2. Lihat Rekomendasi</div>'
        '<div style="font-size:0.8rem;color:#64748b;">Kami carikan film yang mirip</div>'
        '</div>'
        '<div style="text-align:center;background:#1a1f2e;border-radius:12px;padding:1.2rem 1.5rem;min-width:130px;border:1px solid rgba(255,255,255,0.06);">'
        '<div style="font-size:1.8rem;">👍</div>'
        '<div style="font-weight:700;color:#e2e8f0;margin:0.4rem 0 0.2rem;">3. Beri Pendapat</div>'
        '<div style="font-size:0.8rem;color:#64748b;">Suka atau tidak? Rekomendasi makin akurat!</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

col1, col2 = st.columns([5, 1])
with col1:
    query = st.text_input(
        "🔍 Cari film",
        value=st.session_state.search_query,
        label_visibility="collapsed",
    )
    st.session_state.search_query = query
with col2:
    if st.button("🎲 Acak", use_container_width=True):
        trending = fetch_api("trending/movie/week")
        if trending and trending.get("results"):
            st.session_state.search_query = random.choice(trending["results"])["title"]
            st.rerun()


if query:
    with st.spinner("Sedang mencari film..."):
        search = fetch_api("search/movie", {"query": query, "include_adult": "false"})

    if not search or not search.get("results"):
        st.error("Film tidak ditemukan. Coba judul lain ya! 🎬")
        st.caption("Contoh: Inception, Avengers, The Dark Knight, Interstellar")
        st.stop()

    selected_movie = search["results"][0]
    details = fetch_movie_details(selected_movie["id"])
    if not details:
        st.error("Ups, ada masalah saat mengambil data. Coba lagi ya!")
        st.stop()

    backdrop_path = details.get("backdrop_path") or details.get("poster_path") or ""
    backdrop = f"{BACKDROP_BASE}{backdrop_path}" if backdrop_path else ""
    safe_title = escape(details.get("title", "Untitled"))
    safe_overview = escape((details.get("overview") or "")[:280])
    year = details.get("release_date", "N/A")[:4]
    rating = safe_float(details.get("vote_average"))
    runtime = format_runtime(details.get("runtime"))
    budget = int(details.get("budget") or 0)
    status = details.get("status", "N/A")
    genres_str = " • ".join(g["name"] for g in (details.get("genres") or [])[:3])

    trailer = next(
        (
            f"https://youtube.com/watch?v={video['key']}"
            for video in details.get("videos", {}).get("results", [])
            if video.get("type") == "Trailer"
        ),
        None,
    )

    if backdrop:
        st.markdown(
            f'<div style="position:relative;border-radius:12px;overflow:hidden;height:300px;margin:0.25rem 0 0.5rem;">'
            f'<img src="{backdrop}" alt="{safe_title}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 30%;">'
            f'<div style="position:absolute;inset:0;background:linear-gradient(to right,rgba(0,0,0,0.85) 50%,rgba(0,0,0,0.1) 100%);display:flex;align-items:center;padding:1.5rem 2rem;z-index:1;">'
            f'<div>'
            f'<div style="font-size:1.9rem;font-weight:800;color:#fff;margin:0 0 6px;line-height:1.2;">{safe_title}</div>'
            f'<div style="font-size:0.85rem;color:#94a3b8;margin:0 0 8px;">&#11088; {rating:.1f}/10 &nbsp;&bull;&nbsp; {year} &nbsp;&bull;&nbsp; {runtime} &nbsp;&bull;&nbsp; {genres_str}</div>'
            f'<div style="font-size:0.85rem;color:#cbd5e1;line-height:1.6;max-width:520px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{safe_overview}</div>'
            f'</div></div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1a1f2e 0%,#0f172a 100%);border-radius:12px;display:flex;align-items:center;padding:2rem;min-height:160px;margin:0.25rem 0 0.5rem;">'
            f'<div>'
            f'<div style="font-size:1.9rem;font-weight:800;color:#fff;margin:0 0 6px;line-height:1.2;">{safe_title}</div>'
            f'<div style="font-size:0.85rem;color:#94a3b8;margin:0 0 8px;">&#11088; {rating:.1f}/10 &nbsp;&bull;&nbsp; {year} &nbsp;&bull;&nbsp; {runtime} &nbsp;&bull;&nbsp; {genres_str}</div>'
            f'<div style="font-size:0.85rem;color:#cbd5e1;line-height:1.6;max-width:520px;">{safe_overview}</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    # Action bar: tombol + stat dalam satu baris HTML yang rapi
    # Tombol Streamlit native di kolom kiri, stat di kanan
    action_bar_html = (
        f'<div style="display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap;margin:0.25rem 0 0;">'
        f'<div id="_watchlist_placeholder_" style="display:none;"></div>'
        f'<div style="background:#1e293b;border-radius:8px;padding:8px 14px;text-align:center;">'
        f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Rating</div>'
        f'<div style="font-size:1rem;font-weight:700;color:#fbbf24;">&#11088; {rating:.1f}</div></div>'
        f'<div style="background:#1e293b;border-radius:8px;padding:8px 14px;text-align:center;">'
        f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Durasi</div>'
        f'<div style="font-size:1rem;font-weight:700;color:#e2e8f0;">{runtime}</div></div>'
        f'<div style="background:#1e293b;border-radius:8px;padding:8px 14px;text-align:center;">'
        f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Tahun</div>'
        f'<div style="font-size:1rem;font-weight:700;color:#e2e8f0;">{year}</div></div>'
        f'<div style="background:#1e293b;border-radius:8px;padding:8px 14px;text-align:center;">'
        f'<div style="font-size:0.6rem;color:#64748b;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Status</div>'
        f'<div style="font-size:0.85rem;font-weight:700;color:#22c55e;">{status}</div></div>'
        f'</div>'
    )

    btn_col, stat_col, fb_col = st.columns([5, 7, 3])
    with btn_col:
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("❤️ Simpan ke Tontonan", use_container_width=True):
                if details["title"] not in st.session_state.watchlist:
                    st.session_state.watchlist.append(details["title"])
                    st.session_state.flash_message = "Film berhasil disimpan ke Tontonan kamu! 🎬"
                else:
                    st.session_state.flash_message = "Film ini sudah ada di Tontonan kamu."
                st.rerun()
        with bcol2:
            if trailer:
                st.link_button("▶ Tonton Trailer", trailer, use_container_width=True)
    with stat_col:
        st.markdown(action_bar_html, unsafe_allow_html=True)
    with fb_col:
        main_fb_status = status_for_feedback(int(details["id"]), int(details["id"]))
        fbc1, fbc2 = st.columns(2)
        with fbc1:
            liked = main_fb_status == "positive"
            if st.button("👍" + (" Disukai" if liked else " Suka"), key="main_like", use_container_width=True):
                sample = {
                    "source_id": int(details["id"]),
                    "movie_id": int(details["id"]),
                    "label": "positive",
                    "features": {"genre_match": 1.0, "story_match": 1.0, "keyword_match": 1.0,
                                 "people_match": 1.0, "quality": safe_float(details.get("vote_average")) / 10,
                                 "era_match": 1.0, "franchise_match": 0.0, "tmdb_signal": 1.0},
                }
                st.session_state.feedback_samples = [s for s in st.session_state.feedback_samples
                    if not (s["source_id"] == sample["source_id"] and s["movie_id"] == sample["movie_id"])]
                st.session_state.feedback_samples.append(sample)
                if not any(int(m.get("id") or 0) == int(details["id"]) for m in st.session_state.liked_movie_details):
                    st.session_state.liked_movie_details.append(details)
                st.session_state.flash_message = "Film ini ditandai Suka! 👍"
                st.rerun()
        with fbc2:
            disliked = main_fb_status == "negative"
            if st.button("👎" + (" Tidak Cocok" if disliked else " Tidak"), key="main_dislike", use_container_width=True):
                sample = {
                    "source_id": int(details["id"]),
                    "movie_id": int(details["id"]),
                    "label": "negative",
                    "features": {"genre_match": 1.0, "story_match": 1.0, "keyword_match": 1.0,
                                 "people_match": 1.0, "quality": safe_float(details.get("vote_average")) / 10,
                                 "era_match": 1.0, "franchise_match": 0.0, "tmdb_signal": 1.0},
                }
                st.session_state.feedback_samples = [s for s in st.session_state.feedback_samples
                    if not (s["source_id"] == sample["source_id"] and s["movie_id"] == sample["movie_id"])]
                st.session_state.feedback_samples.append(sample)
                st.session_state.flash_message = "Film ini ditandai Tidak Cocok! 👎"
                st.rerun()

    st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)
    st.subheader(f"🎬 Film yang Relevan dengan {details['title']}")

    with st.spinner("Sedang mencari film yang cocok untukmu..."):
        candidates = collect_live_candidates(details)
        recs, model_info = ai_engine.rank(
            details,
            candidates,
            feedback_samples=st.session_state.feedback_samples,
            min_year=min_year,
            min_rating=min_rating,
            limit=RECOMMENDATION_CONFIG["default_n"],
        )

    if recs:
        st.success(f"Kami menemukan **{len(recs)} film** yang mungkin kamu suka! 🎉")

        rows = (len(recs) + 2) // 3
        source_id = int(details["id"])
        for row in range(rows):
            cols = st.columns(3)
            for i in range(3):
                rec_index = row * 3 + i
                if rec_index >= len(recs):
                    continue

                rec = recs[rec_index]
                with cols[i]:
                    safe_rec_title = escape(rec["title"][:36])
                    poster = f"{POSTER_BASE}{rec.get('poster_path')}" if rec.get('poster_path') else "https://via.placeholder.com/500x300?text=No+Poster"
                    feedback_status = status_for_feedback(source_id, rec["id"])
                    explanation = explain_recommendation(rec, details["title"])

                    # Badge inline styles (DOMPurify strips class attributes)
                    if rec.get('franchise_match', 0) >= 50:
                        franchise_badge = '<span style="display:inline-block;background:rgba(229,9,20,0.2);color:#ff6b6b;border-radius:4px;padding:2px 6px;font-size:0.68rem;font-weight:600;margin:2px 2px 4px 0;">&#127916; Seri</span>'
                    else:
                        franchise_badge = ''

                    if feedback_status == "positive":
                        fb_badge = '<span style="display:inline-block;background:rgba(34,197,94,0.2);color:#22c55e;border-radius:4px;padding:2px 6px;font-size:0.68rem;font-weight:600;margin:2px 2px 4px 0;">&#10003; Disukai</span>'
                    elif feedback_status == "negative":
                        fb_badge = '<span style="display:inline-block;background:rgba(239,68,68,0.2);color:#ef4444;border-radius:4px;padding:2px 6px;font-size:0.68rem;font-weight:600;margin:2px 2px 4px 0;">&#10007; Tidak Cocok</span>'
                    else:
                        fb_badge = ''

                    safe_verdict = escape(explanation['verdict'])
                    reasons_parts = "".join(
                        f'<div style="font-size:0.7rem;color:#64748b;margin:2px 0;line-height:1.4;">{escape(r)}</div>'
                        for r in explanation["reasons"][:2]
                    )

                    card_html = (
                        '<div style="background:#1a1f2e;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.06);box-shadow:0 4px 16px rgba(0,0,0,0.3);margin-bottom:8px;display:flex;flex-direction:column;">'
                          '<div style="position:relative;width:100%;height:200px;overflow:hidden;flex-shrink:0;">'
                            f'<img src="{poster}" alt="{safe_rec_title}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;">'
                            '<div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top,rgba(0,0,0,0.92) 0%,transparent 65%);padding:10px 8px 6px;">'
                              f'<div style="font-size:0.8rem;font-weight:700;color:#fff;margin:0;line-height:1.2;">{safe_rec_title}</div>'
                              f'<div style="font-size:0.7rem;color:#fbbf24;font-weight:600;margin-top:2px;">&#11088; {rec["vote_average"]:.1f} &bull; {rec.get("release_date","")[:4]}</div>'
                            '</div>'
                          '</div>'
                          '<div style="padding:7px 9px 6px;min-height:72px;">'
                            f'{franchise_badge}{fb_badge}'
                            f'<div style="font-size:0.72rem;color:#94a3b8;margin-bottom:3px;font-weight:600;">{safe_verdict}</div>'
                            f'{reasons_parts}'
                          '</div>'
                        '</div>'
                    )
                    st.html(card_html)

                    if st.button("🔍 Cari film ini", key=f"view_{source_id}_{rec['id']}", use_container_width=True):
                        st.session_state.search_query = rec["title"]
                        st.rerun()

                    fb_cols = st.columns(2)
                    with fb_cols[0]:
                        if st.button("👍 Suka", key=f"up_{source_id}_{rec['id']}", use_container_width=True):
                            record_feedback(source_id, rec, "positive")
                            st.session_state.flash_message = f"Oke, CineMatch akan cari film serupa untukmu! 👍"
                            st.rerun()
                    with fb_cols[1]:
                        if st.button("👎 Tidak Cocok", key=f"down_{source_id}_{rec['id']}", use_container_width=True):
                            record_feedback(source_id, rec, "negative")
                            st.session_state.flash_message = f"Oke, CineMatch akan hindari film seperti ini! 👎"
                            st.rerun()
            if row < rows - 1:
                st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
    else:
        st.info("Belum ada film yang cocok ditemukan. Coba turunkan filter tahun atau rating.")


# ── Taste-based recommendations ─────────────────────────────────────────────
if st.session_state.show_taste_recs:
    taste = build_taste_profile(
        st.session_state.feedback_samples,
        st.session_state.liked_movie_details,
    )
    if taste is None:
        st.warning("Belum ada film yang kamu suka. Klik 👍 pada film dulu!")
    else:
        st.divider()
        liked_titles = [
            m.get("title", "")
            for m in st.session_state.liked_movie_details
            if int(m.get("id") or 0) in taste.liked_movie_ids
        ]
        disliked_count = len(taste.disliked_movie_ids)

        st.subheader("🎯 Film Pilihan Untukmu")
        st.info(
            f"CineMatch mempelajari seleramu dari film yang kamu suka:\n\n"
            f"**{', '.join(liked_titles[:5])}{'...' if len(liked_titles) > 5 else ''}**\n\n"
            f"🎭 Genre favorit: **{len(taste.liked_genre_ids)} genre**"
            + (f"\n🚫 Menghindari pola dari: **{disliked_count} film yang tidak cocok**" if disliked_count else "")
        )

        with st.spinner("Sedang mencari film yang cocok untukmu..."):
            taste_candidates = collect_taste_candidates(
                tuple(taste.top_genre_ids),
                tuple(list(taste.liked_keyword_tokens.keys())[:5]),
            )
            taste_recs = ai_engine.rank_from_taste(
                taste,
                taste_candidates,
                feedback_samples=st.session_state.feedback_samples,
                min_year=min_year,
                min_rating=min_rating,
                limit=RECOMMENDATION_CONFIG["default_n"],
            )

        if taste_recs:
            st.caption(f"🎉 Ditemukan {len(taste_recs)} film yang cocok dengan seleramu!")
            taste_rows = (len(taste_recs) + 2) // 3
            for row in range(taste_rows):
                cols = st.columns(3)
                for i in range(3):
                    idx = row * 3 + i
                    if idx >= len(taste_recs):
                        continue
                    rec = taste_recs[idx]
                    with cols[i]:
                        safe_rec_title = escape(rec["title"][:34])
                        poster = f"{POSTER_BASE}{rec.get('poster_path')}" if rec.get('poster_path') else "https://via.placeholder.com/500x300?text=No+Poster"
                        explanation = explain_recommendation(rec, "seleramu")
                        safe_verdict = escape(explanation['verdict'])
                        reasons_parts = "".join(
                            f'<div style="font-size:0.7rem;color:#64748b;margin:2px 0;line-height:1.4;">{escape(r)}</div>'
                            for r in explanation["reasons"][:2]
                        )
                        taste_card_html = (
                            '<div style="background:#1a1f2e;border-radius:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.06);box-shadow:0 4px 16px rgba(0,0,0,0.3);margin-bottom:8px;display:flex;flex-direction:column;">'
                              '<div style="position:relative;width:100%;height:200px;overflow:hidden;flex-shrink:0;">'
                                f'<img src="{poster}" alt="{safe_rec_title}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;">'
                                '<div style="position:absolute;bottom:0;left:0;right:0;background:linear-gradient(to top,rgba(0,0,0,0.92) 0%,transparent 65%);padding:10px 8px 6px;">'
                                  f'<div style="font-size:0.8rem;font-weight:700;color:#fff;margin:0;line-height:1.2;">{safe_rec_title}</div>'
                                  f'<div style="font-size:0.7rem;color:#fbbf24;font-weight:600;margin-top:2px;">&#11088; {rec["vote_average"]:.1f}</div>'
                                '</div>'
                              '</div>'
                              '<div style="padding:7px 9px 6px;min-height:72px;">'
                                f'<div style="font-size:0.72rem;color:#22c55e;margin-bottom:3px;font-weight:600;">&#10003; {safe_verdict}</div>'
                                f'{reasons_parts}'
                              '</div>'
                            '</div>'
                        )
                        st.html(taste_card_html)

                        if st.button("🔍 Cari film ini", key=f"taste_view_{rec['id']}", use_container_width=True):
                            st.session_state.search_query = rec["title"]
                            st.session_state.show_taste_recs = False
                            st.rerun()
                if row < taste_rows - 1:
                    st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)
        else:
            st.info("Belum ada film yang cocok ditemukan. Coba beri pendapat pada lebih banyak film!")


st.caption("Dibuat dengan ❤️ oleh Rahmadtzy • 2026")
