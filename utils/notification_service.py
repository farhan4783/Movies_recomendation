"""
Notification service for Movie Maverick
Handles in-app and email notifications
"""
from model import db
from model.models import Notification, User, UserPreferences
from datetime import datetime
import json


def create_notification(user_id, notification_type, title, message, link=None):
    """
    Create a new notification for a user
    
    Args:
        user_id: ID of the user to notify
        notification_type: Type of notification ('follow', 'like', 'comment', 'achievement', etc.)
        title: Notification title
        message: Notification message
        link: Optional link to related content
    
    Returns:
        Notification object
    """
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        link=link
    )
    
    db.session.add(notification)
    db.session.commit()
    
    return notification


def notify_new_follower(followed_user_id, follower_username):
    """Notify user when someone follows them"""
    # Check if user wants this notification
    prefs = UserPreferences.query.filter_by(user_id=followed_user_id).first()
    if prefs and not prefs.notify_new_follower:
        return None
    
    return create_notification(
        user_id=followed_user_id,
        notification_type='follow',
        title='New Follower',
        message=f'{follower_username} started following you',
        link=f'/users/{follower_username}'
    )


def notify_review_like(review_owner_id, liker_username, movie_title):
    """Notify user when someone likes their review"""
    # Check if user wants this notification
    prefs = UserPreferences.query.filter_by(user_id=review_owner_id).first()
    if prefs and not prefs.notify_review_like:
        return None
    
    return create_notification(
        user_id=review_owner_id,
        notification_type='like',
        title='Review Liked',
        message=f'{liker_username} liked your review of "{movie_title}"',
        link=f'/movie/{movie_title}'
    )


def notify_review_comment(review_owner_id, commenter_username, movie_title, review_id):
    """Notify user when someone comments on their review"""
    # Check if user wants this notification
    prefs = UserPreferences.query.filter_by(user_id=review_owner_id).first()
    if prefs and not prefs.notify_review_comment:
        return None
    
    return create_notification(
        user_id=review_owner_id,
        notification_type='comment',
        title='New Comment',
        message=f'{commenter_username} commented on your review of "{movie_title}"',
        link=f'/movie/{movie_title}#review-{review_id}'
    )


def notify_achievement_unlocked(user_id, achievement_name, achievement_icon):
    """Notify user when they unlock an achievement"""
    return create_notification(
        user_id=user_id,
        notification_type='achievement',
        title='Achievement Unlocked!',
        message=f'{achievement_icon} You earned the "{achievement_name}" badge!',
        link='/profile#achievements'
    )


def notify_new_recommendations(user_id, count):
    """Notify user about new personalized recommendations"""
    # Check if user wants this notification
    prefs = UserPreferences.query.filter_by(user_id=user_id).first()
    if prefs and not prefs.notify_new_recommendations:
        return None
    
    return create_notification(
        user_id=user_id,
        notification_type='recommendation',
        title='New Recommendations',
        message=f'We have {count} new movie recommendations for you!',
        link='/explore'
    )


def mark_notification_read(notification_id, user_id):
    """
    Mark a notification as read
    
    Args:
        notification_id: ID of the notification
        user_id: ID of the user (for security check)
    
    Returns:
        True if successful, False otherwise
    """
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    
    return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()


def get_unread_count(user_id):
    """Get count of unread notifications for a user"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def get_recent_notifications(user_id, limit=10, unread_only=False):
    """
    Get recent notifications for a user
    
    Args:
        user_id: ID of the user
        limit: Maximum number of notifications to return
        unread_only: If True, only return unread notifications
    
    Returns:
        List of Notification objects
    """
    query = Notification.query.filter_by(user_id=user_id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def delete_old_notifications(days=30):
    """
    Delete notifications older than specified days
    Called by background tasks
    
    Args:
        days: Number of days to keep notifications
    """
    from datetime import timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deleted = Notification.query.filter(
        Notification.created_at < cutoff_date,
        Notification.is_read == True
    ).delete()
    
    db.session.commit()
    
    return deleted


# Email notification functions (optional)

def send_email_notification(user_id, subject, body):
    """
    Send email notification to user
    This is a placeholder - implement with Flask-Mail or your email service
    
    Args:
        user_id: ID of the user
        subject: Email subject
        body: Email body (HTML)
    """
    user = User.query.get(user_id)
    
    if not user or not user.email:
        return False
    
    # Check if user wants email notifications
    prefs = UserPreferences.query.filter_by(user_id=user_id).first()
    if prefs and not prefs.email_notifications:
        return False
    
    # TODO: Implement email sending with Flask-Mail
    # from flask_mail import Message
    # msg = Message(subject, recipients=[user.email])
    # msg.html = body
    # mail.send(msg)
    
    return True


def send_weekly_digest(user_id):
    """
    Send weekly digest email to user
    Called by background tasks
    """
    # Get user's activity from the past week
    from datetime import timedelta
    
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    notifications = Notification.query.filter(
        Notification.user_id == user_id,
        Notification.created_at >= week_ago
    ).all()
    
    if not notifications:
        return False
    
    # Build email body
    subject = "Your Movie Maverick Weekly Digest"
    body = f"""
    <h2>Your Week in Movies</h2>
    <p>Here's what happened this week:</p>
    <ul>
    """
    
    for notif in notifications:
        body += f"<li><strong>{notif.title}</strong>: {notif.message}</li>"
    
    body += "</ul>"
    
    return send_email_notification(user_id, subject, body)
