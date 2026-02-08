import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

def get_weather_mood_modifier(lat=None, lon=None, city=None):
    """
    Fetches current weather and suggests mood modifiers.
    Returns weather condition and recommended mood adjustments.
    """
    if not OPENWEATHER_API_KEY:
        return {"weather": "unknown", "mood_suggestions": []}
    
    try:
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        
        # Build params based on available location data
        params = {"appid": OPENWEATHER_API_KEY, "units": "metric"}
        
        if lat and lon:
            params["lat"] = lat
            params["lon"] = lon
        elif city:
            params["q"] = city
        else:
            # Default to a major city if no location provided
            params["q"] = "New York"
        
        response = requests.get(base_url, params=params, timeout=5)
        data = response.json()
        
        if response.status_code != 200:
            return {"weather": "unknown", "mood_suggestions": []}
        
        weather_main = data.get("weather", [{}])[0].get("main", "").lower()
        weather_desc = data.get("weather", [{}])[0].get("description", "")
        temp = data.get("main", {}).get("temp", 0)
        
        # Map weather to mood suggestions
        mood_map = {
            "rain": ["cozy", "melancholic", "introspective", "romantic"],
            "drizzle": ["cozy", "calm", "romantic"],
            "thunderstorm": ["intense", "dramatic", "thrilling"],
            "snow": ["cozy", "nostalgic", "magical", "romantic"],
            "clear": ["uplifting", "adventurous", "energetic", "happy"],
            "clouds": ["contemplative", "calm", "mysterious"],
            "mist": ["mysterious", "atmospheric", "noir"],
            "fog": ["mysterious", "eerie", "atmospheric"]
        }
        
        # Temperature-based adjustments
        temp_moods = []
        if temp < 10:
            temp_moods = ["cozy", "warm-hearted"]
        elif temp > 30:
            temp_moods = ["light", "breezy", "summer-vibes"]
        
        mood_suggestions = mood_map.get(weather_main, ["any"])
        if temp_moods:
            mood_suggestions.extend(temp_moods)
        
        return {
            "weather": weather_main,
            "description": weather_desc,
            "temperature": temp,
            "mood_suggestions": list(set(mood_suggestions))  # Remove duplicates
        }
        
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return {"weather": "unknown", "mood_suggestions": []}


def get_time_based_suggestions():
    """
    Returns mood and genre suggestions based on current time of day.
    """
    current_hour = datetime.now().hour
    day_of_week = datetime.now().weekday()  # 0=Monday, 6=Sunday
    
    # Time of day mapping
    if 5 <= current_hour < 12:
        time_period = "morning"
        mood_suggestions = ["uplifting", "motivational", "light", "feel-good"]
        genre_suggestions = ["Comedy", "Animation", "Family", "Adventure"]
    elif 12 <= current_hour < 17:
        time_period = "afternoon"
        mood_suggestions = ["adventurous", "exciting", "engaging"]
        genre_suggestions = ["Action", "Adventure", "Sci-Fi", "Mystery"]
    elif 17 <= current_hour < 21:
        time_period = "evening"
        mood_suggestions = ["entertaining", "engaging", "social"]
        genre_suggestions = ["Drama", "Comedy", "Thriller", "Romance"]
    else:  # 21-5
        time_period = "night"
        mood_suggestions = ["intense", "thrilling", "atmospheric", "contemplative"]
        genre_suggestions = ["Horror", "Thriller", "Mystery", "Drama", "Noir"]
    
    # Weekend adjustments
    is_weekend = day_of_week >= 5
    if is_weekend:
        mood_suggestions.append("relaxed")
        genre_suggestions.append("Epic")
    
    return {
        "time_period": time_period,
        "hour": current_hour,
        "is_weekend": is_weekend,
        "mood_suggestions": mood_suggestions,
        "genre_suggestions": genre_suggestions
    }


def calculate_energy_level_match(energy_level, movie_runtime, movie_genres):
    """
    Calculates how well a movie matches the user's energy level.
    
    Args:
        energy_level (int): 1-5 scale (1=exhausted, 5=fully alert)
        movie_runtime (int): Runtime in minutes
        movie_genres (list): List of genre strings
    
    Returns:
        float: Match score 0-1
    """
    score = 1.0
    
    # Runtime considerations
    if energy_level <= 2:  # Low energy
        if movie_runtime > 150:  # Long movie
            score *= 0.5
        elif movie_runtime < 90:  # Short movie
            score *= 1.2
    elif energy_level >= 4:  # High energy
        if movie_runtime > 150:  # Can handle epics
            score *= 1.1
    
    # Genre complexity considerations
    complex_genres = ["Sci-Fi", "Mystery", "Thriller", "Crime", "Documentary"]
    simple_genres = ["Comedy", "Animation", "Romance", "Family"]
    
    if energy_level <= 2:  # Low energy - prefer simple
        if any(g in movie_genres for g in complex_genres):
            score *= 0.7
        if any(g in movie_genres for g in simple_genres):
            score *= 1.3
    elif energy_level >= 4:  # High energy - can handle complex
        if any(g in movie_genres for g in complex_genres):
            score *= 1.2
    
    return min(score, 1.5)  # Cap at 1.5x boost


