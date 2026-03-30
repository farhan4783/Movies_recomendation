"""
TMDB Client for Movie Maverick
Improvements over previous version:
  - In-memory TTL cache (_SimpleCache) eliminates redundant API calls
  - ThreadPoolExecutor parallelises watch-provider fetches (was sequential)
  - Consistent timeout on all requests
"""

import requests
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# ---------------------------------------------------------------------------
# Simple in-memory TTL cache (no Redis needed)
# ---------------------------------------------------------------------------

class _SimpleCache:
    """Thread-safe dict-based TTL cache."""

    def __init__(self):
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._data[key]
                return None
            return value

    def set(self, key, value, ttl: int):
        with self._lock:
            self._data[key] = (value, time.time() + ttl)

    def delete(self, key):
        with self._lock:
            self._data.pop(key, None)


_cache = _SimpleCache()

# TTL constants (seconds)
TTL_SEARCH = 4 * 3600       # 4 hours for title -> basic details
TTL_PROVIDERS = 12 * 3600   # 12 hours for watch providers
TTL_TRENDING = 30 * 60      # 30 min for trending list
TTL_POPULAR = 60 * 60       # 1 hour  for popular list
TTL_FULL = 2 * 3600         # 2 hours for full movie details


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get(url, params, timeout=7):
    """Thin wrapper around requests.get with a consistent timeout."""
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_watch_providers(movie_id, region="US"):
    """
    Returns streaming/rent/buy options for a movie.
    Results are cached for TTL_PROVIDERS seconds.
    """
    if not TMDB_API_KEY or not movie_id:
        return None

    cache_key = f"providers:{movie_id}:{region}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/movie/{movie_id}/watch/providers",
        {"api_key": TMDB_API_KEY},
    )

    providers_data = data.get("results", {}).get(region, {})

    def _fmt(providers):
        return [
            {
                "name": p.get("provider_name"),
                "logo": f"{IMAGE_BASE_URL}{p['logo_path']}" if p.get("logo_path") else None,
            }
            for p in providers
        ]

    result = {
        "link": providers_data.get("link"),
        "flatrate": _fmt(providers_data.get("flatrate", [])),
        "rent": _fmt(providers_data.get("rent", [])),
        "buy": _fmt(providers_data.get("buy", [])),
    }

    _cache.set(cache_key, result, TTL_PROVIDERS)
    return result


def fetch_movie_details(title):
    """
    Basic movie details (used on cards). Cached for TTL_SEARCH.
    Watch-providers are fetched in parallel after the search resolves.
    """
    if not TMDB_API_KEY or not title:
        return None

    cache_key = f"search:{title.lower().strip()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/search/movie",
        {"api_key": TMDB_API_KEY, "query": title},
    )
    results = data.get("results")
    if not results:
        _cache.set(cache_key, None, 600)  # cache misses for 10 min
        return None

    movie = results[0]
    movie_id = movie.get("id")
    providers = fetch_watch_providers(movie_id)  # might be cached already

    result = {
        "title": movie.get("title"),
        "poster_path": f"{IMAGE_BASE_URL}{movie['poster_path']}" if movie.get("poster_path") else None,
        "overview": movie.get("overview"),
        "release_date": movie.get("release_date"),
        "vote_average": movie.get("vote_average"),
        "id": movie_id,
        "watch_providers": providers,
    }
    _cache.set(cache_key, result, TTL_SEARCH)
    return result


def fetch_movie_details_batch(titles, max_workers=8):
    """
    Fetch basic movie details for a list of titles in parallel.
    Returns a list in the same order as input (None where fetch failed).
    """
    results = [None] * len(titles)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(fetch_movie_details, t): i for i, t in enumerate(titles)}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = None
    return results


def fetch_popular_movies(page=1):
    """Popular movies from TMDB. Watch providers fetched in parallel."""
    if not TMDB_API_KEY:
        return []

    cache_key = f"popular:{page}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/movie/popular",
        {"api_key": TMDB_API_KEY, "language": "en-US", "page": page},
    )
    items = data.get("results", [])

    # Fetch providers for all movies in parallel
    movie_ids = [item.get("id") for item in items]
    providers_list = _fetch_providers_parallel(movie_ids)

    movies = []
    for item, providers in zip(items, providers_list):
        movies.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "overview": item.get("overview"),
            "poster_path": f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get("poster_path") else None,
            "vote_average": item.get("vote_average"),
            "release_date": item.get("release_date"),
            "watch_providers": providers,
        })

    _cache.set(cache_key, movies, TTL_POPULAR)
    return movies


