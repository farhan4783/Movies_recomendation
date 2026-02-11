"""
Input validation and sanitization middleware for Movie Maverick
Uses Marshmallow for schema validation
"""
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE
from functools import wraps
from flask import request, jsonify
import bleach


# Allowed HTML tags for user content (reviews, bio, etc.)
ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
ALLOWED_ATTRIBUTES = {}


def sanitize_html(text):
    """Sanitize HTML to prevent XSS attacks"""
    if not text:
        return text
    return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


def sanitize_string(text):
    """Remove all HTML tags from string"""
    if not text:
        return text
    return bleach.clean(text, tags=[], strip=True)


# Validation Schemas

class LoginSchema(Schema):
    """Login validation schema"""
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))
    
    class Meta:
        unknown = EXCLUDE


class RegisterSchema(Schema):
    """Registration validation schema"""
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error='Username can only contain letters, numbers, hyphens, and underscores')
        ]
    )
    password = fields.Str(
        required=True,
        validate=[
            validate.Length(min=8, max=128),
            validate.Regexp(r'^(?=.*[A-Za-z])(?=.*\d)', error='Password must contain at least one letter and one number')
        ]
    )
    email = fields.Email(required=False)
    
    class Meta:
        unknown = EXCLUDE


class ReviewSchema(Schema):
    """Review submission validation schema"""
    movie_title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    rating = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    comment = fields.Str(required=False, validate=validate.Length(max=2000))
    
    class Meta:
        unknown = EXCLUDE


class ProfileUpdateSchema(Schema):
    """Profile update validation schema"""
    bio = fields.Str(required=False, validate=validate.Length(max=500))
    avatar_url = fields.Url(required=False)
    
    class Meta:
        unknown = EXCLUDE


class ListCreateSchema(Schema):
    """Movie list creation validation schema"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(required=False, validate=validate.Length(max=500))
    is_public = fields.Bool(required=False, missing=True)
    
    class Meta:
        unknown = EXCLUDE


class WatchlistToggleSchema(Schema):
    """Watchlist toggle validation schema"""
    title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    poster_path = fields.Str(required=False)
    id = fields.Int(required=False)
    
    class Meta:
        unknown = EXCLUDE


class SearchSchema(Schema):
    """Search validation schema"""
    query = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    page = fields.Int(required=False, validate=validate.Range(min=1), missing=1)
    limit = fields.Int(required=False, validate=validate.Range(min=1, max=100), missing=20)
    
    class Meta:
        unknown = EXCLUDE


class AdvancedSearchSchema(Schema):
    """Advanced search validation schema"""
    query = fields.Str(required=False, validate=validate.Length(max=200))
    genre = fields.Str(required=False, validate=validate.Length(max=50))
    min_year = fields.Int(required=False, validate=validate.Range(min=1900, max=2100))
    max_year = fields.Int(required=False, validate=validate.Range(min=1900, max=2100))
    min_rating = fields.Float(required=False, validate=validate.Range(min=0, max=10))
    max_rating = fields.Float(required=False, validate=validate.Range(min=0, max=10))
    actor = fields.Str(required=False, validate=validate.Length(max=100))
    director = fields.Str(required=False, validate=validate.Length(max=100))
    page = fields.Int(required=False, validate=validate.Range(min=1), missing=1)
    
    class Meta:
        unknown = EXCLUDE


class CommentSchema(Schema):
    """Comment validation schema"""
    review_id = fields.Int(required=True)
    comment = fields.Str(required=True, validate=validate.Length(min=1, max=1000))
    
    class Meta:
        unknown = EXCLUDE


class ReportSchema(Schema):
    """Content report validation schema"""
    content_type = fields.Str(required=True, validate=validate.OneOf(['review', 'comment', 'list', 'user']))
    content_id = fields.Int(required=True)
    reason = fields.Str(required=True, validate=validate.OneOf([
        'spam', 'harassment', 'inappropriate', 'copyright', 'other'
    ]))
    description = fields.Str(required=False, validate=validate.Length(max=500))
    
    class Meta:
        unknown = EXCLUDE


# Decorator for validating request data

def validate_request(schema_class):
    """
    Decorator to validate request JSON data against a Marshmallow schema
    
    Usage:
        @app.route('/api/endpoint', methods=['POST'])
        @validate_request(MySchema)
        def my_endpoint(validated_data):
            # validated_data contains the validated and sanitized data
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            
            # Get JSON data from request
            json_data = request.get_json(silent=True)
            
            if json_data is None:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON data'
                }), 400
            
            try:
                # Validate and deserialize
                validated_data = schema.load(json_data)
                
                # Sanitize string fields
                for key, value in validated_data.items():
                    if isinstance(value, str):
                        # Sanitize based on field type
                        field = schema.fields.get(key)
                        if isinstance(field, fields.Email) or isinstance(field, fields.Url):
                            # Don't sanitize URLs and emails
                            continue
                        elif key in ['comment', 'bio', 'description']:
                            # Allow limited HTML for rich text fields
                            validated_data[key] = sanitize_html(value)
                        else:
                            # Strip all HTML for other fields
                            validated_data[key] = sanitize_string(value)
                
                # Pass validated data to the route function
                return f(validated_data, *args, **kwargs)
                
            except ValidationError as err:
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'details': err.messages
                }), 400
        
        return decorated_function
    return decorator


def validate_form(schema_class):
    """
    Decorator to validate form data against a Marshmallow schema
    
    Usage:
        @app.route('/endpoint', methods=['POST'])
        @validate_form(MySchema)
        def my_endpoint(validated_data):
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_class()
            
            try:
                # Validate form data
                validated_data = schema.load(request.form)
                
                # Sanitize string fields
                for key, value in validated_data.items():
                    if isinstance(value, str):
                        if key in ['comment', 'bio', 'description']:
                            validated_data[key] = sanitize_html(value)
                        else:
                            validated_data[key] = sanitize_string(value)
                
                return f(validated_data, *args, **kwargs)
                
            except ValidationError as err:
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'details': err.messages
                }), 400
        
        return decorated_function
    return decorator
