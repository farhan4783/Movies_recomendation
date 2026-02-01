"""
Achievement system for gamification.
Defines achievement criteria and checking logic.
"""

from model.models import Achievement, UserAchievement, Review, Watchlist
from model import db

# Achievement definitions
ACHIEVEMENTS = [
    {
        "name": "First Steps",
        "description": "Add your first movie to watchlist",
        "icon": "🎬",
        "criteria_type": "watchlist_count",
        "criteria_value": 1
    },
    {
        "name": "Movie Buff",
        "description": "Add 10 movies to your watchlist",
        "icon": "🍿",
        "criteria_type": "watchlist_count",
        "criteria_value": 10
    },
    {
        "name": "Cinephile",
        "description": "Add 50 movies to your watchlist",
        "icon": "🎥",
        "criteria_type": "watchlist_count",
        "criteria_value": 50
    },
    {
        "name": "First Review",
        "description": "Write your first movie review",
        "icon": "✍️",
        "criteria_type": "review_count",
        "criteria_value": 1
    },
    {
        "name": "Critic",
        "description": "Write 10 movie reviews",
        "icon": "📝",
        "criteria_type": "review_count",
        "criteria_value": 10
    },
    {
        "name": "Master Critic",
        "description": "Write 50 movie reviews",
        "icon": "🏆",
        "criteria_type": "review_count",
        "criteria_value": 50
    },
    {
        "name": "List Creator",
        "description": "Create your first custom movie list",
        "icon": "📋",
        "criteria_type": "list_count",
        "criteria_value": 1
    },
    {
        "name": "Curator",
        "description": "Create 5 custom movie lists",
        "icon": "📚",
        "criteria_type": "list_count",
        "criteria_value": 5
    }
]

def initialize_achievements():
    """Create achievement records in database if they don't exist"""
    for ach_data in ACHIEVEMENTS:
        existing = Achievement.query.filter_by(name=ach_data["name"]).first()
        if not existing:
            achievement = Achievement(
                name=ach_data["name"],
                description=ach_data["description"],
                icon=ach_data["icon"],
                criteria_type=ach_data["criteria_type"],
                criteria_value=ach_data["criteria_value"]
            )
            db.session.add(achievement)
    db.session.commit()

def check_and_award_achievements(user_id):
    """
    Check if user has earned any new achievements and award them.
    Returns list of newly earned achievements.
    """
    from model.models import MovieList
    
    newly_earned = []
    
    # Get user's current stats
    watchlist_count = Watchlist.query.filter_by(user_id=user_id).count()
    review_count = Review.query.filter_by(user_id=user_id).count()
    list_count = MovieList.query.filter_by(user_id=user_id).count()
    
    stats = {
        "watchlist_count": watchlist_count,
        "review_count": review_count,
        "list_count": list_count
    }
    
    # Get all achievements
    all_achievements = Achievement.query.all()
    
    # Get achievements user already has
    user_achievement_ids = [ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()]
    
    for achievement in all_achievements:
        # Skip if user already has this achievement
        if achievement.id in user_achievement_ids:
            continue
            
        # Check if user meets criteria
        user_stat = stats.get(achievement.criteria_type, 0)
        if user_stat >= achievement.criteria_value:
            # Award achievement
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id
            )
            db.session.add(user_achievement)
            newly_earned.append(achievement)
    
    db.session.commit()
    return newly_earned

def get_user_achievements(user_id):
    """Get all achievements earned by a user"""
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    return [ua.achievement for ua in user_achievements]

def get_achievement_progress(user_id):
    """
    Get user's progress toward all achievements.
    Returns dict with achievement info and progress percentage.
    """
    from model.models import MovieList
    
    # Get user's current stats
    watchlist_count = Watchlist.query.filter_by(user_id=user_id).count()
    review_count = Review.query.filter_by(user_id=user_id).count()
    list_count = MovieList.query.filter_by(user_id=user_id).count()
    
    stats = {
        "watchlist_count": watchlist_count,
        "review_count": review_count,
        "list_count": list_count
    }
    
    # Get all achievements
    all_achievements = Achievement.query.all()
    user_achievement_ids = [ua.achievement_id for ua in UserAchievement.query.filter_by(user_id=user_id).all()]
    
    progress = []
    for achievement in all_achievements:
        user_stat = stats.get(achievement.criteria_type, 0)
        is_earned = achievement.id in user_achievement_ids
        progress_pct = min(100, int((user_stat / achievement.criteria_value) * 100))
        
        progress.append({
            "achievement": achievement,
            "is_earned": is_earned,
            "progress": progress_pct,
            "current": user_stat,
            "required": achievement.criteria_value
        })
    
    return progress
