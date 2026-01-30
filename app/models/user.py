from .. import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin, staff, technician
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - will be defined in respective files
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_manager(self):
        """Backward compatibility - treat staff as manager for existing code"""
        return self.role in ['admin', 'staff']  # Admin and staff have manager privileges
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permissions = {
            'admin': ['view', 'create', 'edit', 'delete', 'approve', 'manage_users'],
            'staff': ['view', 'create', 'edit', 'approve'],  # Staff can do most things
            'technician': ['view', 'create', 'edit']  # Limited to repair tasks
        }
        
        return permission in permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'