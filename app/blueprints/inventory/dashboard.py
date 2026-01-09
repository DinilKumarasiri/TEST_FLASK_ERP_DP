from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from ... import db
from ...models import Product, StockItem
from sqlalchemy import text
from . import inventory_bp

@inventory_bp.route('/')
@login_required
def inventory_dashboard():
    # Get inventory summary
    total_products = Product.query.filter_by(is_active=True).count()
    
    # Calculate total stock value
    total_value = 0
    for product in Product.query.filter_by(is_active=True).all():
        # Use raw SQL to avoid column issues
        stock_count_result = db.session.execute(
            text("SELECT COUNT(*) FROM stock_items WHERE product_id = :product_id AND status = :status"),
            {'product_id': product.id, 'status': 'available'}
        ).scalar()
        stock_count = stock_count_result or 0
        total_value += stock_count * product.purchase_price
    
    # Low stock products
    low_stock_products = []
    for product in Product.query.filter_by(is_active=True).all():
        stock_count_result = db.session.execute(
            text("SELECT COUNT(*) FROM stock_items WHERE product_id = :product_id AND status = :status"),
            {'product_id': product.id, 'status': 'available'}
        ).scalar()
        stock_count = stock_count_result or 0
        
        if stock_count <= product.min_stock_level:
            low_stock_products.append({
                'product': product,
                'stock_count': stock_count
            })
    
    # Recent stock movements
    recent_stock = StockItem.query.order_by(
        StockItem.created_at.desc()
    ).limit(10).all()
    
    return render_template('inventory/dashboard.html',
                         total_products=total_products,
                         total_value=total_value,
                         low_stock_products=low_stock_products,
                         recent_stock=recent_stock,
                         title='Inventory Dashboard')

@inventory_bp.route('/stock-report')
@login_required
def stock_report():
    # Get all products with stock information
    products = Product.query.filter_by(is_active=True).all()
    
    stock_data = []
    for product in products:
        stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        
        stock_value = stock_count * product.purchase_price
        
        stock_data.append({
            'product': product,
            'stock_count': stock_count,
            'stock_value': stock_value,
            'status': 'low' if stock_count <= product.min_stock_level else 'ok'
        })
    
    # Sort by stock value (descending)
    stock_data.sort(key=lambda x: x['stock_value'], reverse=True)
    
    return render_template('inventory/stock_report.html',
                         stock_data=stock_data,
                         title='Stock Report')

# Add test data creation route for debugging
@inventory_bp.route('/test/create-test-data')
@login_required
def create_test_data():
    """Create test data for inventory module"""
    from ...models import Supplier, ProductCategory, Product
    try:
        # Create a test supplier
        supplier = Supplier(
            name='Mobile Parts Supplier',
            contact_person='John Doe',
            phone='+94 77 123 4567',
            email='supplier@example.com',
            address='123 Supplier Street, Colombo',
            gst_number='GST123456789'
        )
        db.session.add(supplier)
        
        # Create a test product category
        category = ProductCategory(
            name='Mobile Accessories',
            description='Mobile phone accessories'
        )
        db.session.add(category)
        db.session.flush()  # Get category ID
        
        # Create test products
        products_data = [
            {'sku': 'PHN001', 'name': 'iPhone 13 Screen', 'purchase_price': 5000, 'selling_price': 7500, 'category_id': category.id},
            {'sku': 'PHN002', 'name': 'Samsung Battery', 'purchase_price': 1500, 'selling_price': 2500, 'category_id': category.id},
            {'sku': 'PHN003', 'name': 'USB-C Cable', 'purchase_price': 200, 'selling_price': 500, 'category_id': category.id},
            {'sku': 'PHN004', 'name': 'Phone Case', 'purchase_price': 300, 'selling_price': 800, 'category_id': category.id},
        ]
        
        for prod_data in products_data:
            product = Product(
                sku=prod_data['sku'],
                name=prod_data['name'],
                category_id=prod_data['category_id'],
                purchase_price=prod_data['purchase_price'],
                selling_price=prod_data['selling_price'],
                min_stock_level=5,
                is_active=True
            )
            db.session.add(product)
        
        db.session.commit()
        
        flash('Test data created successfully!', 'success')
        return redirect(url_for('inventory.inventory_dashboard'))
    except Exception as e:
        flash(f'Error creating test data: {str(e)}', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