def fetch_trending_movies(time_window="week"):
    """Trending movies from TMDB. Watch providers fetched in parallel."""
    if not TMDB_API_KEY:
        return []

    cache_key = f"trending:{time_window}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/trending/movie/{time_window}",
        {"api_key": TMDB_API_KEY, "language": "en-US"},
    )
    items = data.get("results", [])[:12]

    movie_ids = [item.get("id") for item in items]
    providers_list = _fetch_providers_parallel(movie_ids)

    movies = []
    for item, providers in zip(items, providers_list):
        movies.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "overview": item.get("overview"),
            "poster_path": f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get("poster_path") else None,
            "vote_average": round(item.get("vote_average", 0), 1),
            "release_date": item.get("release_date", ""),
            "watch_providers": providers,
        })

    _cache.set(cache_key, movies, TTL_TRENDING)
    return movies


def fetch_full_movie_details(title):
    """
    Full movie details by title: cast, trailer, similar, watch providers.
    First resolves title to ID via search, then fetches full record.
    """
    if not TMDB_API_KEY or not title:
        return None

    cache_key = f"full_title:{title.lower().strip()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(f"{BASE_URL}/search/movie", {"api_key": TMDB_API_KEY, "query": title})
    if not data.get("results"):
        return None

    movie_id = data["results"][0]["id"]
    result = fetch_full_movie_details_by_id(movie_id)

    if result:
        _cache.set(cache_key, result, TTL_FULL)
    return result


def fetch_full_movie_details_by_id(tmdb_id):
    """Full movie details by TMDB ID. Cached for TTL_FULL."""
    if not TMDB_API_KEY or not tmdb_id:
        return None

    cache_key = f"full_id:{tmdb_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/movie/{tmdb_id}",
        {"api_key": TMDB_API_KEY, "append_to_response": "credits,videos,similar,recommendations"},
        timeout=10,
    )

    if data.get("status_code") == 34 or not data.get("id"):
        return None

    # Cast (top 10)
    cast = [
        {
            "id": m.get("id"),
            "name": m.get("name"),
            "character": m.get("character"),
            "profile_path": f"{IMAGE_BASE_URL}{m['profile_path']}" if m.get("profile_path") else None,
        }
        for m in data.get("credits", {}).get("cast", [])[:10]
    ]

    # Trailer
    trailer_key = next(
        (v["key"] for v in data.get("videos", {}).get("results", [])
         if v.get("type") == "Trailer" and v.get("site") == "YouTube"),
        None,
    )

    watch_providers = fetch_watch_providers(tmdb_id)

    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "overview": data.get("overview"),
        "poster_path": f"{IMAGE_BASE_URL}{data['poster_path']}" if data.get("poster_path") else None,
        "backdrop_path": f"https://image.tmdb.org/t/p/original{data['backdrop_path']}" if data.get("backdrop_path") else None,
        "release_date": data.get("release_date"),
        "vote_average": data.get("vote_average"),
        "runtime": data.get("runtime"),
        "genres": [g["name"] for g in data.get("genres", [])],
        "tagline": data.get("tagline"),
        "cast": cast,
        "trailer_url": f"https://www.youtube.com/embed/{trailer_key}" if trailer_key else None,
        "similar": data.get("similar", {}).get("results", [])[:6],
        "watch_providers": watch_providers,
    }

    _cache.set(cache_key, result, TTL_FULL)
    return result


def fetch_person_details(person_id):
    """Full person (actor/director) details by TMDB ID. Cached for TTL_FULL."""
    if not TMDB_API_KEY or not person_id:
        return None

    cache_key = f"person:{person_id}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    data = _get(
        f"{BASE_URL}/person/{person_id}",
        {"api_key": TMDB_API_KEY, "append_to_response": "combined_credits"},
        timeout=10,
    )

    if data.get("status_code") == 34 or not data.get("id"):
        return None

    credits_data = data.get("combined_credits", {})
    cast_credits = credits_data.get("cast", [])
    
    # Sort cast credits by popularity
    cast_credits_sorted = sorted(
        [c for c in cast_credits if c.get("poster_path")], 
        key=lambda x: x.get("popularity", 0), 
        reverse=True
    )[:15]

    known_for = [
        {
            "id": c.get("id"),
            "title": c.get("title") or c.get("name"),
            "poster_path": f"{IMAGE_BASE_URL}{c['poster_path']}" if c.get("poster_path") else None,
            "release_date": c.get("release_date") or c.get("first_air_date", ""),
            "vote_average": round(c.get("vote_average", 0), 1),
            "media_type": c.get("media_type", "movie"),
            "character": c.get("character", ""),
        }
        for c in cast_credits_sorted
    ]

    result = {
        "id": data.get("id"),
        "name": data.get("name"),
        "biography": data.get("biography"),
        "profile_path": f"{IMAGE_BASE_URL}{data['profile_path']}" if data.get("profile_path") else None,
        "birthday": data.get("birthday"),
        "deathday": data.get("deathday"),
        "place_of_birth": data.get("place_of_birth"),
        "known_for_department": data.get("known_for_department"),
        "known_for": known_for,
    }

    _cache.set(cache_key, result, TTL_FULL)
    return result



