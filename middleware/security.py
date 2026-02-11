"""
Security utilities and middleware for Movie Maverick
"""
import secrets
import hashlib
import re
from functools import wraps
from flask import request, jsonify, abort
from flask_login import current_user


def generate_csrf_token():
    """Generate a secure CSRF token"""
    return secrets.token_hex(32)


def validate_csrf_token(token):
    """Validate CSRF token"""
    # This is a simple implementation
    # In production, you might want to use Flask-WTF for CSRF protection
    return token and len(token) == 64


def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        if not getattr(current_user, 'is_admin', False):
            return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_moderator(f):
    """Decorator to require moderator or admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        is_mod = getattr(current_user, 'is_moderator', False)
        is_admin = getattr(current_user, 'is_admin', False)
        
        if not (is_mod or is_admin):
            return jsonify({'success': False, 'error': 'Moderator privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def validate_password_strength(password):
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Optional: Check for special characters
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     return False, "Password must contain at least one special character"
    
    # Check for common passwords
    common_passwords = [
        'password', '12345678', 'qwerty', 'abc123', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', '1234567890'
    ]
    
    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a stronger password"
    
    return True, None


def hash_file(file_path):
    """Generate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal attacks"""
    # Remove any directory components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove any non-alphanumeric characters except dots, hyphens, and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')
    
    return filename


def check_file_extension(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_client_ip():
    """Get client IP address, considering proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def is_safe_url(target):
    """
    Check if a redirect URL is safe (same domain)
    Prevents open redirect vulnerabilities
    """
    from urllib.parse import urlparse, urljoin
    from flask import request
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


class SecurityHeaders:
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        app.after_request(self.add_security_headers)
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response"""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions policy
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


def rate_limit_key():
    """Generate rate limit key based on user or IP"""
    if current_user.is_authenticated:
        return f"user_{current_user.id}"
    return f"ip_{get_client_ip()}"
