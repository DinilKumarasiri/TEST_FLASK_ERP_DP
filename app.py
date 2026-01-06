from flask import Flask, render_template, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from config import Config
import os
from datetime import datetime, timedelta

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
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


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Create upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Jinja filters
    app.jinja_env.filters['time_ago'] = time_ago_filter

    # Import models
    from modules.models import User, Commission, Attendance, LeaveRequest

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

    # Context processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow(), 'timedelta': timedelta}

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

    # Initialize database with sample data
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
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
                print("✓ Created default admin user: admin / admin123")
            
            # Create sample users for testing
            sample_users = [
                {'username': 'manager', 'email': 'manager@mobileshop.com', 'role': 'manager', 'password': 'manager123'},
                {'username': 'technician1', 'email': 'tech1@mobileshop.com', 'role': 'technician', 'password': 'tech123'},
                {'username': 'staff1', 'email': 'staff1@mobileshop.com', 'role': 'staff', 'password': 'staff123'},
                {'username': 'technician2', 'email': 'tech2@mobileshop.com', 'role': 'technician', 'password': 'tech123'},
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
                    print(f"✓ Created sample user: {user_data['username']} / {user_data['password']}")
            
            db.session.commit()
            
            # Create sample commissions (without notes field)
            if Commission.query.count() == 0:
                users = User.query.filter_by(is_active=True).all()
                
                sample_commissions = [
                    {
                        'employee_id': users[0].id if len(users) > 0 else admin.id,
                        'sale_amount': 25000.00,
                        'commission_rate': 5.0,
                        'commission_amount': 1250.00,
                        'status': 'paid',
                        'payment_date': datetime.utcnow() - timedelta(days=15),
                    },
                    {
                        'employee_id': users[1].id if len(users) > 1 else admin.id,
                        'sale_amount': 18000.00,
                        'commission_rate': 4.5,
                        'commission_amount': 810.00,
                        'status': 'pending',
                    },
                    {
                        'employee_id': users[2].id if len(users) > 2 else admin.id,
                        'sale_amount': 12000.00,
                        'commission_rate': 3.0,
                        'commission_amount': 360.00,
                        'status': 'paid',
                        'payment_date': datetime.utcnow() - timedelta(days=7),
                    }
                ]
                
                for commission_data in sample_commissions:
                    commission = Commission(**commission_data)
                    db.session.add(commission)
                
                print("✓ Created sample commission records")
            
            # Create sample attendance records for today
            today = datetime.utcnow().date()
            if Attendance.query.filter_by(date=today).count() == 0:
                users = User.query.filter_by(is_active=True).all()
                for user in users:
                    attendance = Attendance(
                        employee_id=user.id,
                        date=today,
                        status='present'
                    )
                    db.session.add(attendance)
                print("✓ Created sample attendance records for today")
            
            # Create sample leave requests
            if LeaveRequest.query.count() == 0 and len(User.query.all()) > 0:
                users = User.query.filter_by(is_active=True).limit(3).all()
                leave_types = ['sick', 'casual', 'annual', 'emergency']
                
                for i, user in enumerate(users):
                    if i < len(leave_types):
                        leave_request = LeaveRequest(
                            employee_id=user.id,
                            leave_type=leave_types[i],
                            start_date=today + timedelta(days=5),
                            end_date=today + timedelta(days=7 + i),
                            reason=f'{leave_types[i].title()} leave for personal reasons',
                            status='pending' if i % 2 == 0 else 'approved'
                        )
                        db.session.add(leave_request)
                
                print("✓ Created sample leave requests")
            
            db.session.commit()
            print("✓ Database initialization completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during database initialization: {str(e)}")
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
    
    # API endpoint for system info
    @app.route('/api/system-info')
    @login_required
    def system_info():
        if current_user.role != 'admin':
            return {'error': 'Unauthorized'}, 403
        
        info = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'pending_commissions': Commission.query.filter_by(status='pending').count(),
            'pending_leaves': LeaveRequest.query.filter_by(status='pending').count(),
            'today_attendance': Attendance.query.filter(
                db.func.date(Attendance.date) == datetime.utcnow().date()
            ).count()
        }
        
        return info
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)