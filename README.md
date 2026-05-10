# CineMatch

Realtime movie recommendation app built with Streamlit, TMDB, and a custom ML
ranker written in this project.

There is no bundled dataset or master movie database. Every recommendation is
calculated from live TMDB data when the user searches for a movie.

## What Makes It AI/ML?

CineMatch uses a self-made realtime ranking model:

- Live candidate collection from TMDB recommendations, similar movies, genre
  discovery, and keyword discovery
- Custom feature extraction for genre, keyword, story/overview, cast/crew,
  rating quality, and release-era similarity
- Manual TF-IDF cosine similarity for story matching
- Weighted ranking model written in `src/engines/realtime_ai_engine.py`
- Online learning from user feedback buttons during the current session

This is not a pre-trained deep learning model. It is a custom realtime ML
ranker that learns ranking weights from feedback.

## Quick Start

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python -m streamlit run src/main.py
```

Optional:

```bash
set TMDB_API_KEY=your_api_key
python -m streamlit run src/main.py
```

If `TMDB_API_KEY` is not set, the project uses the bundled API key from
`src/core/config.py`.

## Project Structure

```text
CineMatch/
├── src/
│   ├── main.py
│   ├── core/
│   │   └── config.py
│   └── engines/
│       └── realtime_ai_engine.py
├── assets/
├── docs/
├── requirements.txt
└── README.md
```

## Presentation Talking Point

"CineMatch tidak memakai dataset lokal. Data film diambil realtime dari TMDB,
lalu model ML buatan sendiri menghitung feature dan melakukan ranking. Modelnya
juga bisa belajar dari feedback user saat demo."
