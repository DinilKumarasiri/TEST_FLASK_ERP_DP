import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Base configuration class. All configurations inherit from this.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-production-12345'
    DB_HOST = os.environ.get('DB_HOST')
    DB_USER = os.environ.get('DB_USER')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_NAME = os.environ.get('DB_NAME')
    DB_PORT = os.environ.get('DB_PORT')
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')
    else:
        if DB_PASSWORD:
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        else:
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': int(os.environ.get('SQLALCHEMY_POOL_RECYCLE', 280)),
        'pool_pre_ping': os.environ.get('SQLALCHEMY_POOL_PRE_PING', 'true').lower() == 'true',
        'pool_size': int(os.environ.get('SQLALCHEMY_POOL_SIZE', 10)),
        'max_overflow': int(os.environ.get('SQLALCHEMY_MAX_OVERFLOW', 20)),
        'pool_timeout': int(os.environ.get('SQLALCHEMY_POOL_TIMEOUT', 30)),
    }
    
    # ==================== Security Configuration ====================
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    
    # CSRF Protection
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'false').lower() == 'true'
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY') or 'csrf-secret-key-here-67890'
    
    # ==================== Application Settings ====================
    
    # POS Settings
    DEFAULT_VAT_RATE = float(os.environ.get('DEFAULT_VAT_RATE', 0.15))
    DEFAULT_TAX_RATE = float(os.environ.get('DEFAULT_TAX_RATE', 0.15))
    DEFAULT_CURRENCY = os.environ.get('DEFAULT_CURRENCY', 'LKR')
    DEFAULT_CURRENCY_SYMBOL = os.environ.get('DEFAULT_CURRENCY_SYMBOL', 'Rs.')
    
    # Employee Settings
    DEFAULT_COMMISSION_RATE = float(os.environ.get('DEFAULT_COMMISSION_RATE', 5.0))
    WORKING_HOURS_PER_DAY = 8
    ATTENDANCE_TOLERANCE_MINUTES = 15
    DEFAULT_WORKING_DAYS = 26
    
    # Inventory Settings
    LOW_STOCK_THRESHOLD = int(os.environ.get('LOW_STOCK_THRESHOLD', 5))
    CRITICAL_STOCK_THRESHOLD = int(os.environ.get('CRITICAL_STOCK_THRESHOLD', 2))
    STOCK_REORDER_MULTIPLIER = 1.5
    
    # Repair Settings
    DEFAULT_WARRANTY_PERIOD = 3
    MAX_REPAIR_DAYS = 14
    REPAIR_JOB_PREFIX = 'RJ'
    
    # Invoice Settings
    INVOICE_PREFIX = 'INV'
    DEFAULT_PAYMENT_METHODS = ['cash', 'card', 'online', 'due']
    
    # ==================== File Upload Settings ====================
    UPLOAD_FOLDER = os.path.join(basedir, os.environ.get('UPLOAD_FOLDER', 'uploads'))
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,pdf').split(','))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    
    # ==================== Pagination Settings ====================
    ITEMS_PER_PAGE = 20
    ITEMS_PER_PAGE_SMALL = 10
    ITEMS_PER_PAGE_LARGE = 50
    
    # ==================== Email Settings ====================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@mobileshop.com')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'true').lower() in ['true', 'on', '1']
    
    # ==================== Logging Configuration ====================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(basedir, os.environ.get('LOG_FILE', 'logs/mobile_shop.log'))
    
    # ==================== API Settings ====================
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '200 per day, 50 per hour')
    API_PREFIX = os.environ.get('API_PREFIX', '/api/v1')
    
    # ==================== Business Hours ====================
    BUSINESS_OPEN_TIME = os.environ.get('BUSINESS_OPEN_TIME', '09:00')
    BUSINESS_CLOSE_TIME = os.environ.get('BUSINESS_CLOSE_TIME', '18:00')
    BUSINESS_DAYS = os.environ.get('BUSINESS_DAYS', 'Monday,Tuesday,Wednesday,Thursday,Friday,Saturday').split(',')
    
    # ==================== Backup Settings ====================
    BACKUP_FOLDER = os.path.join(basedir, os.environ.get('BACKUP_FOLDER', 'backups'))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    # ==================== Cache Settings ====================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))
    
    # ==================== Theme Settings ====================
    THEME_COLOR_PRIMARY = os.environ.get('THEME_COLOR_PRIMARY', '#4361ee')
    THEME_COLOR_SECONDARY = os.environ.get('THEME_COLOR_SECONDARY', '#3a0ca3')
    THEME_COLOR_SUCCESS = os.environ.get('THEME_COLOR_SUCCESS', '#4cc9f0')
    THEME_COLOR_DANGER = os.environ.get('THEME_COLOR_DANGER', '#f72585')
    THEME_COLOR_WARNING = os.environ.get('THEME_COLOR_WARNING', '#f8961e')
    THEME_COLOR_INFO = os.environ.get('THEME_COLOR_INFO', '#7209b7')
    
    # ==================== Flask Server Settings ====================
    SERVER_NAME = os.environ.get('SERVER_NAME')
    APPLICATION_ROOT = os.environ.get('APPLICATION_ROOT', '/')
    PREFERRED_URL_SCHEME = os.environ.get('PREFERRED_URL_SCHEME', 'http')
    JSON_AS_ASCII = os.environ.get('JSON_AS_ASCII', 'false').lower() == 'true'
    JSON_SORT_KEYS = os.environ.get('JSON_SORT_KEYS', 'false').lower() == 'true'
    TEMPLATES_AUTO_RELOAD = os.environ.get('TEMPLATES_AUTO_RELOAD', 'true').lower() == 'true'
    
    def __init__(self):
        env = os.environ.get('FLASK_ENV', 'development').upper()
        db_display = self.SQLALCHEMY_DATABASE_URI
        if ':' in db_display and '@' in db_display:
            parts = db_display.split('@')
            if ':' in parts[0]:
                user_pass = parts[0].split(':')
                if len(user_pass) > 2:
                    db_display = f"{user_pass[0]}:****@{parts[1]}"
        print(f"\n{'='*60}")
        print(f"Mobile Shop ERP - {env} Configuration")
        print(f"{'='*60}")
        print(f"Database: {db_display}")
        print(f"Debug Mode: {self.DEBUG}")
        print(f"CSRF Enabled: {self.WTF_CSRF_ENABLED}")
        print(f"Upload Folder: {self.UPLOAD_FOLDER}")
        print(f"{'='*60}\n")


