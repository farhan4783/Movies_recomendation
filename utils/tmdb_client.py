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
