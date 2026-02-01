import requests
import os
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

def fetch_movie_details(title):
    """
    Fetches movie details (poster, overview, rating, etc.) from TMDB by title.
    """
    if not TMDB_API_KEY:
        return None

    try:
        # Search for the movie
        search_url = f"{BASE_URL}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": title
        }
        response = requests.get(search_url, params=params)
        data = response.json()

        if data.get("results"):
            movie = data["results"][0]
            return {
                "title": movie.get("title"),
                "poster_path": f"{IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get("poster_path") else None,
                "overview": movie.get("overview"),
                "release_date": movie.get("release_date"),
                "vote_average": movie.get("vote_average"),
                "id": movie.get("id")
            }
        return None
    except Exception as e:
        print(f"Error fetching details for {title}: {e}")
        return None

def fetch_popular_movies(page=1):
    """
    Fetches a list of popular movies from TMDB.
    """
    if not TMDB_API_KEY:
        return []

    try:
        url = f"{BASE_URL}/movie/popular"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "page": page
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        movies = []
        for item in data.get("results", []):
            movies.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "overview": item.get("overview"),
                "poster_path": f"{IMAGE_BASE_URL}{item.get('poster_path')}" if item.get("poster_path") else None,
                "vote_average": item.get("vote_average"),
                "release_date": item.get("release_date")
            })
        return movies
    except Exception as e:
        print(f"Error fetching popular movies: {e}")
        return []

def fetch_watch_providers(movie_id, region="US"):
    """
    Fetches streaming availability (watch providers) for a movie.
    Returns platforms where the movie is available to stream, rent, or buy.
    """
    if not TMDB_API_KEY:
        return None
    
    try:
        url = f"{BASE_URL}/movie/{movie_id}/watch/providers"
        params = {"api_key": TMDB_API_KEY}
        response = requests.get(url, params=params)
        data = response.json()
        
        # Get providers for specified region
        providers_data = data.get("results", {}).get(region, {})
        
        result = {
            "link": providers_data.get("link"),  # TMDB link to watch options
            "flatrate": [],  # Streaming (subscription)
            "rent": [],      # Rent options
            "buy": []        # Buy options
        }
        
        # Process streaming platforms
        for provider in providers_data.get("flatrate", []):
            result["flatrate"].append({
                "name": provider.get("provider_name"),
                "logo": f"{IMAGE_BASE_URL}{provider.get('logo_path')}" if provider.get("logo_path") else None
            })
            
        # Process rental options
        for provider in providers_data.get("rent", []):
            result["rent"].append({
                "name": provider.get("provider_name"),
                "logo": f"{IMAGE_BASE_URL}{provider.get('logo_path')}" if provider.get("logo_path") else None
            })
            
        # Process buy options
        for provider in providers_data.get("buy", []):
            result["buy"].append({
                "name": provider.get("provider_name"),
                "logo": f"{IMAGE_BASE_URL}{provider.get('logo_path')}" if provider.get("logo_path") else None
            })
        
        return result
    except Exception as e:
        print(f"Error fetching watch providers for movie {movie_id}: {e}")
        return None

def fetch_full_movie_details(title):
    """
    Fetches comprehensive movie details including cast, runtime, backdrop, and similar movies.
    First searches by title to get ID, then fetches full details.
    """
    if not TMDB_API_KEY:
        return None

    try:
        # 1. Search for ID
        search_url = f"{BASE_URL}/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": title}
        search_res = requests.get(search_url, params=params).json()
        
        if not search_res.get("results"):
            return None
            
        movie_id = search_res["results"][0]["id"]
        
        # 2. Get Full Details
        details_url = f"{BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits,videos,similar,recommendations"
        }
        data = requests.get(details_url, params=params).json()
        
        # Process Cast (Top 10)
        cast = []
        for member in data.get("credits", {}).get("cast", [])[:10]:
            cast.append({
                "name": member.get("name"),
                "character": member.get("character"),
                "profile_path": f"{IMAGE_BASE_URL}{member.get('profile_path')}" if member.get("profile_path") else None
            })
            
        # Process Videos (Trailer)
        trailer_key = None
        for video in data.get("videos", {}).get("results", []):
            if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                trailer_key = video.get("key")
                break
        
        # Get Watch Providers
        watch_providers = fetch_watch_providers(movie_id)
                
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "overview": data.get("overview"),
            "poster_path": f"{IMAGE_BASE_URL}{data.get('poster_path')}" if data.get('poster_path') else None,
            "backdrop_path": f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None,
            "release_date": data.get("release_date"),
            "vote_average": data.get("vote_average"),
            "runtime": data.get("runtime"),
            "genres": [g["name"] for g in data.get("genres", [])],
            "tagline": data.get("tagline"),
            "cast": cast,
            "trailer_url": f"https://www.youtube.com/embed/{trailer_key}" if trailer_key else None,
            "similar": data.get("similar", {}).get("results", [])[:6],
            "watch_providers": watch_providers
        }
    except Exception as e:
        print(f"Error fetching full details for {title}: {e}")
        return None
