import os
from datetime import timedelta

# Get the base directory
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Base configuration class. All configurations inherit from this.
    """
    
    # ==================== Flask Configuration ====================
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-this-in-production-12345'
    
    # ==================== Database Configuration ====================
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f"sqlite:///{os.path.join(basedir, 'mobile_shop.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query debugging
    
    # ==================== Security Configuration ====================
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('CSRF_SECRET_KEY') or 'csrf-secret-key-here-67890'
    
    # ==================== Application Settings ====================
    
    # POS Settings
    DEFAULT_VAT_RATE = 0.15  # 15% VAT
    DEFAULT_TAX_RATE = 0.15  # 15% Tax
    DEFAULT_CURRENCY = 'LKR'
    DEFAULT_CURRENCY_SYMBOL = '₹'
    
    # Employee Settings
    DEFAULT_COMMISSION_RATE = 5.0  # 5% commission
    WORKING_HOURS_PER_DAY = 8
    ATTENDANCE_TOLERANCE_MINUTES = 15  # Late tolerance in minutes
    DEFAULT_WORKING_DAYS = 26  # Default working days per month
    
    # Inventory Settings
    LOW_STOCK_THRESHOLD = 5
    CRITICAL_STOCK_THRESHOLD = 2
    STOCK_REORDER_MULTIPLIER = 1.5  # Reorder 1.5 times the low stock threshold
    
    # Repair Settings
    DEFAULT_WARRANTY_PERIOD = 3  # months
    MAX_REPAIR_DAYS = 14  # Maximum days for repair completion
    REPAIR_JOB_PREFIX = 'RJ'
    
    # Invoice Settings
    INVOICE_PREFIX = 'INV'
    DEFAULT_PAYMENT_METHODS = ['cash', 'card', 'online', 'due']
    
    # ==================== File Upload Settings ====================
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
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
    MAIL_SUPPRESS_SEND = True  # Set to False to actually send emails
    
    # ==================== Logging Configuration ====================
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.path.join(basedir, 'logs', 'mobile_shop.log')
    
    # ==================== API Settings ====================
    API_RATE_LIMIT = "200 per day, 50 per hour"
    API_PREFIX = '/api/v1'
    
    # ==================== Business Hours ====================
    BUSINESS_OPEN_TIME = "09:00"
    BUSINESS_CLOSE_TIME = "18:00"
    BUSINESS_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    # ==================== Backup Settings ====================
    BACKUP_FOLDER = os.path.join(basedir, 'backups')
    BACKUP_RETENTION_DAYS = 30
    
    # ==================== Cache Settings ====================
    CACHE_TYPE = 'simple'  # 'simple', 'redis', 'memcached'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # ==================== Theme Settings ====================
    THEME_COLOR_PRIMARY = '#4361ee'
    THEME_COLOR_SECONDARY = '#3a0ca3'
    THEME_COLOR_SUCCESS = '#4cc9f0'
    THEME_COLOR_DANGER = '#f72585'
    THEME_COLOR_WARNING = '#f8961e'
    THEME_COLOR_INFO = '#7209b7'


class DevelopmentConfig(Config):
    """
    Development configuration - for local development
    """
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Show SQL queries in console - set to True for debugging
    TEMPLATES_AUTO_RELOAD = True
    MAIL_SUPPRESS_SEND = True  # Don't send emails in development
    
    # Development-specific settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'development-secret-key-123456'
    
    def __init__(self):
        super().__init__()
        print("📱 Using Development Configuration")
        print(f"🔗 Database: {self.SQLALCHEMY_DATABASE_URI}")


class TestingConfig(Config):
    """
    Testing configuration - for unit tests
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    MAIL_SUPPRESS_SEND = True
    
    # Testing-specific settings
    SECRET_KEY = 'testing-secret-key-123456'
    
    def __init__(self):
        super().__init__()
        print("🧪 Using Testing Configuration")