def search_movies(query, page=1):
    """Live search / autocomplete — lightweight, short results."""
    if not TMDB_API_KEY or not query:
        return []

    data = _get(
        f"{BASE_URL}/search/movie",
        {"api_key": TMDB_API_KEY, "query": query, "page": page, "language": "en-US"},
        timeout=5,
    )

    return [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "poster_path": f"{IMAGE_BASE_URL}{item['poster_path']}" if item.get("poster_path") else None,
            "release_date": item.get("release_date", ""),
            "vote_average": round(item.get("vote_average", 0), 1),
        }
        for item in data.get("results", [])[:8]
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_providers_parallel(movie_ids, max_workers=8):
    """Fetch watch providers for multiple movie IDs in parallel."""
    results = [None] * len(movie_ids)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_watch_providers, mid): i
            for i, mid in enumerate(movie_ids) if mid
        }
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                results[idx] = future.result()
            except Exception:
                results[idx] = None
    return results


# ---------------------------------------------------------------------------
# Genre Map & Discover by Genre
# ---------------------------------------------------------------------------

GENRE_MAP = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "Sci-Fi": 878,
    "TV Movie": 10770,
    "Thriller": 53,
    "War": 10752,
    "Western": 37,
}


def fetch_movies_by_genre(genre_id: int, page: int = 1) -> list:
    """Fetch movies from TMDB /discover/movie filtered by genre_id."""
    cache_key = f"discover_genre_{genre_id}_p{page}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://api.themoviedb.org/3/discover/movie",
            params={
                "api_key": api_key,
                "with_genres": genre_id,
                "sort_by": "popularity.desc",
                "page": page,
                "language": "en-US",
                "include_adult": "false",
            },
            timeout=6,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "id": m.get("id"),
                "title": m.get("title"),
                "poster_path": f"{IMAGE_BASE_URL}{m['poster_path']}" if m.get("poster_path") else None,
                "release_date": m.get("release_date", ""),
                "vote_average": round(m.get("vote_average", 0), 1),
                "overview": m.get("overview", ""),
            }
            for m in data.get("results", [])[:20]
        ]
        _cache.set(cache_key, results, ttl=1800)
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Discover by Country
# ---------------------------------------------------------------------------

COUNTRY_MAP = {
    "US": "United States", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IN": "India", "JP": "Japan", "KR": "South Korea",
    "CN": "China", "BR": "Brazil", "MX": "Mexico", "IT": "Italy",
    "ES": "Spain", "AU": "Australia", "CA": "Canada", "RU": "Russia",
    "SE": "Sweden", "DK": "Denmark", "NO": "Norway", "FI": "Finland",
    "AR": "Argentina", "TR": "Turkey", "TH": "Thailand", "NG": "Nigeria",
    "EG": "Egypt", "ZA": "South Africa", "PL": "Poland", "NL": "Netherlands",
    "IE": "Ireland", "NZ": "New Zealand", "HK": "Hong Kong", "TW": "Taiwan",
    "IR": "Iran", "CO": "Colombia", "CL": "Chile", "PH": "Philippines",
}


def fetch_movies_by_country(country_code: str, page: int = 1) -> list:
    """Fetch popular movies from a specific country using TMDB discover."""
    cache_key = f"discover_country_{country_code}_p{page}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    if not TMDB_API_KEY:
        return []

    try:
        resp = requests.get(
            f"{BASE_URL}/discover/movie",
            params={
                "api_key": TMDB_API_KEY,
                "with_origin_country": country_code,
                "sort_by": "vote_count.desc",
                "page": page,
                "language": "en-US",
                "include_adult": "false",
                "vote_count.gte": 50,
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "id": m.get("id"),
                "title": m.get("title"),
                "poster_path": f"{IMAGE_BASE_URL}{m['poster_path']}" if m.get("poster_path") else None,
                "release_date": m.get("release_date", ""),
                "vote_average": round(m.get("vote_average", 0), 1),
                "overview": m.get("overview", ""),
            }
            for m in data.get("results", [])[:15]
        ]
        _cache.set(cache_key, results, ttl=3600)
        return results
    except Exception:
        return []
