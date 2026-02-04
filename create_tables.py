# create_tables.py
"""
Create necessary tables for barcode system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Create minimal app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost:3306/mobile_shop?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define only the new tables we need
class AttendanceLog(db.Model):
    """Barcode-based attendance logging"""
    __tablename__ = 'attendance_logs'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, nullable=False)
    scan_type = db.Column(db.String(20), nullable=False)
    scan_time = db.Column(db.DateTime, nullable=False)
    barcode_used = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AttendanceLog {self.id}>'

def create_tables():
    print("Creating barcode system tables...")
    
    with app.app_context():
        try:
            # Create attendance_logs table
            print("1. Creating attendance_logs table...")
            db.create_all()
            print("   Table created successfully")
            
            # Check if columns exist in employee_profiles
            print("\n2. Checking employee_profiles table...")
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Check for columns
            columns = inspector.get_columns('employee_profiles')
            column_names = [col['name'] for col in columns]
            
            barcode_columns = ['employee_barcode', 'barcode_image', 'barcode_generated_at', 'barcode_scans_count']
            
            for col in barcode_columns:
                if col in column_names:
                    print(f"   ✓ {col} column exists")
                else:
                    print(f"   ✗ {col} column missing")
            
            return True
            
        except Exception as e:
            print(f"\nError: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = create_tables()
    if success:
        print("\nDatabase setup completed successfully!")
    else:
        print("\nDatabase setup failed!")
    sys.exit(0 if success else 1)