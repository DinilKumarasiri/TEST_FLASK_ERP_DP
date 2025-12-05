from flask import Flask, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from config import Config
import os
from datetime import datetime



db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
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

#########
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}
#########

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
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
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
    
    return app