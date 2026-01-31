# populate_test_data.py
import sys
import os
from datetime import datetime, date, timedelta
import random

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import (
    User, Attendance, LeaveRequest, Commission, EmployeeProfile, 
    Customer, Invoice, InvoiceItem, Product, ProductCategory, 
    RepairJob, RepairItem, RepairInvoice, StockItem
)
from app.blueprints.employee.forms import EmployeeForm
from werkzeug.security import generate_password_hash

def create_test_users(app):
    """Create test users with different roles"""
    print("Creating test users...")
    
    users_data = [
        # admin user already exists
        {
            'username': 'john_sales',
            'email': 'john@mobileshop.com',
            'role': 'staff',
            'full_name': 'John Smith',
            'job_title': 'sales_executive',
            'department': 'sales',
            'commission_rate': 5.0,
            'sales_target_monthly': 50000.0
        },
        {
            'username': 'jane_manager',
            'email': 'jane@mobileshop.com',
            'role': 'manager',
            'full_name': 'Jane Doe',
            'job_title': 'sales_manager',
            'department': 'sales',
            'commission_rate': 3.0,
            'sales_target_monthly': 100000.0
        },
        {
            'username': 'mike_tech',
            'email': 'mike@mobileshop.com',
            'role': 'technician',
            'full_name': 'Mike Johnson',
            'job_title': 'repair_technician',
            'department': 'repair',
            'commission_rate': 2.0
        },
        {
            'username': 'sarah_tech',
            'email': 'sarah@mobileshop.com',
            'role': 'technician',
            'full_name': 'Sarah Williams',
            'job_title': 'senior_technician',
            'department': 'repair',
            'commission_rate': 3.0
        },
        {
            'username': 'tom_staff',
            'email': 'tom@mobileshop.com',
            'role': 'staff',
            'full_name': 'Tom Brown',
            'job_title': 'sales_executive',
            'department': 'sales',
            'commission_rate': 5.0,
            'sales_target_monthly': 40000.0
        },
        {
            'username': 'lisa_staff',
            'email': 'lisa@mobileshop.com',
            'role': 'staff',
            'full_name': 'Lisa Wilson',
            'job_title': 'sales_executive',
            'department': 'sales',
            'commission_rate': 5.0,
            'sales_target_monthly': 45000.0
        }
    ]
    
    for user_data in users_data:
        # Check if user already exists
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if existing_user:
            print(f"User {user_data['username']} already exists")
            continue
            
        # Create user
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()  # Get the user ID
        
        # Create employee profile
        profile = EmployeeProfile(
            user_id=user.id,
            full_name=user_data['full_name'],
            date_of_joining=date(2024, 1, 1),
            job_title=user_data['job_title'],
            department=user_data['department'],
            employment_type='full_time',
            employee_code=f"EMP{user.id:04d}",
            basic_salary=random.randint(30000, 60000),
            commission_rate=user_data.get('commission_rate', 0.0),
            sales_target_monthly=user_data.get('sales_target_monthly', 0.0)
        )
        db.session.add(profile)
        
        print(f"Created user: {user_data['username']} ({user_data['role']})")
    
    db.session.commit()
    print("Test users created successfully!")

def create_test_customers(app):
    """Create test customers"""
    print("\nCreating test customers...")
    
    customers_data = [
        {'name': 'Raj Kumar', 'phone': '9876543210', 'email': 'raj@gmail.com'},
        {'name': 'Priya Sharma', 'phone': '9876543211', 'email': 'priya@gmail.com'},
        {'name': 'Amit Patel', 'phone': '9876543212', 'email': 'amit@gmail.com'},
        {'name': 'Sneha Gupta', 'phone': '9876543213', 'email': 'sneha@gmail.com'},
        {'name': 'Vikram Singh', 'phone': '9876543214', 'email': 'vikram@gmail.com'},
        {'name': 'Anjali Mehta', 'phone': '9876543215', 'email': 'anjali@gmail.com'},
        {'name': 'Rahul Verma', 'phone': '9876543216', 'email': 'rahul@gmail.com'},
        {'name': 'Kavita Joshi', 'phone': '9876543217', 'email': 'kavita@gmail.com'},
    ]
    
    for cust_data in customers_data:
        customer = Customer.query.filter_by(phone=cust_data['phone']).first()
        if not customer:
            customer = Customer(
                name=cust_data['name'],
                phone=cust_data['phone'],
                email=cust_data['email']
            )
            db.session.add(customer)
    
    db.session.commit()
    print(f"Created {len(customers_data)} test customers")

