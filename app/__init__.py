import os
from flask import Flask, render_template, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from flask_wtf import CSRFProtect
from config import Config, get_config, ensure_directories
from datetime import datetime, timedelta

# Ensure directories exist before anything else
ensure_directories()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def time_ago_filter(value):
    """Format datetime as time ago"""
    if not value:
        return ''

    now = datetime.utcnow()

    if hasattr(value, 'date') and not hasattr(value, 'hour'):
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


def create_app(config_class=None):
    if config_class is None:
        config_class = get_config()
    
    app = Flask(__name__, template_folder='../templates')
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Jinja filters
    app.jinja_env.filters['time_ago'] = time_ago_filter

    # Import models
    from .models import User, Commission, Attendance, LeaveRequest, Customer, Product, Supplier, StockItem, RepairJob

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from .blueprints.auth import auth_bp
    from .blueprints.pos import pos_bp
    from .blueprints.inventory import inventory_bp
    from .blueprints.repair import repair_bp
    from .blueprints.employee import employee_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(pos_bp, url_prefix='/pos')
    app.register_blueprint(repair_bp, url_prefix='/repair')
    app.register_blueprint(employee_bp, url_prefix='/employee')

    # Context processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow(), 'timedelta': timedelta}
    
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

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

    # Extra filters
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        """Format value as currency"""
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter('format_date')
    def format_date_filter(value, format='%Y-%m-%d'):
        """Format date"""
        if not value:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return str(value)

    @app.template_filter('truncate')
    def truncate_filter(value, length=50):
        """Truncate text"""
        if not value:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + '...'

    @app.template_filter('format_time')
    def format_time_filter(value):
        """Format time"""
        if not value:
            return '--:--'
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        return str(value)
    
    @app.template_filter('match')
    def match_filter(value, pattern):
        """Check if string matches pattern"""
        if not value:
            return False
        return str(value).startswith(pattern)

    # Initialize database with sample data
    with app.app_context():
        try:
            # Create all tables if they don't exist
            db.create_all()
            print("✅ Database tables checked/created successfully!")

            # Create default admin if not exists
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
                print("✅ Created default admin user: admin / admin123")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during database initialization: {str(e)}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
    
    # CSRF token endpoint
    @app.route('/csrf-token')
    def csrf_token_endpoint():
        from flask_wtf.csrf import generate_csrf
        return {
            'csrf_token': generate_csrf(),
            'message': 'CSRF token generated'
        }

    return app