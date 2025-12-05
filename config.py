import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    
    # POS Settings
    DEFAULT_VAT_RATE = 0.15
    DEFAULT_CURRENCY = 'LKR'
    
    # Inventory Settings
    LOW_STOCK_THRESHOLD = 5
    
    # File Upload Settings
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size