def create_test_products(app):
    """Create test products"""
    print("\nCreating test products...")
    
    # Create categories
    categories = ['Mobile Phones', 'Tablets', 'Accessories', 'Repair Parts']
    category_objects = {}
    
    for cat_name in categories:
        category = ProductCategory.query.filter_by(name=cat_name).first()
        if not category:
            category = ProductCategory(name=cat_name)
            db.session.add(category)
            db.session.flush()
        category_objects[cat_name] = category
    
    db.session.commit()
    
    # Create products
    products_data = [
        {'sku': 'IPHONE14-128', 'name': 'iPhone 14 128GB', 'category': 'Mobile Phones', 
         'purchase_price': 70000, 'selling_price': 79999, 'min_stock': 10},
        {'sku': 'SAMSUNG-S23', 'name': 'Samsung Galaxy S23', 'category': 'Mobile Phones',
         'purchase_price': 65000, 'selling_price': 74999, 'min_stock': 8},
        {'sku': 'ONEPLUS-11R', 'name': 'OnePlus 11R', 'category': 'Mobile Phones',
         'purchase_price': 35000, 'selling_price': 39999, 'min_stock': 15},
        {'sku': 'IPAD-10', 'name': 'iPad 10th Gen', 'category': 'Tablets',
         'purchase_price': 40000, 'selling_price': 45999, 'min_stock': 5},
        {'sku': 'SAMSUNG-TAB', 'name': 'Samsung Tab S8', 'category': 'Tablets',
         'purchase_price': 55000, 'selling_price': 59999, 'min_stock': 4},
        {'sku': 'CASE-IPH14', 'name': 'iPhone 14 Case', 'category': 'Accessories',
         'purchase_price': 500, 'selling_price': 999, 'min_stock': 50},
        {'sku': 'SCREEN-GUARD', 'name': 'Tempered Glass', 'category': 'Accessories',
         'purchase_price': 100, 'selling_price': 299, 'min_stock': 100},
        {'sku': 'CHARGER-USB', 'name': 'Fast Charger', 'category': 'Accessories',
         'purchase_price': 800, 'selling_price': 1499, 'min_stock': 30},
        {'sku': 'BATTERY-IPH', 'name': 'iPhone Battery', 'category': 'Repair Parts',
         'purchase_price': 2000, 'selling_price': 3499, 'min_stock': 20},
        {'sku': 'SCREEN-IPH14', 'name': 'iPhone 14 Screen', 'category': 'Repair Parts',
         'purchase_price': 8000, 'selling_price': 11999, 'min_stock': 10},
    ]
    
    for prod_data in products_data:
        product = Product.query.filter_by(sku=prod_data['sku']).first()
        if not product:
            product = Product(
                sku=prod_data['sku'],
                name=prod_data['name'],
                category_id=category_objects[prod_data['category']].id,
                purchase_price=prod_data['purchase_price'],
                selling_price=prod_data['selling_price'],
                min_stock_level=prod_data['min_stock'],
                is_active=True
            )
            db.session.add(product)
    
    db.session.commit()
    print(f"Created {len(products_data)} test products")

def create_test_attendance(app):
    """Create test attendance records for the current month"""
    print("\nCreating test attendance records...")
    
    users = User.query.filter_by(is_active=True).all()
    current_date = date.today()
    current_month = current_date.month
    current_year = current_date.year
    
    # Get the first day of current month
    month_start = date(current_year, current_month, 1)
    
    # Generate attendance for each day of current month up to today
    day_count = (current_date - month_start).days + 1
    
    for user in users:
        for day_offset in range(day_count):
            attendance_date = month_start + timedelta(days=day_offset)
            
            # Skip weekends (Saturday=5, Sunday=6)
            if attendance_date.weekday() >= 5:
                continue
                
            # Check if attendance record already exists
            existing = Attendance.query.filter_by(
                employee_id=user.id,
                date=attendance_date
            ).first()
            
            if existing:
                continue
            
            # Create attendance record
            # Randomize attendance status
            status_random = random.random()
            
            if status_random < 0.85:  # 85% present
                status = 'present'
                check_in = datetime(attendance_date.year, attendance_date.month, attendance_date.day, 
                                   random.randint(9, 10), random.randint(0, 59))
                check_out = datetime(attendance_date.year, attendance_date.month, attendance_date.day,
                                    random.randint(17, 18), random.randint(0, 59))
                total_hours = (check_out - check_in).seconds / 3600
                
                attendance = Attendance(
                    employee_id=user.id,
                    date=attendance_date,
                    status=status,
                    check_in=check_in,
                    check_out=check_out,
                    total_hours=round(total_hours, 1)
                )
            elif status_random < 0.90:  # 5% leave
                status = 'leave'
                attendance = Attendance(
                    employee_id=user.id,
                    date=attendance_date,
                    status=status
                )
            else:  # 10% absent
                status = 'absent'
                attendance = Attendance(
                    employee_id=user.id,
                    date=attendance_date,
                    status=status
                )
            
            db.session.add(attendance)
    
    db.session.commit()
    print(f"Created attendance records for {day_count} days")