class ProductionConfig(Config):
    """
    Production configuration - for live deployment
    """
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    TEMPLATES_AUTO_RELOAD = False
    
    # Security settings for production
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Email settings for production
    MAIL_SUPPRESS_SEND = False
    
    def __init__(self):
        super().__init__()
        
        # Override database URL for production if DATABASE_URL is set
        if os.environ.get('DATABASE_URL'):
            # Convert postgres:// to postgresql:// for SQLAlchemy
            db_url = os.environ.get('DATABASE_URL')
            if db_url.startswith('postgres://'):
                self.SQLALCHEMY_DATABASE_URI = db_url.replace('postgres://', 'postgresql://')
            else:
                self.SQLALCHEMY_DATABASE_URI = db_url
        
        # Warn about insecure secret key (but don't crash on import)
        current_env = os.environ.get('FLASK_ENV', '').lower()
        if current_env == 'production':
            if not self.SECRET_KEY or self.SECRET_KEY.startswith('dev-secret-key') or self.SECRET_KEY.startswith('development'):
                import warnings
                warnings.warn(
                    "⚠️  WARNING: Using default or development secret key in production! "
                    "Set a strong SECRET_KEY environment variable.",
                    RuntimeWarning
                )
        
        print("🚀 Using Production Configuration")
        print(f"🔒 Secure cookies: {self.SESSION_COOKIE_SECURE}")


# Configuration dictionary for easy access
config_dict = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Get configuration class based on environment name.
    
    Args:
        config_name (str): Configuration name ('development', 'testing', 'production')
    
    Returns:
        Config class
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development').lower()
    
    config_class = config_dict.get(config_name)
    
    if config_class is None:
        print(f"⚠️  Warning: Unknown configuration '{config_name}', using 'development'")
        config_class = DevelopmentConfig
    
    return config_class()


def ensure_directories():
    """
    Ensure all required directories exist.
    """
    config = get_config()
    directories = [
        config.UPLOAD_FOLDER,
        config.BACKUP_FOLDER,
        os.path.dirname(config.LOG_FILE),
        os.path.dirname(config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', ''))
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")


def print_config_summary():
    """
    Print a summary of the current configuration.
    """
    config = get_config()
    
    print("\n" + "="*60)
    print("📱 Mobile Shop ERP - Configuration Summary")
    print("="*60)
    
    # Basic info
    env = os.environ.get('FLASK_ENV', 'development')
    print(f"Environment: {env.upper()}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Database: {config.SQLALCHEMY_DATABASE_URI}")
    
    # Security info
    print(f"\n🔒 Security:")
    print(f"  CSRF Enabled: {config.WTF_CSRF_ENABLED}")
    print(f"  Secure Cookies: {config.SESSION_COOKIE_SECURE}")
    
    # Application settings
    print(f"\n⚙️  Application Settings:")
    print(f"  Currency: {config.DEFAULT_CURRENCY_SYMBOL}{config.DEFAULT_CURRENCY}")
    print(f"  VAT Rate: {config.DEFAULT_VAT_RATE*100}%")
    print(f"  Default Commission: {config.DEFAULT_COMMISSION_RATE}%")
    
    # File settings
    print(f"\n📁 File Settings:")
    print(f"  Upload Folder: {config.UPLOAD_FOLDER}")
    print(f"  Max File Size: {config.MAX_CONTENT_LENGTH/1024/1024:.0f}MB")
    
    # Pagination
    print(f"\n📄 Pagination:")
    print(f"  Items per page: {config.ITEMS_PER_PAGE}")
    
    # Business hours
    print(f"\n🕒 Business Hours:")
    print(f"  Open: {config.BUSINESS_OPEN_TIME}")
    print(f"  Close: {config.BUSINESS_CLOSE_TIME}")
    print(f"  Days: {', '.join(config.BUSINESS_DAYS)}")
    
    print("="*60 + "\n")


# Auto-create directories when config is imported
if __name__ != '__main__':
    try:
        ensure_directories()
    except Exception as e:
        print(f"⚠️  Warning: Could not create directories: {e}")

# Default configuration (for backward compatibility)
Config = DevelopmentConfig