import os
import sys

# Add your app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set production environment
os.environ['FLASK_ENV'] = 'production'

# Import and create the app
from app import create_app
from config import ProductionConfig

# Create application instance
application = create_app(ProductionConfig())

print("Mobile Shop ERP - Production Server Started")