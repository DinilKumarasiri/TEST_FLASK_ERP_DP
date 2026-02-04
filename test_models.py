# test_models.py
"""
Test script to verify models are working
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a minimal Flask app
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost:3306/mobile_shop?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

db = SQLAlchemy(app)

# Define models directly in test script
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    is_active = db.Column(db.Boolean, default=True)

class AttendanceLog(db.Model):
    """Barcode-based attendance logging"""
    __tablename__ = 'attendance_logs'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_type = db.Column(db.String(20), nullable=False)
    scan_time = db.Column(db.DateTime, nullable=False)
    barcode_used = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    employee = db.relationship('User', foreign_keys=[employee_id], backref='attendance_logs')

def test_models():
    print("Testing models...")
    
    with app.app_context():
        try:
            # Try to create tables if they don't exist
            print("1. Creating tables if they don't exist...")
            db.create_all()
            print("   Tables created/verified successfully")
            
            # Try to query
            print("\n2. Testing queries...")
            user_count = User.query.count()
            print(f"   Total users: {user_count}")
            
            # Check if attendance_logs table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"   Existing tables: {', '.join(tables)}")
            
            if 'attendance_logs' in tables:
                print("   ✓ attendance_logs table exists")
                logs_count = AttendanceLog.query.count()
                print(f"   Total attendance logs: {logs_count}")
            else:
                print("   ✗ attendance_logs table does not exist")
            
            return True
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    from datetime import datetime
    success = test_models()
    sys.exit(0 if success else 1)