def create_test_sales(app):
    """Create test sales invoices for the current month"""
    print("\nCreating test sales invoices...")
    
    # Get staff users
    staff_users = User.query.filter_by(role='staff').all()
    manager_users = User.query.filter_by(role='manager').all()
    all_sales_users = staff_users + manager_users
    
    customers = Customer.query.all()
    products = Product.query.filter_by(is_active=True).all()
    
    current_date = date.today()
    current_month = current_date.month
    current_year = current_date.year
    month_start = date(current_year, current_month, 1)
    
    # Generate invoices for current month
    invoice_count = 0
    
    for user in all_sales_users:
        # Each sales person gets random number of invoices this month
        num_invoices = random.randint(3, 8)
        
        for i in range(num_invoices):
            invoice_date = month_start + timedelta(days=random.randint(0, (current_date - month_start).days))
            
            # Select random customer
            customer = random.choice(customers)
            
            # Create invoice
            invoice = Invoice(
                invoice_number = f"INV-{invoice_count + 1:06d}",
                customer_id=customer.id,
                customer_name=customer.name,
                customer_phone=customer.phone,
                date=datetime(invoice_date.year, invoice_date.month, invoice_date.day,
                            random.randint(10, 18), random.randint(0, 59)),
                created_by=user.id
            )
            
            # Add items to invoice
            num_items = random.randint(1, 3)
            subtotal = 0
            
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 2)
                unit_price = product.selling_price
                discount = random.choice([0, 50, 100, 200])  # Random small discount
                item_total = (unit_price * quantity) - discount
                subtotal += item_total
                
                invoice_item = InvoiceItem(
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount=discount,
                    total=item_total
                )
                invoice.items.append(invoice_item)
            
            # Calculate totals
            invoice.subtotal = subtotal
            invoice.tax = subtotal * 0.15  # 15% tax
            invoice.total = subtotal + invoice.tax
            invoice.payment_status = random.choice(['paid', 'paid', 'paid', 'partial'])  # Mostly paid
            invoice.payment_method = random.choice(['cash', 'card', 'online'])
            
            db.session.add(invoice)
            invoice_count += 1
            
            # Create commission record for the sales person
            if user.role in ['staff', 'manager']:
                # Get commission rate from profile
                profile = EmployeeProfile.query.filter_by(user_id=user.id).first()
                commission_rate = profile.commission_rate if profile else 5.0
                
                commission_amount = subtotal * (commission_rate / 100)
                
                commission = Commission(
                    employee_id=user.id,
                    invoice_id=invoice.id,
                    sale_amount=subtotal,
                    commission_rate=commission_rate,
                    commission_amount=commission_amount,
                    status='paid' if invoice.payment_status == 'paid' else 'pending'
                )
                db.session.add(commission)
    
    db.session.commit()
    print(f"Created {invoice_count} test invoices with commissions")

def create_test_repairs(app):
    """Create test repair jobs for the current month"""
    print("\nCreating test repair jobs...")
    
    technician_users = User.query.filter_by(role='technician').all()
    customers = Customer.query.all()
    
    current_date = date.today()
    current_month = current_date.month
    current_year = current_date.year
    month_start = date(current_year, current_month, 1)
    
    device_types = ['Mobile', 'Tablet', 'Laptop']
    brands = ['Apple', 'Samsung', 'OnePlus', 'Xiaomi', 'Realme']
    issues = [
        'Screen broken', 'Battery replacement', 'Water damage',
        'Charging port issue', 'Software problem', 'Speaker not working',
        'Camera not working', 'Overheating issue'
    ]
    
    repair_count = 0
    
    for tech in technician_users:
        # Each technician gets random number of repair jobs
        num_repairs = random.randint(4, 12)
        
        for i in range(num_repairs):
            created_date = month_start + timedelta(days=random.randint(0, (current_date - month_start).days))
            
            # Determine status based on date
            days_since_created = (current_date - created_date).days
            if days_since_created > 7:
                status = 'completed'
                completed_date = created_date + timedelta(days=random.randint(1, 5))
            elif days_since_created > 3:
                status = random.choice(['diagnostic', 'repairing', 'waiting_parts'])
                completed_date = None
            else:
                status = 'received'
                completed_date = None
            
            customer = random.choice(customers)
            device_type = random.choice(device_types)
            brand = random.choice(brands)
            
            repair = RepairJob(
                job_number = f"RJ-{repair_count + 1:06d}",
                customer_id=customer.id,
                device_type=device_type,
                brand=brand,
                model=f"{brand} {random.choice(['A1', 'B2', 'C3', 'D4', 'E5'])}",
                imei=f"{random.randint(100000000000000, 999999999999999)}" if device_type == 'Mobile' else None,
                issue_description=random.choice(issues),
                estimated_cost=random.randint(500, 5000),
                status=status,
                technician_id=tech.id,
                created_at=datetime(created_date.year, created_date.month, created_date.day,
                                  random.randint(9, 17), random.randint(0, 59)),
                completed_date=datetime(completed_date.year, completed_date.month, completed_date.day,
                                      random.randint(12, 18), random.randint(0, 59)) if completed_date else None
            )
            
            if status == 'completed' and completed_date:
                repair.final_cost = repair.estimated_cost * random.uniform(0.9, 1.1)  # +/- 10%
                repair.warranty_period = random.choice([0, 3, 6])
                repair.delivered_date = completed_date + timedelta(days=random.randint(0, 2))
            
            db.session.add(repair)
            repair_count += 1
    
    db.session.commit()
    print(f"Created {repair_count} test repair jobs")

