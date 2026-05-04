import streamlit as st
import requests
import random
import pickle
import bz2
import pandas as pd
from difflib import SequenceMatcher

# ---------------- PAGE CONFIG ----------------

st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")

# ---------------- STYLE ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: white;
}

.main { background: radial-gradient(circle at top right, #1a1a1a, #050505); }

.movie-card {
    background: rgba(255,255,255,0.05);
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    overflow: hidden;
    transition: 0.3s;
}

.movie-card:hover {
    transform: translateY(-8px);
    border-color: #E50914;
    box-shadow: 0 10px 25px rgba(229,9,20,0.3);
}

.hero {
    height: 520px;
    border-radius: 30px;
    padding: 50px;
    display: flex;
    align-items: flex-end;
    background-size: cover;
    background-position: center;
}

.genre {
    background: rgba(229,9,20,0.2);
    padding: 5px 12px;
    border-radius: 30px;
    font-size: 11px;
    margin-right: 5px;
}

.stat {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    text-align: center;
    padding: 10px;
}

.cast-card {
    background: rgba(255,255,255,0.05);
    border-radius: 12px;
    text-align: center;
    padding: 8px;
    font-size: 11px;
}

.watchlist-card {
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 12px;
}

.badge-ml {
    background: rgba(0,200,100,0.2);
    border: 1px solid rgba(0,200,100,0.4);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    color: #00c864;
}

.badge-api {
    background: rgba(229,9,20,0.2);
    border: 1px solid rgba(229,9,20,0.4);
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    color: #E50914;
}
</style>
""", unsafe_allow_html=True)

# ---------------- API ----------------

API_KEY = "244a292fb73be77c0134ac3de3c9b824"

@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    try:
        r = requests.get(f"https://api.themoviedb.org/3/{endpoint}", params=params)
        return r.json()
    except:
        return None

# ---------------- LOAD ML MODEL ----------------

@st.cache_resource
def load_ml_model():
    movies = pd.DataFrame(pickle.load(open("movie_dict.pkl", "rb")))
    with bz2.BZ2File("similarity.pbz2", "rb") as f:
        similarity = pickle.load(f)
    return movies, similarity

movies_df, similarity_matrix = load_ml_model()

# ---------------- HELPER ----------------

def format_runtime(m):
    if not m:
        return "N/A"
    return f"{m//60}j {m%60}m"

def similarity_score(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def get_poster(movie_id):
    data = fetch_api(f"movie/{movie_id}")
    if data and data.get("poster_path"):
        return f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
    return None

# ---------------- ML RECOMMENDATION ENGINE ----------------

def ml_recommend(title, min_year=None, min_rating=None, n=12):
    """Cosine similarity-based ML recommendation from local model."""
    # fuzzy match title in dataset
    titles = movies_df["title"].tolist()
    best_match = max(titles, key=lambda t: similarity_score(title, t))
    score = similarity_score(title, best_match)

    if score < 0.4:
        return [], False

    idx = movies_df[movies_df["title"] == best_match].index[0]
    distances = list(enumerate(similarity_matrix[idx]))
    distances = sorted(distances, key=lambda x: x[1], reverse=True)[1:40]

    results = []
    for i, dist in distances:
        row = movies_df.iloc[i]
        tmdb = fetch_api(f"movie/{row['movie_id']}")
        if not tmdb or not tmdb.get("poster_path"):
            continue

        # filter by year
        year = int(tmdb.get("release_date", "0000")[:4] or 0)
        if min_year and year < min_year:
            continue

        # filter by rating
        rating = tmdb.get("vote_average", 0)
        if min_rating and rating < min_rating:
            continue

        results.append({
            "id": row["movie_id"],
            "title": tmdb["title"],
            "poster_path": tmdb["poster_path"],
            "vote_average": rating,
            "release_date": tmdb.get("release_date", ""),
            "similarity": round(dist * 100, 1),
            "source": "ml"
        })

        if len(results) >= n:
            break

    return results, True

def api_recommend(title, genre_ids, min_year=None, min_rating=None, n=12):
    """Fallback API-based recommendation."""
    search = fetch_api("search/movie", {"query": title})
    if not search:
        return []

    scored = []
    for m in search.get("results", []):
        if not m.get("poster_path"):
            continue
        year = int((m.get("release_date") or "0000")[:4])
        if min_year and year < min_year:
            continue
        rating = m.get("vote_average", 0)
        if min_rating and rating < min_rating:
            continue

        ts = similarity_score(title, m["title"])
        gs = 0.3 if any(g in genre_ids for g in m.get("genre_ids", [])) else 0
        score = ts * 0.6 + rating * 0.03 + m.get("popularity", 0) * 0.001 + gs
        scored.append((score, {**m, "source": "api"}))

    scored.sort(key=lambda x: x[0], reverse=True)
    recs = [m for s, m in scored if s > 0.2]

    if len(recs) < 6 and genre_ids:
        discover = fetch_api("discover/movie", {
            "with_genres": genre_ids[0],
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200
        })
        if discover:
            for m in discover["results"]:
                recs.append({**m, "source": "api"})

    return recs[:n]

# ---------------- SESSION STATE ----------------

for key, default in [
    ("watchlist", []),
    ("search_query", "Dune"),
    ("user_ratings", {}),
    ("active_tab", "🔍 Discover"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def toggle_watchlist(movie_data):
    titles = [w["title"] for w in st.session_state.watchlist]
    if movie_data["title"] in titles:
        st.session_state.watchlist = [w for w in st.session_state.watchlist if w["title"] != movie_data["title"]]
        st.toast("Dihapus dari watchlist")
    else:
        st.session_state.watchlist.append(movie_data)
        st.toast("Ditambahkan ke watchlist ✅")

def in_watchlist(title):
    return title in [w["title"] for w in st.session_state.watchlist]

# ---------------- SIDEBAR ----------------

with st.sidebar:
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("logo.png", width=50)
    with col2:
        st.title("CineMatch")

    st.divider()

    # Navigation
    tabs = ["🔍 Discover", "🔥 Trending", "📋 Watchlist", "⭐ My Ratings"]
    st.session_state.active_tab = st.radio("Navigasi", tabs, index=tabs.index(st.session_state.active_tab), label_visibility="collapsed")

    st.divider()

    # Genre filter
    genre_data = fetch_api("genre/movie/list")
    genres = genre_data["genres"]
    genre_name = st.selectbox("Browse Genre", [g["name"] for g in genres])
    genre_id = next(g["id"] for g in genres if g["name"] == genre_name)

    st.divider()

    # Filters
    st.subheader("🎛️ Filter")
    min_year = st.slider("Tahun Minimum", 1970, 2025, 2000)
    min_rating = st.slider("Rating Minimum", 0.0, 10.0, 5.0, 0.5)

# ================================================================
# TAB: DISCOVER
# ================================================================

if st.session_state.active_tab == "🔍 Discover":

    col1, col2 = st.columns([4, 1])
    with col1:
        user_input = st.text_input("Cari film favoritmu", value=st.session_state.search_query)
        st.session_state.search_query = user_input
    with col2:
        st.write("")
        if st.button("🎲 Surprise"):
            trending = fetch_api("trending/movie/week")
            st.session_state.search_query = random.choice(trending["results"])["title"]
            st.rerun()

    query = st.session_state.search_query

    if query:
        with st.spinner("Mencari film..."):
            search = fetch_api("search/movie", {"query": query})

        if not search or not search["results"]:
            st.error("Film tidak ditemukan")
            st.stop()

        movie = search["results"][0]
        details = fetch_api(f"movie/{movie['id']}", {"append_to_response": "videos,credits"})

        # Hero
        backdrop = f"https://image.tmdb.org/t/p/original{details.get('backdrop_path', '')}"
        genre_html = "".join([f"<span class='genre'>{g['name']}</span>" for g in details["genres"]])

        st.markdown(f"""
        <div class="hero" style="background-image:url('{backdrop}')">
            <div style="max-width:800px">
            {genre_html}
            <h1 style="font-size:3.5rem">{details['title']}</h1>
            <p>{details['overview'][:400]}...</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Stats
        s1, s2, s3, s4, s5 = st.columns(5)
        with s1:
            st.markdown(f"<div class='stat'>⭐ {details['vote_average']:.1f}</div>", unsafe_allow_html=True)
        with s2:
            st.markdown(f"<div class='stat'>⏱ {format_runtime(details.get('runtime'))}</div>", unsafe_allow_html=True)
        with s3:
            st.markdown(f"<div class='stat'>📅 {details.get('release_date', 'N/A')}</div>", unsafe_allow_html=True)
        with s4:
            budget = details.get("budget", 0)
            st.markdown(f"<div class='stat'>💰 {'${:,.0f}'.format(budget) if budget else 'N/A'}</div>", unsafe_allow_html=True)
        with s5:
            st.markdown(f"<div class='stat'>🎬 {details.get('status', 'N/A')}</div>", unsafe_allow_html=True)

        st.write("")

        # Action buttons
        c1, c2, c3 = st.columns(3)
        with c1:
            wl_label = "💔 Hapus Watchlist" if in_watchlist(details["title"]) else "❤️ Watchlist"
            if st.button(wl_label, key="watch_btn"):
                toggle_watchlist({
                    "title": details["title"],
                    "id": details["id"],
                    "poster_path": details.get("poster_path", ""),
                    "vote_average": details["vote_average"],
                    "release_date": details.get("release_date", "")
                })
                st.rerun()

        with c2:
            trailer = next(
                (f"https://youtube.com/watch?v={v['key']}" for v in details["videos"]["results"] if v["type"] == "Trailer"),
                None
            )
            if trailer:
                st.link_button("▶ Trailer", trailer)

        with c3:
            # User rating
            prev_rating = st.session_state.user_ratings.get(details["title"], 0)
            user_star = st.feedback("stars", key=f"rating_{details['id']}")
            if user_star is not None:
                st.session_state.user_ratings[details["title"]] = user_star + 1
                st.toast(f"Rating tersimpan: {'⭐' * (user_star+1)}")

        # Cast
        cast = details["credits"]["cast"][:6]
        if cast:
            st.write("")
            st.subheader("🎭 Pemeran Utama")
            cast_cols = st.columns(6)
            for i, actor in enumerate(cast):
                with cast_cols[i]:
                    photo = f"https://image.tmdb.org/t/p/w185{actor['profile_path']}" if actor.get("profile_path") else "https://via.placeholder.com/185x278?text=N/A"
                    st.markdown(f"""
                    <div class="cast-card">
                        <img src="{photo}" style="width:100%;border-radius:8px;margin-bottom:6px">
                        <b>{actor['name']}</b><br>
                        <span style="color:#aaa">{actor['character']}</span>
                    </div>
                    """, unsafe_allow_html=True)

        # Recommendations
        st.divider()

        genre_ids = [g["id"] for g in details["genres"]]
        ml_recs, ml_found = ml_recommend(details["title"], min_year=min_year, min_rating=min_rating)

        if ml_found and ml_recs:
            st.markdown(f"<span class='badge-ml'>🤖 ML Model</span> &nbsp; <b>Rekomendasi untuk {details['title']}</b>", unsafe_allow_html=True)
            recs = ml_recs
        else:
            st.markdown(f"<span class='badge-api'>🌐 API Based</span> &nbsp; <b>Rekomendasi untuk {details['title']}</b>", unsafe_allow_html=True)
            recs = api_recommend(details["title"], genre_ids, min_year=min_year, min_rating=min_rating)

        st.write("")

        for row in range(2):
            cols = st.columns(6)
            for i in range(6):
                idx = row * 6 + i
                if idx < len(recs):
                    m = recs[idx]
                    with cols[i]:
                        poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                        sim_badge = f"<span style='color:#00c864;font-size:10px'>🤖 {m.get('similarity', '')}%</span>" if m.get("source") == "ml" else ""
                        st.markdown(f"""
                        <div class="movie-card">
                            <img src="{poster}" style="width:100%;height:220px;object-fit:cover">
                            <div style="padding:10px">
                                <b style="font-size:12px">{m['title']}</b>
                                <p style="color:#E50914;font-size:11px">⭐ {m['vote_average']}</p>
                                {sim_badge}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("Detail", key=f"rec_{row}_{i}_{m['id']}"):
                            st.session_state.search_query = m["title"]
                            st.rerun()

        # Popular in genre
        st.divider()
        st.subheader(f"🔥 Populer di Genre {genre_name}")
        popular = fetch_api("discover/movie", {"with_genres": genre_id, "sort_by": "popularity.desc"})
        cols = st.columns(6)
        for i, m in enumerate(popular["results"][:6]):
            with cols[i]:
                poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                st.markdown(f"""
                <div class="movie-card">
                    <img src="{poster}" style="width:100%;height:200px;object-fit:cover">
                    <div style="padding:10px">
                        <b style="font-size:12px">{m['title']}</b>
                        <p style="color:#E50914;font-size:11px">⭐ {m['vote_average']}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("Detail", key=f"pop_{i}_{m['id']}"):
                    st.session_state.search_query = m["title"]
                    st.session_state.active_tab = "🔍 Discover"
                    st.rerun()

# ================================================================
# TAB: TRENDING
# ================================================================

elif st.session_state.active_tab == "🔥 Trending":

    st.subheader("🔥 Trending Minggu Ini")

    period = st.radio("Periode", ["Minggu Ini", "Hari Ini"], horizontal=True)
    endpoint = "trending/movie/week" if period == "Minggu Ini" else "trending/movie/day"

    trending = fetch_api(endpoint)

    if trending:
        results = [m for m in trending["results"] if m.get("poster_path")]
        results = [m for m in results if int((m.get("release_date") or "0000")[:4]) >= min_year]
        results = [m for m in results if m.get("vote_average", 0) >= min_rating]

        for row in range(0, len(results[:18]), 6):
            cols = st.columns(6)
            for i, m in enumerate(results[row:row+6]):
                with cols[i]:
                    poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                    st.markdown(f"""
                    <div class="movie-card">
                        <img src="{poster}" style="width:100%;height:220px;object-fit:cover">
                        <div style="padding:10px">
                            <b style="font-size:12px">{m['title']}</b>
                            <p style="color:#E50914;font-size:11px">⭐ {m['vote_average']} &nbsp; 📅 {m.get('release_date','')[:4]}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Detail", key=f"trend_{row}_{i}_{m['id']}"):
                        st.session_state.search_query = m["title"]
                        st.session_state.active_tab = "🔍 Discover"
                        st.rerun()

    st.divider()
    st.subheader("🏆 Top Rated Sepanjang Masa")
    top_rated = fetch_api("movie/top_rated", {"vote_count.gte": 1000})
    if top_rated:
        results = [m for m in top_rated["results"] if m.get("poster_path")][:12]
        for row in range(0, len(results), 6):
            cols = st.columns(6)
            for i, m in enumerate(results[row:row+6]):
                with cols[i]:
                    poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}"
                    st.markdown(f"""
                    <div class="movie-card">
                        <img src="{poster}" style="width:100%;height:220px;object-fit:cover">
                        <div style="padding:10px">
                            <b style="font-size:12px">{m['title']}</b>
                            <p style="color:#E50914;font-size:11px">⭐ {m['vote_average']}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("Detail", key=f"top_{row}_{i}_{m['id']}"):
                        st.session_state.search_query = m["title"]
                        st.session_state.active_tab = "🔍 Discover"
                        st.rerun()

# ================================================================
# TAB: WATCHLIST
# ================================================================

elif st.session_state.active_tab == "📋 Watchlist":

    st.subheader("📋 Watchlist Kamu")

    if not st.session_state.watchlist:
        st.info("Watchlist masih kosong. Tambahkan film dari halaman Discover!")
    else:
        st.caption(f"{len(st.session_state.watchlist)} film tersimpan")
        cols = st.columns(4)
        for i, m in enumerate(st.session_state.watchlist):
            with cols[i % 4]:
                poster = f"https://image.tmdb.org/t/p/w500{m['poster_path']}" if m.get("poster_path") else ""
                user_r = st.session_state.user_ratings.get(m["title"], 0)
                stars = "⭐" * user_r if user_r else ""
                st.markdown(f"""
                <div class="watchlist-card">
                    <img src="{poster}" style="width:100%;height:250px;object-fit:cover">
                    <div style="padding:12px">
                        <b>{m['title']}</b><br>
                        <span style="color:#E50914;font-size:12px">⭐ {m['vote_average']}</span>
                        &nbsp; <span style="font-size:12px;color:#aaa">{m.get('release_date','')[:4]}</span>
                        <br><span style="font-size:13px">{stars}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Detail", key=f"wl_detail_{i}"):
                        st.session_state.search_query = m["title"]
                        st.session_state.active_tab = "🔍 Discover"
                        st.rerun()
                with c2:
                    if st.button("🗑️", key=f"wl_del_{i}"):
                        st.session_state.watchlist.pop(i)
                        st.rerun()

# ================================================================
# TAB: MY RATINGS
# ================================================================

elif st.session_state.active_tab == "⭐ My Ratings":

    st.subheader("⭐ Film yang Sudah Kamu Rating")

    if not st.session_state.user_ratings:
        st.info("Belum ada rating. Beri rating film dari halaman Discover!")
    else:
        ratings = st.session_state.user_ratings
        avg = sum(ratings.values()) / len(ratings)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Film Dirating", len(ratings))
        c2.metric("Rata-rata Rating", f"{avg:.1f} ⭐")
        c3.metric("Rating Tertinggi", f"{max(ratings.values())} ⭐")

        st.divider()

        sorted_ratings = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        for title, rating in sorted_ratings:
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.write(f"🎬 **{title}**")
            with col2:
                st.write("⭐" * rating)
            with col3:
                if st.button("Cari", key=f"rate_search_{title}"):
                    st.session_state.search_query = title
                    st.session_state.active_tab = "🔍 Discover"
                    st.rerun()

# ---------------- FOOTER ----------------

st.markdown(
    "<center style='opacity:0.5;font-size:12px;margin-top:40px'>Made by Rahmadtzy • CineMatch 2026</center>",
    unsafe_allow_html=True
)
