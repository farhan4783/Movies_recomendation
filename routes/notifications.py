"""
Notification routes for Movie Maverick
Handles notification retrieval and management
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from model import db
from model.models import Notification, UserPreferences
from utils.notification_service import (
    mark_notification_read,
    mark_all_notifications_read,
    get_unread_count,
    get_recent_notifications
)

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/', methods=['GET'])
@login_required
def get_notifications():
    """Get user's notifications"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    # Get notifications
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if unread_only:
        query = query.filter_by(is_read=False)
    
    pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    notifications = []
    for notif in pagination.items:
        notifications.append({
            'id': notif.id,
            'type': notif.type,
            'title': notif.title,
            'message': notif.message,
            'link': notif.link,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'notifications': notifications,
        'unread_count': get_unread_count(current_user.id),
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@notifications_bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read"""
    success = mark_notification_read(notification_id, current_user.id)
    
    if success:
        return jsonify({
            'success': True,
            'unread_count': get_unread_count(current_user.id)
        })
    else:
        return jsonify({'success': False, 'error': 'Notification not found'}), 404


@notifications_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    mark_all_notifications_read(current_user.id)
    
    return jsonify({
        'success': True,
        'unread_count': 0
    })


@notifications_bp.route('/unread-count', methods=['GET'])
@login_required
def unread_count():
    """Get count of unread notifications"""
    count = get_unread_count(current_user.id)
    
    return jsonify({
        'success': True,
        'count': count
    })


@notifications_bp.route('/preferences', methods=['GET', 'POST'])
@login_required
def notification_preferences():
    """Get or update notification preferences"""
    prefs = UserPreferences.query.filter_by(user_id=current_user.id).first()
    
    if not prefs:
        # Create default preferences
        prefs = UserPreferences(user_id=current_user.id)
        db.session.add(prefs)
        db.session.commit()
    
    if request.method == 'POST':
        data = request.get_json()
        
        # Update preferences
        if 'email_notifications' in data:
            prefs.email_notifications = bool(data['email_notifications'])
        if 'notify_new_follower' in data:
            prefs.notify_new_follower = bool(data['notify_new_follower'])
        if 'notify_review_like' in data:
            prefs.notify_review_like = bool(data['notify_review_like'])
        if 'notify_review_comment' in data:
            prefs.notify_review_comment = bool(data['notify_review_comment'])
        if 'notify_new_recommendations' in data:
            prefs.notify_new_recommendations = bool(data['notify_new_recommendations'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Preferences updated'
        })
    
    else:  # GET
        return jsonify({
            'success': True,
            'preferences': {
                'email_notifications': prefs.email_notifications,
                'notify_new_follower': prefs.notify_new_follower,
                'notify_review_like': prefs.notify_review_like,
                'notify_review_comment': prefs.notify_review_comment,
                'notify_new_recommendations': prefs.notify_new_recommendations
            }
        })


@notifications_bp.route('/<int:notification_id>', methods=['DELETE'])
@login_required
def delete_notification(notification_id):
    """Delete a notification"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first()
    
    if not notification:
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'unread_count': get_unread_count(current_user.id)
    })