def get_contextual_mood_recommendation(mood, weather_data=None, time_data=None, energy_level=3):
    """
    Combines user mood with contextual data to provide enhanced recommendations.
    
    Args:
        mood (str): User's selected mood
        weather_data (dict): Weather information
        time_data (dict): Time-based suggestions
        energy_level (int): User's energy level 1-5
    
    Returns:
        dict: Enhanced mood recommendation with context
    """
    recommendation = {
        "primary_mood": mood,
        "suggested_moods": [mood],
        "suggested_genres": [],
        "context_notes": []
    }
    
    # Add weather-based suggestions
    if weather_data and weather_data.get("mood_suggestions"):
        recommendation["suggested_moods"].extend(weather_data["mood_suggestions"][:2])
        recommendation["context_notes"].append(
            f"It's {weather_data.get('description', 'nice')} outside - perfect for {weather_data['mood_suggestions'][0]} movies"
        )
    
    # Add time-based suggestions
    if time_data:
        recommendation["suggested_moods"].extend(time_data["mood_suggestions"][:2])
        recommendation["suggested_genres"].extend(time_data["genre_suggestions"][:3])
        recommendation["context_notes"].append(
            f"It's {time_data['time_period']} - great time for {time_data['genre_suggestions'][0]} films"
        )
    
    # Add energy-based suggestions
    energy_map = {
        1: {"moods": ["comfort", "familiar"], "note": "Low energy detected - comfort watches recommended"},
        2: {"moods": ["light", "easy-going"], "note": "Relaxed mode - light entertainment suggested"},
        3: {"moods": ["balanced", "engaging"], "note": "Moderate energy - balanced recommendations"},
        4: {"moods": ["engaging", "exciting"], "note": "Good energy - ready for engaging content"},
        5: {"moods": ["intense", "complex"], "note": "High energy - perfect for complex narratives"}
    }
    
    if energy_level in energy_map:
        energy_info = energy_map[energy_level]
        recommendation["suggested_moods"].extend(energy_info["moods"])
        recommendation["context_notes"].append(energy_info["note"])
    
    # Remove duplicates and limit
    recommendation["suggested_moods"] = list(set(recommendation["suggested_moods"]))[:5]
    recommendation["suggested_genres"] = list(set(recommendation["suggested_genres"]))[:5]
    
    return recommendation


def get_viewing_situation_filter(situation):
    """
    Returns genre and content filters based on viewing situation.
    
    Args:
        situation (str): 'alone', 'partner', 'family', 'kids', 'friends'
    
    Returns:
        dict: Filters and recommendations
    """
    situation_map = {
        "alone": {
            "preferred_genres": ["Drama", "Thriller", "Mystery", "Documentary", "Art House"],
            "avoid_genres": [],
            "max_intensity": 10,
            "notes": "Personal viewing - all content types available"
        },
        "partner": {
            "preferred_genres": ["Romance", "Comedy", "Drama", "Thriller"],
            "avoid_genres": ["War", "Western"],
            "max_intensity": 8,
            "notes": "Date night - romantic and engaging content"
        },
        "family": {
            "preferred_genres": ["Family", "Animation", "Adventure", "Comedy"],
            "avoid_genres": ["Horror", "Thriller", "Crime"],
            "max_intensity": 5,
            "notes": "Family viewing - age-appropriate content"
        },
        "kids": {
            "preferred_genres": ["Animation", "Family", "Adventure"],
            "avoid_genres": ["Horror", "Thriller", "Crime", "War", "Drama"],
            "max_intensity": 3,
            "notes": "Kid-friendly - G and PG rated content"
        },
        "friends": {
            "preferred_genres": ["Comedy", "Action", "Adventure", "Sci-Fi"],
            "avoid_genres": ["Romance", "Drama"],
            "max_intensity": 8,
            "notes": "Group viewing - fun and entertaining"
        }
    }
    
    return situation_map.get(situation, situation_map["alone"])
