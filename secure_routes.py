"""
Secure routing module to hide IDs and sensitive data from URLs
Uses session-based tokens instead of exposing database IDs
"""
import secrets
from flask import session
from functools import wraps

class SecureRouter:
    """Manages secure token-to-ID mappings in session"""
    
    @staticmethod
    def generate_token(resource_type, resource_id):
        """Generate a secure token for a resource and store in session"""
        if 'secure_tokens' not in session:
            session['secure_tokens'] = {}
        
        # Generate a secure random token
        token = secrets.token_urlsafe(16)
        
        # Store mapping in session
        session['secure_tokens'][token] = {
            'type': resource_type,
            'id': resource_id
        }
        session.modified = True
        
        return token
    
    @staticmethod
    def get_id_from_token(token, resource_type=None):
        """Retrieve resource ID from token"""
        if 'secure_tokens' not in session:
            return None
        
        token_data = session['secure_tokens'].get(token)
        if not token_data:
            return None
        
        # Verify resource type if specified
        if resource_type and token_data['type'] != resource_type:
            return None
        
        return token_data['id']
    
    @staticmethod
    def clear_token(token):
        """Remove a token from session"""
        if 'secure_tokens' in session and token in session['secure_tokens']:
            del session['secure_tokens'][token]
            session.modified = True
    
    @staticmethod
    def clear_all_tokens():
        """Clear all tokens from session"""
        if 'secure_tokens' in session:
            session['secure_tokens'] = {}
            session.modified = True


def require_token(resource_type):
    """Decorator to validate token and extract ID"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, abort
            
            # Get token from POST data or query parameter
            token = request.form.get('token') or request.args.get('token')
            
            if not token:
                abort(400, 'Missing security token')
            
            # Get ID from token
            resource_id = SecureRouter.get_id_from_token(token, resource_type)
            
            if resource_id is None:
                abort(403, 'Invalid or expired security token')
            
            # Pass the ID to the route function
            return f(resource_id, *args, **kwargs)
        
        return decorated_function
    return decorator
