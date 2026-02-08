"""
Streaming Availability Utilities
Provides functions to check where movies are available to watch.
"""

from utils.tmdb_client import fetch_watch_providers
from datetime import datetime, timedelta


def get_streaming_availability(movie_id, region="US"):
    """
    Get streaming availability for a movie.
    
    Args:
        movie_id (int): TMDB movie ID
        region (str): Country code (default: US)
    
    Returns:
        dict: Streaming availability information
    """
    providers = fetch_watch_providers(movie_id, region)
    
    if not providers:
        return {
            "available": False,
            "platforms": [],
            "message": "Streaming information not available"
        }
    
    all_platforms = []
    
    # Combine all provider types
    for platform in providers.get("flatrate", []):
        all_platforms.append({
            **platform,
            "type": "stream",
            "display_type": "Stream"
        })
    
    for platform in providers.get("rent", []):
        all_platforms.append({
            **platform,
            "type": "rent",
            "display_type": "Rent"
        })
    
    for platform in providers.get("buy", []):
        all_platforms.append({
            **platform,
            "type": "buy",
            "display_type": "Buy"
        })
    
    return {
        "available": len(all_platforms) > 0,
        "platforms": all_platforms,
        "tmdb_link": providers.get("link"),
        "streaming_count": len(providers.get("flatrate", [])),
        "rental_count": len(providers.get("rent", [])),
        "purchase_count": len(providers.get("buy", []))
    }


def format_streaming_badge(availability):
    """
    Format streaming availability as a badge/label.
    
    Args:
        availability (dict): Streaming availability data
    
    Returns:
        str: HTML badge string
    """
    if not availability.get("available"):
        return '<span class="streaming-badge unavailable">Not Streaming</span>'
    
    streaming_count = availability.get("streaming_count", 0)
    rental_count = availability.get("rental_count", 0)
    
    if streaming_count > 0:
        platforms = [p["name"] for p in availability["platforms"] if p["type"] == "stream"]
        platform_text = platforms[0] if len(platforms) == 1 else f"{streaming_count} platforms"
        return f'<span class="streaming-badge available">Stream on {platform_text}</span>'
    elif rental_count > 0:
        return f'<span class="streaming-badge rental">Available to Rent</span>'
    else:
        return f'<span class="streaming-badge purchase">Available to Buy</span>'


def get_primary_streaming_platform(availability):
    """
    Get the primary/preferred streaming platform.
    Prioritizes subscription services over rental/purchase.
    
    Args:
        availability (dict): Streaming availability data
    
    Returns:
        dict: Primary platform info or None
    """
    if not availability.get("available"):
        return None
    
    platforms = availability.get("platforms", [])
    
    # Prioritize streaming services
    streaming = [p for p in platforms if p["type"] == "stream"]
    if streaming:
        # Prefer popular platforms
        preferred_order = ["Netflix", "Amazon Prime Video", "Disney Plus", "Hulu", "HBO Max", "Apple TV Plus"]
        for preferred in preferred_order:
            for platform in streaming:
                if preferred.lower() in platform["name"].lower():
                    return platform
        return streaming[0]  # Return first if no preferred match
    
    # Fall back to rental
    rental = [p for p in platforms if p["type"] == "rent"]
    if rental:
        return rental[0]
    
    # Last resort: purchase
    purchase = [p for p in platforms if p["type"] == "buy"]
    if purchase:
        return purchase[0]
    
    return None


def check_multiple_movies_availability(movie_ids, region="US"):
    """
    Check streaming availability for multiple movies at once.
    Useful for recommendation lists.
    
    Args:
        movie_ids (list): List of TMDB movie IDs
        region (str): Country code
    
    Returns:
        dict: Map of movie_id to availability data
    """
    availability_map = {}
    
    for movie_id in movie_ids:
        availability_map[movie_id] = get_streaming_availability(movie_id, region)
    
    return availability_map


def get_platform_statistics(availability_map):
    """
    Get statistics about which platforms have the most content.
    
    Args:
        availability_map (dict): Map of movie_id to availability
    
    Returns:
        dict: Platform statistics
    """
    platform_counts = {}
    
    for movie_id, availability in availability_map.items():
        if availability.get("available"):
            for platform in availability.get("platforms", []):
                name = platform["name"]
                if name not in platform_counts:
                    platform_counts[name] = {
                        "count": 0,
                        "type": platform["type"],
                        "logo": platform.get("logo")
                    }
                platform_counts[name]["count"] += 1
    
    # Sort by count
    sorted_platforms = sorted(
        platform_counts.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    
    return {
        "platforms": sorted_platforms,
        "total_platforms": len(platform_counts),
        "most_common": sorted_platforms[0] if sorted_platforms else None
    }
