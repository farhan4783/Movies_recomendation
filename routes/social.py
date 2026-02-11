"""
Social features routes for Movie Maverick
Handles following, likes, comments, and activity feeds
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from model import db
from model.models import User, Follow, Review, ReviewLike, ReviewComment, ActivityFeed, Notification
from middleware.validators import validate_request, CommentSchema
from utils.notification_service import notify_new_follower, notify_review_like, notify_review_comment
import json
from datetime import datetime

social_bp = Blueprint('social', __name__, url_prefix='/api/social')


@social_bp.route('/users/<int:user_id>/follow', methods=['POST'])
@login_required
def toggle_follow(user_id):
    """Follow or unfollow a user"""
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot follow yourself'}), 400
    
    target_user = User.query.get_or_404(user_id)
    
    # Check if already following
    existing_follow = Follow.query.filter_by(
        follower_id=current_user.id,
        followed_id=user_id
    ).first()
    
    if existing_follow:
        # Unfollow
        db.session.delete(existing_follow)
        action = 'unfollowed'
    else:
        # Follow
        new_follow = Follow(
            follower_id=current_user.id,
            followed_id=user_id
        )
        db.session.add(new_follow)
        action = 'followed'
        
        # Create activity
        activity = ActivityFeed(
            user_id=current_user.id,
            activity_type='follow',
            content=json.dumps({
                'followed_user_id': user_id,
                'followed_username': target_user.username
            })
        )
        db.session.add(activity)
        
        # Notify the followed user
        notify_new_follower(user_id, current_user.username)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': action,
        'follower_count': target_user.get_follower_count()
    })


@social_bp.route('/users/<int:user_id>/followers', methods=['GET'])
def get_followers(user_id):
    """Get list of user's followers"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    user = User.query.get_or_404(user_id)
    
    followers_query = Follow.query.filter_by(followed_id=user_id).order_by(Follow.created_at.desc())
    pagination = followers_query.paginate(page=page, per_page=per_page, error_out=False)
    
    followers = []
    for follow in pagination.items:
        follower = User.query.get(follow.follower_id)
        followers.append({
            'id': follower.id,
            'username': follower.username,
            'avatar_url': follower.avatar_url,
            'bio': follower.bio,
            'followed_at': follow.created_at.isoformat(),
            'is_following': current_user.is_authenticated and current_user.is_following(follower)
        })
    
    return jsonify({
        'success': True,
        'followers': followers,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@social_bp.route('/users/<int:user_id>/following', methods=['GET'])
def get_following(user_id):
    """Get list of users that this user is following"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    user = User.query.get_or_404(user_id)
    
    following_query = Follow.query.filter_by(follower_id=user_id).order_by(Follow.created_at.desc())
    pagination = following_query.paginate(page=page, per_page=per_page, error_out=False)
    
    following = []
    for follow in pagination.items:
        followed = User.query.get(follow.followed_id)
        following.append({
            'id': followed.id,
            'username': followed.username,
            'avatar_url': followed.avatar_url,
            'bio': followed.bio,
            'followed_at': follow.created_at.isoformat(),
            'is_following': current_user.is_authenticated and current_user.is_following(followed)
        })
    
    return jsonify({
        'success': True,
        'following': following,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@social_bp.route('/reviews/<int:review_id>/like', methods=['POST'])
@login_required
def toggle_review_like(review_id):
    """Like or unlike a review"""
    review = Review.query.get_or_404(review_id)
    
    # Check if already liked
    existing_like = ReviewLike.query.filter_by(
        user_id=current_user.id,
        review_id=review_id
    ).first()
    
    if existing_like:
        # Unlike
        db.session.delete(existing_like)
        action = 'unliked'
    else:
        # Like
        new_like = ReviewLike(
            user_id=current_user.id,
            review_id=review_id
        )
        db.session.add(new_like)
        action = 'liked'
        
        # Notify review owner (if not liking own review)
        if review.user_id != current_user.id:
            notify_review_like(review.user_id, current_user.username, review.movie_title)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': action,
        'like_count': review.get_like_count()
    })


@social_bp.route('/reviews/<int:review_id>/comments', methods=['GET', 'POST'])
def review_comments(review_id):
    """Get or post comments on a review"""
    review = Review.query.get_or_404(review_id)
    
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        data = request.get_json()
        comment_text = data.get('comment', '').strip()
        
        if not comment_text:
            return jsonify({'success': False, 'error': 'Comment cannot be empty'}), 400
        
        if len(comment_text) > 1000:
            return jsonify({'success': False, 'error': 'Comment too long (max 1000 characters)'}), 400
        
        # Create comment
        comment = ReviewComment(
            user_id=current_user.id,
            review_id=review_id,
            comment=comment_text
        )
        db.session.add(comment)
        db.session.commit()
        
        # Notify review owner (if not commenting on own review)
        if review.user_id != current_user.id:
            notify_review_comment(review.user_id, current_user.username, review.movie_title, review_id)
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': {
                    'id': current_user.id,
                    'username': current_user.username,
                    'avatar_url': current_user.avatar_url
                },
                'comment': comment.comment,
                'created_at': comment.created_at.isoformat()
            }
        })
    
    else:  # GET
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        comments_query = ReviewComment.query.filter_by(
            review_id=review_id,
            is_hidden=False
        ).order_by(ReviewComment.created_at.desc())
        
        pagination = comments_query.paginate(page=page, per_page=per_page, error_out=False)
        
        comments = []
        for comment in pagination.items:
            comments.append({
                'id': comment.id,
                'user': {
                    'id': comment.user.id,
                    'username': comment.user.username,
                    'avatar_url': comment.user.avatar_url
                },
                'comment': comment.comment,
                'created_at': comment.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'comments': comments,
            'total': pagination.total,
            'page': page,
            'pages': pagination.pages
        })


@social_bp.route('/feed', methods=['GET'])
@login_required
def get_activity_feed():
    """Get personalized activity feed from followed users"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Get IDs of users being followed
    following = Follow.query.filter_by(follower_id=current_user.id).all()
    following_ids = [f.followed_id for f in following]
    following_ids.append(current_user.id)  # Include own activities
    
    # Get activities from followed users
    activities_query = ActivityFeed.query.filter(
        ActivityFeed.user_id.in_(following_ids)
    ).order_by(ActivityFeed.created_at.desc())
    
    pagination = activities_query.paginate(page=page, per_page=per_page, error_out=False)
    
    feed = []
    for activity in pagination.items:
        user = User.query.get(activity.user_id)
        content = json.loads(activity.content) if activity.content else {}
        
        feed.append({
            'id': activity.id,
            'user': {
                'id': user.id,
                'username': user.username,
                'avatar_url': user.avatar_url
            },
            'activity_type': activity.activity_type,
            'content': content,
            'created_at': activity.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'feed': feed,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@social_bp.route('/users/search', methods=['GET'])
def search_users():
    """Search for users"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not query:
        return jsonify({'success': False, 'error': 'Search query required'}), 400
    
    # Search users by username
    users_query = User.query.filter(
        User.username.ilike(f'%{query}%'),
        User.is_active == True
    ).order_by(User.username)
    
    pagination = users_query.paginate(page=page, per_page=per_page, error_out=False)
    
    users = []
    for user in pagination.items:
        users.append({
            'id': user.id,
            'username': user.username,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'follower_count': user.get_follower_count(),
            'is_following': current_user.is_authenticated and current_user.is_following(user)
        })
    
    return jsonify({
        'success': True,
        'users': users,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })


@social_bp.route('/users/<int:user_id>/profile', methods=['GET'])
def get_user_profile(user_id):
    """Get public user profile"""
    user = User.query.get_or_404(user_id)
    
    # Check privacy settings
    prefs = user.preferences
    if prefs and not prefs.profile_public and (not current_user.is_authenticated or current_user.id != user_id):
        return jsonify({'success': False, 'error': 'Profile is private'}), 403
    
    profile = {
        'id': user.id,
        'username': user.username,
        'avatar_url': user.avatar_url,
        'bio': user.bio,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'follower_count': user.get_follower_count(),
        'following_count': user.get_following_count(),
        'is_following': current_user.is_authenticated and current_user.is_following(user)
    }
    
    # Add stats if allowed
    if not prefs or prefs.show_watchlist:
        from model.models import Watchlist
        profile['watchlist_count'] = Watchlist.query.filter_by(user_id=user_id).count()
    
    if not prefs or prefs.show_reviews:
        profile['review_count'] = Review.query.filter_by(user_id=user_id).count()
    
    return jsonify({
        'success': True,
        'profile': profile
    })
