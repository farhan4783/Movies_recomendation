from flask_login import UserMixin
from . import db
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    bio = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String(200), default="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix")
    
    # Admin & Moderation
    is_admin = db.Column(db.Boolean, default=False)
    is_moderator = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    watchlist = db.relationship('Watchlist', backref='user', lazy=True, cascade='all, delete-orphan')
    preferences = db.relationship('UserPreferences', backref='user', uselist=False, cascade='all, delete-orphan')
    
    # Social relationships
    followers = db.relationship('Follow', foreign_keys='Follow.followed_id', backref='followed', lazy='dynamic', cascade='all, delete-orphan')
    following = db.relationship('Follow', foreign_keys='Follow.follower_id', backref='follower', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_following(self, user):
        """Check if this user is following another user"""
        return self.following.filter_by(followed_id=user.id).first() is not None
    
    def get_follower_count(self):
        """Get number of followers"""
        return self.followers.count()
    
    def get_following_count(self):
        """Get number of users being followed"""
        return self.following.count()

class UserPreferences(db.Model):
    """User preferences and settings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Theme & Display
    theme = db.Column(db.String(20), default='dark')  # 'dark', 'light'
    language = db.Column(db.String(10), default='en')
    
    # Privacy Settings
    profile_public = db.Column(db.Boolean, default=True)
    show_watchlist = db.Column(db.Boolean, default=True)
    show_reviews = db.Column(db.Boolean, default=True)
    
    # Notification Preferences
    email_notifications = db.Column(db.Boolean, default=False)
    notify_new_follower = db.Column(db.Boolean, default=True)
    notify_review_like = db.Column(db.Boolean, default=True)
    notify_review_comment = db.Column(db.Boolean, default=True)
    notify_new_recommendations = db.Column(db.Boolean, default=False)
    
    # Content Filters
    filter_adult_content = db.Column(db.Boolean, default=False)
    preferred_genres = db.Column(db.String(500))  # Comma-separated list

class Follow(db.Model):
    """User following relationships"""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    movie_title = db.Column(db.String(200), nullable=False)
    poster_path = db.Column(db.String(500))
    tmdb_id = db.Column(db.Integer, index=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    movie_title = db.Column(db.String(200), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Moderation
    is_flagged = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    likes = db.relationship('ReviewLike', backref='review', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('ReviewComment', backref='review', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_like_count(self):
        """Get number of likes"""
        return self.likes.count()
    
    def is_liked_by(self, user):
        """Check if user has liked this review"""
        return self.likes.filter_by(user_id=user.id).first() is not None

class ReviewLike(db.Model):
    """Likes on reviews"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='review_likes')
    __table_args__ = (db.UniqueConstraint('user_id', 'review_id', name='unique_review_like'),)

class ReviewComment(db.Model):
    """Comments on reviews"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    review_id = db.Column(db.Integer, db.ForeignKey('review.id'), nullable=False, index=True)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Moderation
    is_flagged = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='review_comments')

class Notification(db.Model):
    """User notifications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # 'follow', 'like', 'comment', 'achievement', etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(200))  # URL to related content
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

class SearchHistory(db.Model):
    """Track user search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)  # Null for anonymous
    query = db.Column(db.String(200), nullable=False, index=True)
    filters = db.Column(db.Text)  # JSON string of applied filters
    results_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class ViewingHistory(db.Model):
    """Track movie views for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    movie_title = db.Column(db.String(200), nullable=False)
    tmdb_id = db.Column(db.Integer, index=True)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class ActivityFeed(db.Model):
    """User activity feed for social features"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False)  # 'review', 'watchlist_add', 'list_create', etc.
    content = db.Column(db.Text)  # JSON string with activity details
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref=db.backref('activities', lazy=True))

class Achievement(db.Model):
    """Defines available achievements/badges"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    icon = db.Column(db.String(50), default="🏆")
    criteria_type = db.Column(db.String(50), nullable=False)
    criteria_value = db.Column(db.Integer, nullable=False)

class UserAchievement(db.Model):
    """Tracks which achievements users have earned"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('achievements', lazy=True))
    achievement = db.relationship('Achievement', backref='earned_by')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='unique_user_achievement'),)

class MovieList(db.Model):
    """User-created custom movie lists"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('movie_lists', lazy=True))
    items = db.relationship('ListItem', backref='list', lazy=True, cascade='all, delete-orphan')

class ListItem(db.Model):
    """Movies within a custom list"""
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('movie_list.id'), nullable=False, index=True)
    movie_title = db.Column(db.String(200), nullable=False)
    poster_path = db.Column(db.String(500))
    tmdb_id = db.Column(db.Integer)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    """Content reports for moderation"""
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content_type = db.Column(db.String(50), nullable=False)  # 'review', 'comment', 'list', 'user'
    content_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(50), nullable=False)  # 'spam', 'harassment', 'inappropriate', etc.
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'reviewed', 'resolved', 'dismissed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reports_made')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

class FeaturedContent(db.Model):
    """Featured movies/lists managed by admins"""
    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(db.String(50), nullable=False)  # 'movie', 'list'
    content_id = db.Column(db.Integer)  # List ID or null for movies
    movie_title = db.Column(db.String(200))  # For featured movies
    tmdb_id = db.Column(db.Integer)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    creator = db.relationship('User', backref='featured_content_created')

