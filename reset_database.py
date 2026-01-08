# reset_database.py
from app import create_app, db
from modules.models import *
import os

app = create_app()

with app.app_context():
    # Delete database file
    db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed database file: {db_path}")
    
    # Create all tables
    db.create_all()
    print("Created all tables")
    
    # Create default admin user
    from werkzeug.security import generate_password_hash
    
    admin = User(
        username='admin',
        email='admin@example.com',
        password_hash=generate_password_hash('admin123'),
        role='admin',
        is_active=True
    )
    
    db.session.add(admin)
    db.session.commit()
    print("Created admin user (username: admin, password: admin123)")