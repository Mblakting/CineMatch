# -*- coding: utf-8 -*-
"""
Realtime AI ranking engine for CineMatch.

The engine does not use a bundled dataset. It builds features from live TMDB
responses, ranks candidates with a custom weighted model, and can adapt its
weights from feedback collected during the current Streamlit session.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any


STOP_WORDS = {
    "about", "after", "again", "against", "all", "also", "and", "are", "as",
    "back", "been", "but", "can", "for", "from", "has", "have", "her", "his",
    "into", "its", "life", "new", "not", "now", "old", "one", "only", "out",
    "she", "that", "the", "their", "them", "then", "there", "they", "this",
    "through", "to", "when", "where", "while", "who", "will", "with", "world",
    "you", "young",
}


BASE_WEIGHTS = {
    "tmdb_signal": 0.15,
    "genre_match": 0.20,
    "keyword_match": 0.18,
    "story_match": 0.15,
    "people_match": 0.12,
    "quality": 0.07,
    "era_match": 0.05,
    "franchise_match": 0.08,
}


@dataclass(frozen=True)
class MovieProfile:
    movie_id: int
    title: str
    base_name: str
    year: int
    rating: float
    vote_count: int
    genre_ids: frozenset[int]
    genre_names: tuple[str, ...]
    keyword_tokens: tuple[str, ...]
    story_tokens: tuple[str, ...]
    people_tokens: tuple[str, ...]


def tokenize_text(text: Any) -> tuple[str, ...]:
    words = re.findall(r"[a-z0-9][a-z0-9']+", str(text or "").casefold())
    return tuple(
        word
        for word in words
        if len(word) > 2 and word not in STOP_WORDS
    )


def extract_base_name(title: str) -> str:
    title_lower = str(title or "").casefold()
    patterns = [
        r"\s+(part|chapter|episode)\s+\d+",
        r"\s+\d+(?:st|nd|rd|th)?\s*$",
        r"\s+(\d+)$",
        r"\s+-\s+\d+\s*$",
    ]
    result = title_lower
    for pattern in patterns:
        result = re.sub(pattern, "", result)
    return re.sub(r"[^\w\s]", "", result).strip()


def compact_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).casefold())


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_year(value: Any) -> int:
    try:
        return int(str(value or "0")[:4])
    except (TypeError, ValueError):
        return 0


def sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    cleaned = {
        key: max(0.02, float(value))
        for key, value in weights.items()
        if key in BASE_WEIGHTS
    }
    total = sum(cleaned.values()) or 1.0
    return {key: value / total for key, value in cleaned.items()}


def jaccard(left: set[Any] | frozenset[Any], right: set[Any] | frozenset[Any]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def overlap(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / min(len(left_set), len(right_set))


def term_frequency(tokens: tuple[str, ...], idf: dict[str, float]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1

    total = len(tokens) or 1
    return {
        token: (count / total) * idf.get(token, 1.0)
        for token, count in counts.items()
    }


def cosine_similarity(
    left_tokens: tuple[str, ...],
    right_tokens: tuple[str, ...],
    idf: dict[str, float],
) -> float:
    left_vec = term_frequency(left_tokens, idf)
    right_vec = term_frequency(right_tokens, idf)
    if not left_vec or not right_vec:
        return 0.0

    shared = set(left_vec) & set(right_vec)
    dot = sum(left_vec[token] * right_vec[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left_vec.values()))
    right_norm = math.sqrt(sum(value * value for value in right_vec.values()))
    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def build_idf(profiles: list[MovieProfile]) -> dict[str, float]:
    documents = [
        set(profile.story_tokens + profile.keyword_tokens)
        for profile in profiles
    ]
    total_docs = len(documents) or 1
    document_frequency: dict[str, int] = {}

    for document in documents:
        for token in document:
            document_frequency[token] = document_frequency.get(token, 0) + 1

    return {
        token: math.log((1 + total_docs) / (1 + count)) + 1
        for token, count in document_frequency.items()
    }


def extract_genres(movie: dict[str, Any]) -> tuple[frozenset[int], tuple[str, ...]]:
    if movie.get("genres"):
        genre_ids = []
        genre_names = []
        for genre in movie.get("genres", []):
            if not isinstance(genre, dict):
                continue
            if genre.get("id") is not None:
                genre_ids.append(int(genre["id"]))
            if genre.get("name"):
                genre_names.append(str(genre["name"]))
        return frozenset(genre_ids), tuple(genre_names)

    return frozenset(int(genre_id) for genre_id in movie.get("genre_ids", [])), ()


def extract_keywords(movie: dict[str, Any]) -> tuple[str, ...]:
    keyword_data = movie.get("keywords") or {}
    keywords = keyword_data.get("keywords") or keyword_data.get("results") or []
    tokens = []
    for keyword in keywords:
        if isinstance(keyword, dict):
            tokens.extend(tokenize_text(keyword.get("name", "")))
    return tuple(tokens)


def extract_people(movie: dict[str, Any]) -> tuple[str, ...]:
    credits = movie.get("credits") or {}
    cast = credits.get("cast", [])[:8]
    crew = [
        member
        for member in credits.get("crew", [])
        if member.get("job") in {"Director", "Writer", "Screenplay", "Story"}
    ][:8]

    people = []
    for person in [*cast, *crew]:
        key = compact_name(person.get("name", ""))
        if key:
            people.append(key)

    return tuple(dict.fromkeys(people))


def movie_profile(movie: dict[str, Any]) -> MovieProfile:
    genre_ids, genre_names = extract_genres(movie)
    keyword_tokens = extract_keywords(movie)
    story_tokens = tokenize_text(" ".join([
        str(movie.get("title") or ""),
        str(movie.get("tagline") or ""),
        str(movie.get("overview") or ""),
    ]))

    return MovieProfile(
        movie_id=int(movie.get("id") or 0),
        title=str(movie.get("title") or movie.get("name") or "Untitled"),
        base_name=extract_base_name(movie.get("title") or ""),
        year=safe_year(movie.get("release_date")),
        rating=safe_float(movie.get("vote_average")),
        vote_count=int(movie.get("vote_count") or 0),
        genre_ids=genre_ids,
        genre_names=genre_names,
        keyword_tokens=keyword_tokens,
        story_tokens=story_tokens,
        people_tokens=extract_people(movie),
    )


def quality_signal(profile: MovieProfile) -> float:
    rating = profile.rating / 10
    vote_confidence = min(profile.vote_count / 700, 1.0)
    return rating * (0.35 + (vote_confidence * 0.65))


def era_signal(source: MovieProfile, candidate: MovieProfile) -> float:
    if not source.year or not candidate.year:
        return 0.5
    return max(0.0, 1 - (abs(source.year - candidate.year) / 45))


def franchise_signal(source: MovieProfile, candidate: MovieProfile) -> float:
    if not source.base_name or not candidate.base_name:
        return 0.0
    similarity = 1.0 if source.base_name == candidate.base_name else 0.0
    if similarity and source.year and candidate.year:
        year_diff = abs(source.year - candidate.year)
        if year_diff <= 3:
            return 1.0
        return 0.75
    return similarity


def explain_recommendation(rec: dict[str, Any], source_title: str) -> dict[str, Any]:
    """Generate human-readable explanation for why a movie was recommended."""
    reasons = []
    highlights = []

    genre_match = rec.get("genre_match", 0)
    story_match = rec.get("story_match", 0)
    keyword_match = rec.get("keyword_match", 0)
    people_match = rec.get("people_match", 0)
    franchise_match = rec.get("franchise_match", 0)
    ai_score = rec.get("ai_score", 0)

    if franchise_match >= 50:
        reasons.append("🎬 Masih satu franchise / seri yang sama")
        highlights.append("franchise")
    if genre_match >= 70:
        reasons.append(f"🎭 Genre sangat cocok ({genre_match:.0f}% sama)")
        highlights.append("genre")
    elif genre_match >= 40:
        reasons.append(f"🎭 Genre mirip ({genre_match:.0f}% sama)")
    if story_match >= 50:
        reasons.append(f"📖 Cerita dan tema sangat mirip ({story_match:.0f}% sama)")
        highlights.append("story")
    elif story_match >= 25:
        reasons.append(f"📖 Tema cerita ada kemiripan ({story_match:.0f}%)")
    if keyword_match >= 40:
        reasons.append(f"🔑 Kata kunci film banyak yang sama ({keyword_match:.0f}%)")
    if people_match >= 30:
        reasons.append(f"🎥 Ada aktor atau sutradara yang sama ({people_match:.0f}%)")
        highlights.append("people")
    if rec.get("vote_average", 0) >= 7.5:
        reasons.append(f"⭐ Film ini sangat disukai penonton ({rec['vote_average']:.1f}/10)")

    if not reasons:
        reasons.append("🤖 AI menemukan pola kesamaan tersembunyi dengan film ini")

    if ai_score >= 75:
        verdict = "Sangat Direkomendasikan"
        verdict_color = "#00c864"
    elif ai_score >= 55:
        verdict = "Direkomendasikan"
        verdict_color = "#ffb703"
    else:
        verdict = "Mungkin Cocok"
        verdict_color = "#aaaaaa"

    return {
        "reasons": reasons[:3],
        "verdict": verdict,
        "verdict_color": verdict_color,
        "highlights": highlights,
    }


@dataclass
class TasteProfile:
    """Aggregated user taste built from liked/disliked feedback."""
    liked_genre_ids: dict[int, float]       # genre_id -> weight
    liked_keyword_tokens: dict[str, float]  # token -> weight
    liked_story_tokens: dict[str, float]    # token -> weight
    avg_era: float                          # weighted average year
    disliked_genre_ids: set[int]            # genres to penalise
    disliked_keyword_tokens: set[str]       # keywords to penalise
    liked_movie_ids: set[int]
    disliked_movie_ids: set[int]
    top_genre_ids: list[int]                # top-3 liked genres for TMDB query


def build_taste_profile(
    feedback_samples: list[dict[str, Any]],
    liked_movie_details: list[dict[str, Any]],
) -> TasteProfile | None:
    """
    Build a TasteProfile from feedback + the actual movie details of liked films.
    Returns None if there are no liked films.
    """
    liked_ids = {s["movie_id"] for s in feedback_samples if s["label"] == "positive"}
    disliked_ids = {s["movie_id"] for s in feedback_samples if s["label"] == "negative"}

    if not liked_ids:
        return None

    liked_genre_ids: dict[int, float] = {}
    liked_keyword_tokens: dict[str, float] = {}
    liked_story_tokens: dict[str, float] = {}
    era_sum = 0.0
    era_count = 0

    disliked_genre_ids: set[int] = set()
    disliked_keyword_tokens: set[str] = set()

    # Build liked profile from actual movie details
    for movie in liked_movie_details:
        if int(movie.get("id") or 0) not in liked_ids:
            continue
        profile = movie_profile(movie)
        for gid in profile.genre_ids:
            liked_genre_ids[gid] = liked_genre_ids.get(gid, 0.0) + 1.0
        for token in profile.keyword_tokens:
            liked_keyword_tokens[token] = liked_keyword_tokens.get(token, 0.0) + 1.0
        for token in profile.story_tokens:
            liked_story_tokens[token] = liked_story_tokens.get(token, 0.0) + 1.0
        if profile.year:
            era_sum += profile.year
            era_count += 1

    # Build disliked profile — only penalise genres/keywords NOT present in liked
    for movie in liked_movie_details:
        if int(movie.get("id") or 0) not in disliked_ids:
            continue
        profile = movie_profile(movie)
        for gid in profile.genre_ids:
            if gid not in liked_genre_ids:
                disliked_genre_ids.add(gid)
        for token in profile.keyword_tokens:
            if token not in liked_keyword_tokens:
                disliked_keyword_tokens.add(token)

    avg_era = era_sum / era_count if era_count else 0.0

    # Top genres by frequency for TMDB discovery query
    top_genre_ids = [
        gid for gid, _ in sorted(liked_genre_ids.items(), key=lambda x: -x[1])[:3]
    ]

    return TasteProfile(
        liked_genre_ids=liked_genre_ids,
        liked_keyword_tokens=liked_keyword_tokens,
        liked_story_tokens=liked_story_tokens,
        avg_era=avg_era,
        disliked_genre_ids=disliked_genre_ids,
        disliked_keyword_tokens=disliked_keyword_tokens,
        liked_movie_ids=liked_ids,
        disliked_movie_ids=disliked_ids,
        top_genre_ids=top_genre_ids,
    )


class RealtimeMovieAI:
    """Custom realtime ranker with simple online learning."""

    def learned_weights(self, feedback_samples: list[dict[str, Any]] | None = None) -> dict[str, float]:
        weights = dict(BASE_WEIGHTS)
        learning_rate = 0.18

        for sample in feedback_samples or []:
            features = sample.get("features") or {}
            label = 1.0 if sample.get("label") == "positive" else 0.0
            raw_score = sum(weights.get(key, 0.0) * safe_float(features.get(key)) for key in BASE_WEIGHTS)
            predicted = sigmoid((raw_score - 0.5) * 5)
            error = label - predicted

            for key in BASE_WEIGHTS:
                weights[key] = weights.get(key, 0.0) + (learning_rate * error * safe_float(features.get(key)))

            weights = normalize_weights(weights)

        return normalize_weights(weights)

    def rank(
        self,
        source_movie: dict[str, Any],
        candidate_movies: list[dict[str, Any]],
        feedback_samples: list[dict[str, Any]] | None = None,
        min_year: int = 1990,
        min_rating: float = 5.0,
        limit: int = 12,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source = movie_profile(source_movie)
        candidate_pairs = [
            (movie, movie_profile(movie))
            for movie in candidate_movies
            if int(movie.get("id") or 0) != source.movie_id
        ]
        idf = build_idf([source, *(profile for _, profile in candidate_pairs)])
        weights = self.learned_weights(feedback_samples)
        ranked = []

        for movie, candidate in candidate_pairs:
            if not movie.get("poster_path"):
                continue
            if candidate.year and candidate.year < min_year:
                continue
            if candidate.rating < min_rating:
                continue

            features = {
                "tmdb_signal": safe_float(movie.get("_tmdb_signal"), 0.55),
                "genre_match": jaccard(source.genre_ids, candidate.genre_ids),
                "keyword_match": overlap(source.keyword_tokens, candidate.keyword_tokens or candidate.story_tokens),
                "story_match": cosine_similarity(source.story_tokens, candidate.story_tokens, idf),
                "people_match": overlap(source.people_tokens, candidate.people_tokens),
                "quality": quality_signal(candidate),
                "era_match": era_signal(source, candidate),
                "franchise_match": franchise_signal(source, candidate),
            }

            score = sum(weights[key] * features[key] for key in BASE_WEIGHTS)
            evidence = max(
                features["keyword_match"],
                features["story_match"],
                features["people_match"],
                features["franchise_match"],
            )
            if source.genre_ids and candidate.genre_ids and features["genre_match"] == 0:
                if features["franchise_match"] < 0.5:
                    score *= 0.62
            if evidence < 0.04:
                score *= 0.78

            ranked.append({
                "id": candidate.movie_id,
                "title": candidate.title,
                "poster_path": movie.get("poster_path"),
                "vote_average": candidate.rating,
                "release_date": movie.get("release_date", ""),
                "genres": candidate.genre_names,
                "sources": movie.get("_sources", ("TMDB live",)),
                "ai_score": round(min(score * 100, 99), 1),
                "genre_match": round(features["genre_match"] * 100, 1),
                "keyword_match": round(features["keyword_match"] * 100, 1),
                "story_match": round(features["story_match"] * 100, 1),
                "people_match": round(features["people_match"] * 100, 1),
                "franchise_match": round(features["franchise_match"] * 100, 1),
                "features": {key: round(value, 4) for key, value in features.items()},
                "_rank_score": score,
            })

        ranked.sort(key=lambda item: item["_rank_score"], reverse=True)
        model_info = {
            "weights": {key: round(value, 3) for key, value in weights.items()},
            "feedback_count": len(feedback_samples or []),
            "source_profile": source,
        }
        return ranked[:limit], model_info

    def rank_from_taste(
        self,
        taste: TasteProfile,
        candidate_movies: list[dict[str, Any]],
        feedback_samples: list[dict[str, Any]] | None = None,
        min_year: int = 1970,
        min_rating: float = 5.0,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """
        Rank candidates against the user's aggregated taste profile.
        Candidates that match liked genres/keywords score higher;
        candidates matching disliked-only patterns are penalised.
        Films already in feedback are excluded.
        """
        already_seen = taste.liked_movie_ids | taste.disliked_movie_ids
        weights = self.learned_weights(feedback_samples)

        # Build a pseudo IDF from liked story tokens
        liked_tokens_tuple = tuple(taste.liked_story_tokens.keys())

        ranked = []
        for movie in candidate_movies:
            movie_id = int(movie.get("id") or 0)
            if not movie_id or movie_id in already_seen:
                continue
            if not movie.get("poster_path"):
                continue

            profile = movie_profile(movie)

            if profile.year and profile.year < min_year:
                continue
            if profile.rating < min_rating:
                continue

            # Genre match against liked genres (weighted Jaccard)
            liked_genre_set = set(taste.liked_genre_ids.keys())
            genre_score = jaccard(liked_genre_set, profile.genre_ids)

            # Keyword overlap against liked keywords
            liked_kw_set = set(taste.liked_keyword_tokens.keys())
            kw_score = (
                len(liked_kw_set & set(profile.keyword_tokens)) / min(len(liked_kw_set), max(len(profile.keyword_tokens), 1))
                if liked_kw_set and profile.keyword_tokens else 0.0
            )

            # Story cosine against aggregated liked story tokens
            story_score = 0.0
            if liked_tokens_tuple and profile.story_tokens:
                idf: dict[str, float] = {t: 1.0 for t in liked_tokens_tuple}
                story_score = cosine_similarity(liked_tokens_tuple, profile.story_tokens, idf)

            # Era proximity to user's average liked era
            era_score = 0.5
            if taste.avg_era and profile.year:
                era_score = max(0.0, 1 - abs(taste.avg_era - profile.year) / 40)

            quality = quality_signal(profile)
            tmdb_signal = safe_float(movie.get("_tmdb_signal"), 0.55)

            score = (
                weights["genre_match"] * genre_score
                + weights["keyword_match"] * kw_score
                + weights["story_match"] * story_score
                + weights["era_match"] * era_score
                + weights["quality"] * quality
                + weights["tmdb_signal"] * tmdb_signal
            )

            # Penalise if candidate matches disliked-only patterns
            disliked_genre_overlap = profile.genre_ids & taste.disliked_genre_ids
            if disliked_genre_overlap and not (profile.genre_ids & liked_genre_set):
                score *= 0.45
            disliked_kw_overlap = set(profile.keyword_tokens) & taste.disliked_keyword_tokens
            if len(disliked_kw_overlap) > 2:
                score *= 0.70

            # Must have at least some signal to avoid random noise
            if genre_score == 0 and kw_score < 0.05 and story_score < 0.05:
                score *= 0.50

            ranked.append({
                "id": profile.movie_id,
                "title": profile.title,
                "poster_path": movie.get("poster_path"),
                "vote_average": profile.rating,
                "release_date": movie.get("release_date", ""),
                "genres": profile.genre_names,
                "ai_score": round(min(score * 100, 99), 1),
                "genre_match": round(genre_score * 100, 1),
                "keyword_match": round(kw_score * 100, 1),
                "story_match": round(story_score * 100, 1),
                "people_match": 0.0,
                "franchise_match": 0.0,
                "features": {
                    "genre_match": round(genre_score, 4),
                    "keyword_match": round(kw_score, 4),
                    "story_match": round(story_score, 4),
                    "era_match": round(era_score, 4),
                    "quality": round(quality, 4),
                    "tmdb_signal": round(tmdb_signal, 4),
                    "people_match": 0.0,
                    "franchise_match": 0.0,
                },
                "_rank_score": score,
            })

        ranked.sort(key=lambda item: item["_rank_score"], reverse=True)
        return ranked[:limit]