def create_test_leave_requests(app):
    """Create test leave requests"""
    print("\nCreating test leave requests...")
    
    users = User.query.filter_by(is_active=True).all()
    leave_types = ['casual', 'sick', 'annual', 'other']
    
    # Create some pending leave requests
    for i in range(3):
        user = random.choice(users)
        leave_type = random.choice(leave_types)
        start_date = date.today() + timedelta(days=random.randint(1, 10))
        end_date = start_date + timedelta(days=random.randint(1, 5))
        days_requested = (end_date - start_date).days + 1
        
        leave = LeaveRequest(
            employee_id=user.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=f"Test {leave_type} leave reason {i+1}",
            status='pending'
        )
        db.session.add(leave)
    
    # Create some approved/rejected leave requests from past
    for i in range(5):
        user = random.choice(users)
        leave_type = random.choice(leave_types)
        start_date = date.today() - timedelta(days=random.randint(10, 30))
        end_date = start_date + timedelta(days=random.randint(1, 3))
        days_requested = (end_date - start_date).days + 1
        
        status = random.choice(['approved', 'rejected'])
        
        leave = LeaveRequest(
            employee_id=user.id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days_requested=days_requested,
            reason=f"Past {leave_type} leave reason {i+1}",
            status=status,
            approved_by=1,  # admin user
            approved_date=start_date - timedelta(days=1)
        )
        db.session.add(leave)
    
    db.session.commit()
    print("Created test leave requests")

def main():
    """Main function to populate test data"""
    print("=== Mobile Shop ERP - Test Data Population ===\n")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Clear existing test data (optional - be careful!)
            # Uncomment if you want to clean first
            # print("Clearing existing test data...")
            # db.session.query(Commission).delete()
            # db.session.query(InvoiceItem).delete()
            # db.session.query(Invoice).delete()
            # db.session.query(RepairJob).delete()
            # db.session.query(Attendance).delete()
            # db.session.query(LeaveRequest).delete()
            # db.session.query(EmployeeProfile).filter(EmployeeProfile.user_id != 1).delete()
            # db.session.query(User).filter(User.id != 1).delete()
            # db.session.commit()
            
            # Create test data
            create_test_users(app)
            create_test_customers(app)
            create_test_products(app)
            create_test_attendance(app)
            create_test_sales(app)
            create_test_repairs(app)
            create_test_leave_requests(app)
            
            print("\n" + "="*50)
            print("✅ TEST DATA POPULATION COMPLETED SUCCESSFULLY!")
            print("="*50)
            print("\nTest Credentials:")
            print("- Admin: admin / admin123")
            print("- Sales Staff: john_sales / password123")
            print("- Manager: jane_manager / password123")
            print("- Technician: mike_tech / password123")
            print("\nAll other users: username / password123")
            
            # Show summary statistics
            print("\n📊 Data Summary:")
            print(f"- Total Users: {User.query.count()}")
            print(f"- Total Customers: {Customer.query.count()}")
            print(f"- Total Products: {Product.query.count()}")
            print(f"- Total Invoices: {Invoice.query.count()}")
            print(f"- Total Repair Jobs: {RepairJob.query.count()}")
            print(f"- Total Attendance Records: {Attendance.query.count()}")
            print(f"- Total Leave Requests: {LeaveRequest.query.count()}")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()