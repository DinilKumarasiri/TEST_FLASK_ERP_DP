#!/usr/bin/env python3
"""
Sample Data Initialization Script
Run this script to populate the database with sample data for development/testing.
Usage: python init_sample_data.py
"""

from app import create_app
from app.models import (
    User, ProductCategory, Product, Customer, Supplier, StockItem
)
from app import db

def init_sample_data():
    """Initialize sample data for development"""
    app = create_app()

    with app.app_context():
        try:
            print("Initializing sample data...")

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

            # Create sample products (reduced number for faster startup)
            if Product.query.count() == 0:
                categories = ProductCategory.query.all()

                # Create just a few sample products instead of 100+
                sample_products = [
                    ('MB001', 'Apple iPhone 15 Pro', categories[0].id, 'Latest iPhone model', 899.99, 1199.99, 999.99, True),
                    ('MB002', 'Samsung Galaxy S23', categories[0].id, 'Android flagship', 699.99, 899.99, 799.99, True),
                    ('AC001', 'USB-C Cable', categories[5].id, 'Fast charging cable', 5.99, 12.99, 8.99, False),
                    ('AC002', 'Wireless Charger', categories[5].id, '15W wireless charger', 15.99, 34.99, 24.99, False),
                    ('SP001', 'iPhone Display', categories[10].id, 'Original iPhone display', 35.99, 89.99, 59.99, False),
                ]

                for sku, name, cat_id, desc, pur, sell, whole, imei in sample_products:
                    product = Product(
                        sku=sku,
                        name=name,
                        category_id=cat_id,
                        description=desc,
                        purchase_price=pur,
                        selling_price=sell,
                        wholesale_price=whole,
                        min_stock_level=5,
                        has_imei=imei,
                        is_active=True
                    )
                    db.session.add(product)

                print(f"✓ Created {len(sample_products)} sample products")

            db.session.commit()

            # Create sample customers
            if Customer.query.count() == 0:
                sample_customers = [
                    {'name': 'John Smith', 'phone': '9876543210', 'email': 'john@example.com', 'address': '123 Main St'},
                    {'name': 'Jane Doe', 'phone': '8765432109', 'email': 'jane@example.com', 'address': '456 Park Ave'},
                ]
                for customer_data in sample_customers:
                    customer = Customer(**customer_data)
                    db.session.add(customer)
                print("✓ Created sample customers")

            # Create sample suppliers
            if Supplier.query.count() == 0:
                sample_suppliers = [
                    {'name': 'Mobile Distributors Inc.', 'contact_person': 'David Chen',
                     'phone': '9876543211', 'email': 'sales@mobiledist.com', 'address': '456 Business Park'},
                    {'name': 'Tech Parts Corporation', 'contact_person': 'Raj Kumar',
                     'phone': '9876543213', 'email': 'info@techparts.com', 'address': '321 Industrial Area'},
                ]
                for supplier_data in sample_suppliers:
                    supplier = Supplier(**supplier_data)
                    db.session.add(supplier)
                print("✓ Created sample suppliers")

            # Create sample stock items
            if StockItem.query.count() == 0:
                products = Product.query.all()
                suppliers = Supplier.query.all()

                for product in products[:3]:  # Just first 3 products
                    stock_count = 5 if product.has_imei else 10

                    for i in range(stock_count):
                        stock_item = StockItem(
                            product_id=product.id,
                            stock_type='in',
                            quantity=1,
                            purchase_price=product.purchase_price,
                            selling_price=product.selling_price,
                            supplier_id=suppliers[i % len(suppliers)].id if suppliers else None,
                            status='available',
                            location='Warehouse A1'
                        )

                        if product.has_imei and 'iPhone' in product.name:
                            stock_item.imei = f'35{"{:013d}".format(product.id * 1000 + i)}'

                        db.session.add(stock_item)

                print("✓ Created sample stock items")

            db.session.commit()
            print("✓ Sample data initialization completed successfully!")

        except Exception as e:
            db.session.rollback()
            print(f"✗ Error during sample data initialization: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    init_sample_data()