"""
Permission and role checking utilities
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to require specific roles
    Usage: @role_required('admin', 'staff')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    return role_required('admin')(f)

def staff_required(f):
    """Decorator to require staff or admin role"""
    return role_required('admin', 'staff')(f)

def get_role_hierarchy():
    """Get role hierarchy for permission checks"""
    return {
        'admin': 3,     # Highest level
        'staff': 2,     # Middle level (replaces manager)
        'technician': 1 # Basic level
    }

def can_access(user_role, required_role):
    """Check if user role can access required role level"""
    hierarchy = get_role_hierarchy()
    user_level = hierarchy.get(user_role, 0)
    required_level = hierarchy.get(required_role, 999)
    
    return user_level >= required_level