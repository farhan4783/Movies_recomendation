"""
Redis-based caching layer for Movie Maverick
Improves performance by caching expensive operations
"""
from flask_caching import Cache
from functools import wraps
import json
import hashlib

# Initialize cache (will be configured in app.py)
cache = Cache()


def cache_key_prefix():
    """Generate cache key prefix based on environment"""
    return "moviemaverick:"


def make_cache_key(*args, **kwargs):
    """
    Generate a cache key from function arguments
    """
    # Create a string representation of all arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    
    # Hash for consistent length
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_recommendation(timeout=3600):
    """
    Decorator to cache recommendation results
    Default timeout: 1 hour
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"rec:{f.__name__}:{make_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated_function
    return decorator


def cached_tmdb_api(timeout=86400):
    """
    Decorator to cache TMDB API responses
    Default timeout: 24 hours
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"tmdb:{f.__name__}:{make_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            if result:  # Only cache successful responses
                cache.set(cache_key, result, timeout=timeout)
            
            return result
        return decorated_function
    return decorator


def invalidate_user_cache(user_id):
    """Invalidate all cache entries for a specific user"""
    # This is a simple implementation
    # In production, you might want to use cache tags or patterns
    pattern = f"rec:*user_id={user_id}*"
    # Note: This requires Redis and won't work with simple cache
    try:
        keys = cache.cache._read_client.keys(pattern)
        if keys:
            cache.cache._write_client.delete(*keys)
    except:
        pass  # Fallback if pattern deletion not supported


def clear_recommendation_cache():
    """Clear all recommendation caches"""
    try:
        keys = cache.cache._read_client.keys("rec:*")
        if keys:
            cache.cache._write_client.delete(*keys)
    except:
        cache.clear()  # Fallback to clearing entire cache


# Specific cache functions

def get_popular_movies(fetch_function, n=10):
    """
    Get popular movies with caching
    """
    cache_key = f"popular_movies:{n}"
    result = cache.get(cache_key)
    
    if result is None:
        result = fetch_function(n)
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
    
    return result


def get_trending_searches(limit=10):
    """
    Get trending searches from cache
    """
    cache_key = "trending_searches"
    result = cache.get(cache_key)
    
    if result is None:
        # This would be populated by background tasks
        result = []
    
    return result[:limit]


def update_trending_searches(searches):
    """
    Update trending searches cache
    Called by background tasks
    """
    cache_key = "trending_searches"
    cache.set(cache_key, searches, timeout=3600)


def cache_user_session(user_id, data, timeout=1800):
    """
    Cache user session data
    Default timeout: 30 minutes
    """
    cache_key = f"session:user:{user_id}"
    cache.set(cache_key, data, timeout=timeout)


def get_user_session(user_id):
    """Get cached user session data"""
    cache_key = f"session:user:{user_id}"
    return cache.get(cache_key)


def invalidate_user_session(user_id):
    """Invalidate user session cache"""
    cache_key = f"session:user:{user_id}"
    cache.delete(cache_key)
