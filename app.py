from flask import Flask, render_template, redirect, url_for, flash
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required
from flask_wtf import CSRFProtect
from config import Config
import os
from datetime import datetime, timedelta

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def time_ago_filter(value):
    """Format datetime as time ago"""
    if not value:
        return ''

    now = datetime.utcnow()

    if hasattr(value, 'date') and not hasattr(value, 'hour'):
        value = datetime.combine(value, datetime.min.time())

    diff = now - value

    if diff.days > 365:
        years = diff.days // 365
        return f'{years} year{"s" if years > 1 else ""} ago'
    elif diff.days > 30:
        months = diff.days // 30
        return f'{months} month{"s" if months > 1 else ""} ago'
    elif diff.days > 7:
        weeks = diff.days // 7
        return f'{weeks} week{"s" if weeks > 1 else ""} ago'
    elif diff.days > 0:
        return f'{diff.days} day{"s" if diff.days > 1 else ""} ago'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
    elif diff.seconds > 0:
        return f'{diff.seconds} second{"s" if diff.seconds > 1 else ""} ago'
    else:
        return 'just now'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Create upload folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Jinja filters
    app.jinja_env.filters['time_ago'] = time_ago_filter

    # Import models
    from modules.models import User, Commission, Attendance, LeaveRequest, Customer, Product, Supplier, StockItem, RepairJob

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

    # Context processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow(), 'timedelta': timedelta}

    @app.route('/')
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if current_user.role == 'admin':
            return redirect(url_for('pos.dashboard'))
        elif current_user.role == 'technician':
            return redirect(url_for('repair.technician_dashboard'))
        else:
            return redirect(url_for('pos.pos_home'))

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # Extra filters
    @app.template_filter('format_currency')
    def format_currency_filter(value):
        """Format value as currency"""
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return "₹0.00"

    @app.template_filter('format_date')
    def format_date_filter(value, format='%Y-%m-%d'):
        """Format date"""
        if not value:
            return ''
        if hasattr(value, 'strftime'):
            return value.strftime(format)
        return str(value)

    @app.template_filter('truncate')
    def truncate_filter(value, length=50):
        """Truncate text"""
        if not value:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + '...'

    @app.template_filter('format_time')
    def format_time_filter(value):
        """Format time"""
        if not value:
            return '--:--'
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M')
        return str(value)
    
    @app.template_filter('match')
    def match_filter(value, pattern):
        """Check if string matches pattern"""
        if not value:
            return False
        return str(value).startswith(pattern)

    # Initialize database with sample data
        # Initialize database with sample data
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Create default admin if not exists
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
                print("✓ Created default admin user: admin / admin123")
            
            # Create sample users for testing
            sample_users = [
                {'username': 'manager', 'email': 'manager@mobileshop.com', 'role': 'manager', 'password': 'manager123'},
                {'username': 'technician1', 'email': 'tech1@mobileshop.com', 'role': 'technician', 'password': 'tech123'},
                {'username': 'staff1', 'email': 'staff1@mobileshop.com', 'role': 'staff', 'password': 'staff123'},
                {'username': 'technician2', 'email': 'tech2@mobileshop.com', 'role': 'technician', 'password': 'tech123'},
            ]
            
            for user_data in sample_users:
                existing = User.query.filter_by(username=user_data['username']).first()
                if not existing:
                    user = User(
                        username=user_data['username'],
                        email=user_data['email'],
                        role=user_data['role'],
                        is_active=True
                    )
                    user.set_password(user_data['password'])
                    db.session.add(user)
                    print(f"✓ Created sample user: {user_data['username']} / {user_data['password']}")
            
            db.session.commit()
            
            # ========== CREATE 100 SAMPLE PRODUCTS ==========
            from modules.models import ProductCategory, Product
            
            # Create product categories if they don't exist
            if ProductCategory.query.count() == 0:
                categories = [
                    'Mobile Phones',
                    'Tablets',
                    'Laptops',
                    'Smart Watches',
                    'Earphones & Headphones',
                    'Chargers & Cables',
                    'Mobile Cases & Covers',
                    'Screen Protectors',
                    'Power Banks',
                    'Accessories',
                    'Spare Parts',
                    'Repair Tools',
                    'SIM Cards',
                    'Memory Cards',
                    'Bluetooth Devices'
                ]
                
                for category_name in categories:
                    category = ProductCategory(name=category_name)
                    db.session.add(category)
                print(f"✓ Created {len(categories)} product categories")
            
            db.session.commit()
            
            # Create 100 sample products
            if Product.query.count() == 0:
                categories = ProductCategory.query.all()
                
                # Mobile phone brands and models
                mobile_brands = ['Apple', 'Samsung', 'Xiaomi', 'OnePlus', 'Vivo', 'Oppo', 'Realme', 'Motorola', 'Nokia']
                mobile_models = {
                    'Apple': ['iPhone 15 Pro Max', 'iPhone 15 Pro', 'iPhone 15', 'iPhone 14 Pro', 'iPhone 14', 'iPhone 13', 'iPhone 12'],
                    'Samsung': ['Galaxy S23 Ultra', 'Galaxy S23+', 'Galaxy S23', 'Galaxy Z Fold5', 'Galaxy Z Flip5', 'Galaxy A54', 'Galaxy A34'],
                    'Xiaomi': ['Redmi Note 12 Pro', 'Redmi Note 12', 'Redmi 12', 'Mi 13 Pro', 'Mi 13', 'Poco X5 Pro', 'Poco M5'],
                    'OnePlus': ['OnePlus 11', 'OnePlus 11R', 'OnePlus Nord 3', 'OnePlus Nord CE 3', 'OnePlus 10T'],
                    'Vivo': ['Vivo X90 Pro', 'Vivo X90', 'Vivo V29', 'Vivo V27', 'Vivo Y100', 'Vivo Y56'],
                    'Oppo': ['Oppo Find N3', 'Oppo Find X6', 'Oppo Reno 10 Pro', 'Oppo Reno 10', 'Oppo A98', 'Oppo A78'],
                    'Realme': ['Realme 11 Pro+', 'Realme 11 Pro', 'Realme 11', 'Realme Narzo 60', 'Realme C55'],
                    'Motorola': ['Motorola Edge 40', 'Motorola Edge 30', 'Motorola G84', 'Motorola G54', 'Motorola E32'],
                    'Nokia': ['Nokia G42', 'Nokia C32', 'Nokia C22', 'Nokia 2660 Flip', 'Nokia 110']
                }
                
                # Accessories
                accessories = [
                    ('USB-C Cable', 'Fast Charging Cable 2m', 5.99, 12.99, 8.99),
                    ('Wireless Charger', '15W Fast Wireless Charger', 15.99, 34.99, 24.99),
                    ('Power Bank', '10000mAh Power Bank', 18.99, 39.99, 29.99),
                    ('Mobile Case', 'Shockproof Back Cover', 3.99, 9.99, 6.99),
                    ('Tempered Glass', '9H Hardness Screen Protector', 1.99, 4.99, 3.49),
                    ('Earphones', 'Wireless Bluetooth Earphones', 12.99, 29.99, 19.99),
                    ('Car Charger', '30W Fast Car Charger', 8.99, 19.99, 14.99),
                    ('OTG Adapter', 'USB-C to USB Adapter', 2.99, 7.99, 5.49),
                    ('SIM Card', '4G/5G Nano SIM', 0.50, 2.99, 1.99),
                    ('Memory Card', '128GB MicroSD Card', 12.99, 24.99, 18.99)
                ]
                
                # Spare parts
                spare_parts = [
                    ('Display Assembly', 'Original Display with Frame', 35.99, 89.99, 59.99),
                    ('Battery', 'Original Capacity Battery', 12.99, 34.99, 24.99),
                    ('Charging Port', 'Original Charging Port Flex', 8.99, 24.99, 16.99),
                    ('Back Camera', 'Original Rear Camera Module', 18.99, 49.99, 34.99),
                    ('Front Camera', 'Original Front Camera', 9.99, 29.99, 19.99),
                    ('Speaker', 'Original Loudspeaker', 5.99, 19.99, 12.99),
                    ('Vibration Motor', 'Original Vibration Motor', 4.99, 14.99, 9.99),
                    ('Volume Buttons', 'Original Volume Button Flex', 3.99, 12.99, 8.49),
                    ('Power Button', 'Original Power Button Flex', 3.99, 12.99, 8.49),
                    ('Earpiece Speaker', 'Original Earpiece Speaker', 4.99, 14.99, 9.99)
                ]
                
                product_count = 0
                
                # Create mobile phones (40 products)
                for brand in mobile_brands:
                    if brand in mobile_models:
                        for model in mobile_models[brand]:
                            product_count += 1
                            sku = f"MB{product_count:03d}"
                            product = Product(
                                sku=sku,
                                name=f"{brand} {model}",
                                category_id=categories[0].id,  # Mobile Phones category
                                description=f"Brand new {brand} {model} smartphone with latest features",
                                purchase_price=299.99 + (product_count * 10),
                                selling_price=699.99 + (product_count * 25),
                                wholesale_price=499.99 + (product_count * 15),
                                min_stock_level=5,
                                has_imei=True,
                                is_active=True
                            )
                            db.session.add(product)
                
                # Create tablets (15 products)
                tablet_brands = ['Apple iPad', 'Samsung Galaxy Tab', 'Xiaomi Pad', 'Lenovo Tab']
                tablet_models = ['Pro 12.9"', 'Pro 11"', 'Air', 'Mini', 'Standard']
                
                for i, brand in enumerate(tablet_brands):
                    for j, model in enumerate(tablet_models[:3] if i == 0 else tablet_models):
                        product_count += 1
                        sku = f"TB{product_count:03d}"
                        product = Product(
                            sku=sku,
                            name=f"{brand} {model}",
                            category_id=categories[1].id,  # Tablets category
                            description=f"{brand} {model} tablet with high-resolution display",
                            purchase_price=199.99 + (product_count * 8),
                            selling_price=449.99 + (product_count * 20),
                            wholesale_price=299.99 + (product_count * 12),
                            min_stock_level=3,
                            has_imei=True,
                            is_active=True
                        )
                        db.session.add(product)
                
                # Create accessories (25 products)
                for i, (name, desc, cost, price, wholesale) in enumerate(accessories):
                    for variation in ['Black', 'White', 'Blue', 'Red'][:2 if i % 2 == 0 else 3]:
                        product_count += 1
                        sku = f"AC{product_count:03d}"
                        product = Product(
                            sku=sku,
                            name=f"{name} ({variation})",
                            category_id=categories[5 + (i % 5)].id,  # Various accessory categories
                            description=f"{desc} - {variation} color",
                            purchase_price=cost,
                            selling_price=price,
                            wholesale_price=wholesale,
                            min_stock_level=10,
                            has_imei=False,
                            is_active=True
                        )
                        db.session.add(product)
                
                # Create spare parts (20 products)
                for i, (name, desc, cost, price, wholesale) in enumerate(spare_parts):
                    for brand in ['Apple', 'Samsung', 'Xiaomi'][:2 if i % 3 == 0 else 3]:
                        product_count += 1
                        sku = f"SP{product_count:03d}"
                        product = Product(
                            sku=sku,
                            name=f"{brand} {name}",
                            category_id=categories[10].id,  # Spare Parts category
                            description=f"Original {brand} {desc}",
                            purchase_price=cost,
                            selling_price=price,
                            wholesale_price=wholesale,
                            min_stock_level=8,
                            has_imei=False,
                            is_active=True
                        )
                        db.session.add(product)
                
                print(f"✓ Created {product_count} sample products")
            
            db.session.commit()
            
            # Create sample customers
            if Customer.query.count() == 0:
                sample_customers = [
                    {'name': 'John Smith', 'phone': '9876543210', 'email': 'john@example.com', 'address': '123 Main St'},
                    {'name': 'Jane Doe', 'phone': '8765432109', 'email': 'jane@example.com', 'address': '456 Park Ave'},
                    {'name': 'Robert Johnson', 'phone': '7654321098', 'email': 'robert@example.com', 'address': '789 Oak St'},
                    {'name': 'Sarah Williams', 'phone': '6543210987', 'email': 'sarah@example.com', 'address': '321 Pine St'},
                    {'name': 'Michael Brown', 'phone': '5432109876', 'email': 'michael@example.com', 'address': '654 Maple St'},
                ]
                for customer_data in sample_customers:
                    customer = Customer(**customer_data)
                    db.session.add(customer)
                print("✓ Created sample customers")
            
            # Create sample suppliers
            from modules.models import Supplier
            if Supplier.query.count() == 0:
                sample_suppliers = [
                    {'name': 'Mobile Distributors Inc.', 'contact_person': 'David Chen', 
                     'phone': '9876543211', 'email': 'sales@mobiledist.com', 'address': '456 Business Park'},
                    {'name': 'Gadget Wholesalers Ltd.', 'contact_person': 'Lisa Wang', 
                     'phone': '9876543212', 'email': 'orders@gadgetwholesale.com', 'address': '789 Trade Center'},
                    {'name': 'Tech Parts Corporation', 'contact_person': 'Raj Kumar', 
                     'phone': '9876543213', 'email': 'info@techparts.com', 'address': '321 Industrial Area'},
                    {'name': 'Global Electronics', 'contact_person': 'James Wilson', 
                     'phone': '9876543214', 'email': 'sales@globalelectronics.com', 'address': '654 Export Zone'},
                ]
                for supplier_data in sample_suppliers:
                    supplier = Supplier(**supplier_data)
                    db.session.add(supplier)
                print("✓ Created sample suppliers")
            
            # Create sample stock items for products
            from modules.models import StockItem
            if StockItem.query.count() == 0:
                products = Product.query.all()
                suppliers = Supplier.query.all()
                
                for product in products[:50]:  # Add stock for first 50 products
                    stock_count = 10 if product.has_imei else 25  # Less for IMEI products
                    
                    for i in range(stock_count):
                        stock_item = StockItem(
                            product_id=product.id,
                            stock_type='in',
                            quantity=1,
                            purchase_price=product.purchase_price,
                            selling_price=product.selling_price,
                            supplier_id=suppliers[i % len(suppliers)].id if suppliers else None,
                            status='available',
                            location='Warehouse Rack ' + chr(65 + (product.id % 5)) + str((product.id % 10) + 1)
                        )
                        
                        # Add IMEI for mobile phones
                        if product.has_imei and 'iPhone' in product.name:
                            stock_item.imei = f'35{"{:013d}".format(product.id * 1000 + i)}'
                        
                        db.session.add(stock_item)
                
                print("✓ Created sample stock items")
            
            # ... rest of your existing initialization code ...
            
            db.session.commit()
            print("✓ Database initialization completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during database initialization: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
    
    # Add this route in your app.py after the csrf.init_app(app) line
    @app.route('/csrf-token')
    def csrf_token_endpoint():
        from flask_wtf.csrf import generate_csrf
        return {
            'csrf_token': generate_csrf(),
            'message': 'CSRF token generated'
        }
    
    # API endpoint for system info
    @app.route('/api/system-info')
    @login_required
    def system_info():
        if current_user.role != 'admin':
            return {'error': 'Unauthorized'}, 403
        
        info = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'pending_commissions': Commission.query.filter_by(status='pending').count(),
            'pending_leaves': LeaveRequest.query.filter_by(status='pending').count(),
            'today_attendance': Attendance.query.filter(
                db.func.date(Attendance.date) == datetime.utcnow().date()
            ).count(),
            'total_customers': Customer.query.count(),
            'total_products': Product.query.count(),
            'active_repair_jobs': RepairJob.query.filter(
                RepairJob.status.in_(['received', 'diagnostic', 'repairing', 'waiting_parts'])
            ).count(),
        }
        
        return info
    
    # API endpoint for employee statistics
    @app.route('/api/employee-stats')
    @login_required
    def employee_stats():
        if current_user.role not in ['admin', 'manager']:
            return {'error': 'Unauthorized'}, 403
        
        stats = {
            'total_employees': User.query.count(),
            'active_employees': User.query.filter_by(is_active=True).count(),
            'role_distribution': {
                'admin': User.query.filter_by(role='admin', is_active=True).count(),
                'manager': User.query.filter_by(role='manager', is_active=True).count(),
                'technician': User.query.filter_by(role='technician', is_active=True).count(),
                'staff': User.query.filter_by(role='staff', is_active=True).count(),
            }
        }
        
        return stats
    
    # API endpoint for attendance stats
    @app.route('/api/attendance-stats')
    @login_required
    def attendance_stats():
        if current_user.role not in ['admin', 'manager']:
            return {'error': 'Unauthorized'}, 403
        
        today = datetime.utcnow().date()
        attendance_today = Attendance.query.filter_by(date=today).all()
        
        stats = {
            'total': len(attendance_today),
            'present': len([a for a in attendance_today if a.status == 'present']),
            'absent': len([a for a in attendance_today if a.status == 'absent']),
            'leave': len([a for a in attendance_today if a.status == 'leave']),
        }
        
        return stats
    
    # API endpoint for leave stats
    @app.route('/api/leave-stats')
    @login_required
    def leave_stats():
        if current_user.role not in ['admin', 'manager']:
            return {'error': 'Unauthorized'}, 403
        
        stats = {
            'total': LeaveRequest.query.count(),
            'pending': LeaveRequest.query.filter_by(status='pending').count(),
            'approved': LeaveRequest.query.filter_by(status='approved').count(),
            'rejected': LeaveRequest.query.filter_by(status='rejected').count(),
        }
        
        return stats
    
    # Test route for debugging
    @app.route('/test-db')
    def test_db():
        try:
            users = User.query.all()
            return f'Database connected successfully! Found {len(users)} users.'
        except Exception as e:
            return f'Database error: {str(e)}'
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)