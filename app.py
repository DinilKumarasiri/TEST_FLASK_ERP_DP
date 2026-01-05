from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config
import os
from datetime import datetime, timedelta

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def time_ago_filter(value):
    """Format datetime as time ago"""
    if not value:
        return ''
    
    now = datetime.utcnow()
    
    # If value is a date object (not datetime), convert it
    if hasattr(value, 'date') and not hasattr(value, 'hour'):
        # It's a date object
        value = datetime.combine(value, datetime.min.time())
    
    diff = now - value
    
    if diff.days > 365:
        years = diff.days // 365
        return f'{years} year{"s" if years > 1 else ""} ago'
    elif diff.days > 30:
        months = diff.days // 30
        return f'{months} month{"s" if months > 1 else ""} ago'
    elif diff.days > 7:
        weeks = diff.days // 7
        return f'{weeks} week{"s" if weeks > 1 else ""} ago'
    elif diff.days > 0:
        return f'{diff.days} day{"s" if diff.days > 1 else ""} ago'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
    elif diff.seconds > 0:
        return f'{diff.seconds} second{"s" if diff.seconds > 1 else ""} ago'
    else:
        return 'just now'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Add custom Jinja2 filters
    app.jinja_env.filters['time_ago'] = time_ago_filter
    
    # Import models
    from modules.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from modules.auth import auth_bp
    from modules.pos import pos_bp
    from modules.inventory import inventory_bp
    from modules.repair import repair_bp
    from modules.employee import employee_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(repair_bp, url_prefix='/repair')
    app.register_blueprint(employee_bp, url_prefix='/employee')
    
    # Context processor to inject current datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
    
    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Dashboard logic based on user role
        if current_user.role == 'admin':
            return redirect(url_for('pos.dashboard'))
        elif current_user.role == 'technician':
            return redirect(url_for('repair.technician_dashboard'))
        else:
            return redirect(url_for('pos.pos_home'))
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    # Additional Jinja2 filters
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        """Format value as currency"""
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"₹0.00"
    
    @app.template_filter('format_date')
    def format_date_filter(value, format='%Y-%m-%d'):
        """Format date"""
        if not value:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return value
    
    @app.template_filter('truncate')
    def truncate_filter(value, length=50):
        """Truncate text"""
        if not value:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + '...'
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        from modules.models import User
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@mobileshop.com',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            
            # Create some sample users for testing
            sample_users = [
                {'username': 'manager', 'email': 'manager@mobileshop.com', 'role': 'manager', 'password': 'manager123'},
                {'username': 'technician1', 'email': 'tech1@mobileshop.com', 'role': 'technician', 'password': 'tech123'},
                {'username': 'staff1', 'email': 'staff1@mobileshop.com', 'role': 'staff', 'password': 'staff123'},
            ]
            
            for user_data in sample_users:
                existing = User.query.filter_by(username=user_data['username']).first()
                if not existing:
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        role=user_data['role'],
                        is_active=True
                    )
                    user.set_password(user_data['password'])
                    db.session.add(user)
            
            db.session.commit()
    
    return app

# For running the app directly
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)