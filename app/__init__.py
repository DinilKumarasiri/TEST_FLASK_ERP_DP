# app/__init__.py
import os
import sys
from flask import Flask, render_template, redirect, url_for, flash, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from flask_wtf import CSRFProtect
from config import Config, get_config, ensure_directories
from datetime import datetime, timedelta
import pytz  # Add this import

# Force UTF-8 encoding for output
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

# Ensure directories exist before anything else
ensure_directories()

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Sri Lanka timezone
SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

def get_sri_lanka_time():
    """Get current time in Sri Lanka timezone"""
    return datetime.now(SRI_LANKA_TZ)

def format_currency_filter(value, currency_symbol='රු.'):
    """Format value as Sri Lankan currency"""
    try:
        return f"{currency_symbol}{float(value):,.2f}"
    except (ValueError, TypeError):
        return f"{currency_symbol}0.00"

def format_date_sri_lanka(value, format_str='%Y-%m-%d'):
    """Format date for Sri Lanka"""
    if not value:
        return ''
    
    if hasattr(value, 'strftime'):
        # If datetime has timezone info, convert to Sri Lanka time
        if hasattr(value, 'tzinfo') and value.tzinfo:
            sl_time = value.astimezone(SRI_LANKA_TZ)
            return sl_time.strftime(format_str)
        return value.strftime(format_str)
    return str(value)

def format_time_sri_lanka(value, format_str='%H:%M'):
    """Format time for Sri Lanka"""
    if not value:
        return '--:--'
    
    if hasattr(value, 'strftime'):
        # If datetime has timezone info, convert to Sri Lanka time
        if hasattr(value, 'tzinfo') and value.tzinfo:
            sl_time = value.astimezone(SRI_LANKA_TZ)
            return sl_time.strftime(format_str)
        return value.strftime(format_str)
    return str(value)

def time_ago_filter_sri_lanka(value):
    """Format datetime as time ago in Sri Lanka context"""
    from app.utils.timezone_helper import sri_lanka_time_ago
    return sri_lanka_time_ago(value)

def create_app(config_class=None):
    if config_class is None:
        config_class = get_config()
    
    # Create the app instance
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)
    
    # Add Sri Lanka timezone to app config
    app.config['SRI_LANKA_TZ'] = SRI_LANKA_TZ
    
    # Custom Jinja filters for Sri Lanka
    app.jinja_env.filters['sl_currency'] = format_currency_filter
    app.jinja_env.filters['sl_date'] = format_date_sri_lanka
    app.jinja_env.filters['sl_time'] = format_time_sri_lanka
    app.jinja_env.filters['sl_time_ago'] = time_ago_filter_sri_lanka

    # Init extensions WITH the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Import models (inside function to avoid circular imports)
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

    # Context processor for Sri Lanka time
    @app.context_processor
    def inject_sri_lanka_time():
        now_sl = get_sri_lanka_time()
        return {
            'now_sl': now_sl,
            'today_sl': now_sl.date(),
            'sri_lanka_tz': SRI_LANKA_TZ,
            'timedelta': timedelta
        }
    
    @app.route('/favicon.ico')
    def favicon():
        uploads_dir = os.path.join(app.root_path, '..', 'uploads')
        favicon_path = os.path.join(uploads_dir, 'logo.ico')
        
        if os.path.exists(favicon_path):
            return send_from_directory(uploads_dir, 'logo.ico')
        else:
            return send_from_directory(os.path.join(app.root_path, 'static'), 'logo.ico')
        
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow(), 'timedelta': timedelta}
    
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    # Route to serve uploaded files
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        uploads_dir = os.path.join(app.root_path, '..', 'uploads')
        try:
            return send_from_directory(uploads_dir, filename)
        except Exception as e:
            app.logger.error(f"Error serving file {filename}: {str(e)}")
            return f"File not found: {filename}", 404

    @app.route('/static/uploads/<path:filename>')
    def serve_upload_static(filename):
        uploads_dir = os.path.join(app.root_path, '..', 'uploads')
        try:
            return send_from_directory(uploads_dir, filename)
        except Exception as e:
            app.logger.error(f"Error serving file {filename}: {str(e)}")
            return f"File not found: {filename}", 404

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

    # Extra filters for Sri Lanka
    @app.template_filter('format_currency_lkr')
    def format_currency_lkr_filter(value):
        """Format value as Sri Lankan Rupees"""
        try:
            return f"රු.{float(value):,.2f}"
        except (ValueError, TypeError):
            return "රු.0.00"

    @app.template_filter('format_date_sl')
    def format_date_sl_filter(value, format='%Y-%m-%d'):
        """Format date for Sri Lanka"""
        return format_date_sri_lanka(value, format)

    @app.template_filter('format_time_sl')
    def format_time_sl_filter(value):
        """Format time for Sri Lanka"""
        return format_time_sri_lanka(value)

    @app.template_filter('truncate')
    def truncate_filter(value, length=50):
        """Truncate text"""
        if not value:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + '...'
    
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
            print("[SUCCESS] Database tables checked/created successfully!")

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
                print("[SUCCESS] Created default admin user: admin / admin123")

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Error during database initialization: {str(e)}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': get_sri_lanka_time().isoformat()}
    
    # CSRF token endpoint
    @app.route('/csrf-token')
    def csrf_token_endpoint():
        from flask_wtf.csrf import generate_csrf
        return {
            'csrf_token': generate_csrf(),
            'message': 'CSRF token generated'
        }

    return app