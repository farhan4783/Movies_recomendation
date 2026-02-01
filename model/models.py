from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String(200), default="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix")
    
    # Relationships
    watchlist = db.relationship('Watchlist', backref='user', lazy=True)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    poster_path = db.Column(db.String(500))
    tmdb_id = db.Column(db.Integer) # Store TMDB ID for better linking

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class Achievement(db.Model):
    """Defines available achievements/badges"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    icon = db.Column(db.String(50), default="🏆")  # Emoji or icon class
    criteria_type = db.Column(db.String(50), nullable=False)  # e.g., 'review_count', 'watchlist_count'
    criteria_value = db.Column(db.Integer, nullable=False)  # Threshold to unlock

class UserAchievement(db.Model):
    """Tracks which achievements users have earned"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement', backref='earned_by')

class MovieList(db.Model):
    """User-created custom movie lists"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref=db.backref('movie_lists', lazy=True))
    items = db.relationship('ListItem', backref='list', lazy=True, cascade='all, delete-orphan')

class ListItem(db.Model):
    """Movies within a custom list"""
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('movie_list.id'), nullable=False)
    movie_title = db.Column(db.String(200), nullable=False)
    poster_path = db.Column(db.String(500))
    tmdb_id = db.Column(db.Integer)
    added_at = db.Column(db.DateTime, default=db.func.current_timestamp())