class DevelopmentConfig(Config):
    DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
    SQLALCHEMY_ECHO = os.environ.get('SQLALCHEMY_ECHO', 'false').lower() == 'true'
    TEMPLATES_AUTO_RELOAD = True
    MAIL_SUPPRESS_SEND = True
    
    def __init__(self):
        super().__init__()
        print("Development Mode Activated")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    
    def __init__(self):
        super().__init__()
        print("Testing Mode Activated")


class ProductionConfig(Config):
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    TESTING = False
    SQLALCHEMY_ECHO = False
    TEMPLATES_AUTO_RELOAD = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = 'https'
    MAIL_SUPPRESS_SEND = False
    
    def __init__(self):
        super().__init__()
        if not self.SECRET_KEY or 'dev-secret-key' in self.SECRET_KEY or 'development' in self.SECRET_KEY:
            import warnings
            warnings.warn(
                "WARNING: Using default or development secret key! Set a strong SECRET_KEY environment variable.",
                RuntimeWarning
            )
        print("Production Mode - Secure Settings Activated")


config_dict = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development').lower()
    config_class = config_dict.get(config_name)
    if config_class is None:
        print(f"Warning: Unknown configuration '{config_name}', using 'development'")
        config_class = DevelopmentConfig
    return config_class()


def ensure_directories():
    config = get_config()
    directories = [
        config.UPLOAD_FOLDER,
        config.BACKUP_FOLDER,
        os.path.dirname(config.LOG_FILE) if config.LOG_FILE else None,
    ]
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")


def print_config_summary():
    config = get_config()
    env = os.environ.get('FLASK_ENV', 'development').upper()
    print(f"\nConfiguration Summary [{env}]")
    print(f"Database: {config.DB_USER}@{config.DB_HOST}/{config.DB_NAME}")
    print(f"Debug: {config.DEBUG}")
    print(f"Uploads: {config.UPLOAD_FOLDER}")


if __name__ != '__main__':
    try:
        ensure_directories()
    except Exception as e:
        print(f"Warning: Could not create directories: {e}")
