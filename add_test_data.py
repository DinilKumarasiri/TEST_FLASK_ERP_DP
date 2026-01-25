# add_test_data.py (safe version - doesn't delete existing data)
import sys
import os
from datetime import datetime, date, timedelta
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, Attendance, LeaveRequest, Commission, EmployeeProfile, 
    Customer, Invoice, InvoiceItem, Product, ProductCategory, 
    RepairJob, RepairItem, RepairInvoice, StockItem
)

def safe_populate_data():
    """Safely add test data without deleting anything"""
    print("=== Safe Test Data Addition ===\n")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if test data already exists
            test_user = User.query.filter_by(username='john_sales').first()
            if test_user:
                print("⚠️  Test data already exists! Use populate_test_data.py to recreate.")
                return
            
            # Create Flask app
            from populate_test_data import (
                create_test_users, create_test_customers, create_test_products,
                create_test_attendance, create_test_sales, create_test_repairs,
                create_test_leave_requests
            )
            
            # Create test data
            create_test_users(app)
            create_test_customers(app)
            create_test_products(app)
            create_test_attendance(app)
            create_test_sales(app)
            create_test_repairs(app)
            create_test_leave_requests(app)
            
            print("\n✅ Test data added successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    safe_populate_data()