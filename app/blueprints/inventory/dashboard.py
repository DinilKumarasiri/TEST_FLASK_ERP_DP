from flask import render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import Product, StockItem
from sqlalchemy import text, func
from datetime import datetime, timedelta
from . import inventory_bp
from app.utils.permissions import staff_required

@inventory_bp.route('/')
@login_required
@staff_required  # Changed from checking 'admin' or 'manager'
def inventory_dashboard():
    """
    Inventory Dashboard - Shows summary, low stock alerts, and aggregated stock movements
    """
    try:
        # Get inventory summary
        total_products = Product.query.filter_by(is_active=True).count()
        
        # Calculate total stock value
        total_value = 0
        for product in Product.query.filter_by(is_active=True).all():
            # TEMPORARY FIX: Use raw SQL to avoid column issues
            try:
                stock_count = StockItem.query.filter_by(
                    product_id=product.id,
                    status='available'
                ).count()
            except:
                # Fallback if columns don't exist yet
                from sqlalchemy import text
                result = db.session.execute(
                    text("SELECT COUNT(*) FROM stock_items WHERE product_id = :pid AND status = 'available'"),
                    {"pid": product.id}
                ).scalar()
                stock_count = result or 0
            
            if product.purchase_price:
                total_value += stock_count * product.purchase_price
            else:
                total_value += stock_count * (product.selling_price * 0.7) 
        
        # Low stock products
        low_stock_products = []
        for product in Product.query.filter_by(is_active=True).all():
            try:
                stock_count = StockItem.query.filter_by(
                    product_id=product.id,
                    status='available'
                ).count()
            except:
                from sqlalchemy import text
                result = db.session.execute(
                    text("SELECT COUNT(*) FROM stock_items WHERE product_id = :pid AND status = 'available'"),
                    {"pid": product.id}
                ).scalar()
                stock_count = result or 0
            
            if stock_count <= product.min_stock_level:
                low_stock_products.append({
                    'product': product,
                    'stock_count': stock_count
                })
        
        # Get recent stock items (last 24 hours) for aggregation
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        try:
            # Try the new query
            recent_items = StockItem.query.join(Product).filter(
                StockItem.created_at >= twenty_four_hours_ago
            ).all()
        except:
            # Fallback to simple query
            from sqlalchemy import text
            recent_items_query = """
                SELECT si.*, p.name as product_name, p.sku 
                FROM stock_items si
                LEFT JOIN products p ON si.product_id = p.id
                WHERE si.created_at >= :time_limit
                ORDER BY si.created_at DESC
                LIMIT 50
            """
            recent_items = db.session.execute(
                text(recent_items_query),
                {"time_limit": twenty_four_hours_ago}
            ).fetchall()
        
        # Aggregate by product name, stock type, and status
        aggregated = {}
        
        if isinstance(recent_items, list):
            for item in recent_items:
                if hasattr(item, 'product_id'):
                    # It's a StockItem object
                    product_id = item.product_id
                    product_name = item.product.name if item.product else 'Unknown'
                    sku = item.product.sku if item.product else ''
                    stock_type = item.stock_type
                    status = item.status
                else:
                    # It's a result from raw query
                    product_id = item.product_id
                    product_name = item.product_name
                    sku = item.sku
                    stock_type = item.stock_type
                    status = item.status
                
                # Create a unique key for aggregation
                key = f"{product_id}_{stock_type}_{status}"
                
                if key in aggregated:
                    aggregated[key]['quantity'] += 1
                else:
                    aggregated[key] = {
                        'product_name': product_name,
                        'product_id': product_id,
                        'sku': sku,
                        'stock_type': stock_type,
                        'status': status,
                        'quantity': 1,
                        'product': None  # Can't assign product object from raw query
                    }
        
        # Convert to list
        recent_stock = list(aggregated.values())
        
        # Sort by quantity (highest first) for better visibility
        recent_stock.sort(key=lambda x: x['quantity'], reverse=True)
        
        # Limit to 10 items
        recent_stock = recent_stock[:10]
        
        return render_template('inventory/dashboard.html',
                            total_products=total_products,
                            total_value=total_value,
                            low_stock_products=low_stock_products,
                            recent_stock=recent_stock,
                            title='Inventory Dashboard')
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        # Fallback to basic view
        return render_template('inventory/dashboard.html',
                            total_products=0,
                            total_value=0,
                            low_stock_products=[],
                            recent_stock=[],
                            title='Inventory Dashboard')

@inventory_bp.route('/stock-report')
@login_required
@staff_required  # Changed from checking 'admin' or 'manager'
def stock_report():
    """
    Stock Report - Shows all products with stock information
    """
    try:
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
    
    except Exception as e:
        flash(f'Error loading stock report: {str(e)}', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

@inventory_bp.route('/test/create-test-data')
@login_required
def create_test_data():
    """Create test data for inventory module"""
    from ...models import Supplier, ProductCategory, Product, StockItem
    
    # Changed: Only admin can create test data
    if current_user.role != 'admin':
        flash('Only admin can create test data', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))
    
    try:
        # Check if test data already exists
        existing_supplier = Supplier.query.filter_by(name='Mobile Parts Supplier').first()
        if existing_supplier:
            flash('Test data already exists!', 'warning')
            return redirect(url_for('inventory.inventory_dashboard'))
        
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
        
        # Create product categories
        categories_data = [
            {'name': 'Mobile Accessories', 'description': 'Mobile phone accessories'},
            {'name': 'Mobile Phones', 'description': 'Smartphones and feature phones'},
            {'name': 'Repair Parts', 'description': 'Spare parts for phone repair'},
            {'name': 'Chargers & Cables', 'description': 'Chargers and data cables'}
        ]
        
        categories = {}
        for cat_data in categories_data:
            category = ProductCategory(
                name=cat_data['name'],
                description=cat_data['description']
            )
            db.session.add(category)
            db.session.flush()  # Get category ID
            categories[cat_data['name']] = category.id
        
        # Create test products
        products_data = [
            {'sku': 'IP13-SCRN', 'name': 'iPhone 13 Screen', 'category': 'Repair Parts', 
             'purchase_price': 5000, 'selling_price': 7500, 'min_stock': 5, 'has_imei': False},
            {'sku': 'SMB-BATT', 'name': 'Samsung Battery', 'category': 'Repair Parts',
             'purchase_price': 1500, 'selling_price': 2500, 'min_stock': 10, 'has_imei': False},
            {'sku': 'USB-C-3M', 'name': 'USB-C Cable 3m', 'category': 'Chargers & Cables',
             'purchase_price': 200, 'selling_price': 500, 'min_stock': 20, 'has_imei': False},
            {'sku': 'PH-CASE-BLK', 'name': 'Phone Case Black', 'category': 'Mobile Accessories',
             'purchase_price': 300, 'selling_price': 800, 'min_stock': 15, 'has_imei': False},
            {'sku': 'IP13-128-BLK', 'name': 'iPhone 13 128GB Black', 'category': 'Mobile Phones',
             'purchase_price': 85000, 'selling_price': 110000, 'min_stock': 3, 'has_imei': True},
            {'sku': 'S23-256-BLU', 'name': 'Samsung S23 256GB Blue', 'category': 'Mobile Phones',
             'purchase_price': 95000, 'selling_price': 120000, 'min_stock': 2, 'has_imei': True},
            {'sku': 'FAST-CHG', 'name': 'Fast Charger 25W', 'category': 'Chargers & Cables',
             'purchase_price': 1200, 'selling_price': 2000, 'min_stock': 8, 'has_imei': False},
            {'sku': 'EAR-BUD', 'name': 'Wireless Earbuds', 'category': 'Mobile Accessories',
             'purchase_price': 2500, 'selling_price': 4000, 'min_stock': 6, 'has_imei': False}
        ]
        
        created_products = []
        for prod_data in products_data:
            product = Product(
                sku=prod_data['sku'],
                name=prod_data['name'],
                category_id=categories[prod_data['category']],
                purchase_price=prod_data['purchase_price'],
                selling_price=prod_data['selling_price'],
                wholesale_price=prod_data['selling_price'] * 0.85,  # 15% discount
                min_stock_level=prod_data['min_stock'],
                has_imei=prod_data['has_imei'],
                is_active=True,
                description=f"Test product: {prod_data['name']}"
            )
            db.session.add(product)
            db.session.flush()  # Get product ID
            created_products.append(product)
        
        # Create some stock items for testing
        from datetime import datetime, timedelta
        
        # Add stock for iPhone 13 Screen (20 items)
        for i in range(20):
            stock_item = StockItem(
                product_id=created_products[0].id,  # iPhone 13 Screen
                stock_type='in',
                quantity=1,
                purchase_price=5000,
                selling_price=7500,
                supplier_id=supplier.id,
                status='available',
                batch_number=f'BATCH-001-{i+1:03d}',
                location='Shelf A1',
                created_at=datetime.utcnow() - timedelta(hours=10)  # 10 hours ago
            )
            db.session.add(stock_item)
        
        # Add stock for Samsung Battery (5 items)
        for i in range(5):
            stock_item = StockItem(
                product_id=created_products[1].id,  # Samsung Battery
                stock_type='in',
                quantity=1,
                purchase_price=1500,
                selling_price=2500,
                supplier_id=supplier.id,
                status='available',
                batch_number=f'BATCH-002-{i+1:03d}',
                location='Shelf B2',
                created_at=datetime.utcnow() - timedelta(hours=8)
            )
            db.session.add(stock_item)
        
        # Add some stock out items
        for i in range(3):
            stock_item = StockItem(
                product_id=created_products[0].id,  # iPhone 13 Screen
                stock_type='out',
                quantity=1,
                purchase_price=5000,
                selling_price=7500,
                supplier_id=supplier.id,
                status='sold',
                notes='Sold to customer',
                created_at=datetime.utcnow() - timedelta(hours=5)
            )
            db.session.add(stock_item)
        
        # Add a recent stock in
        stock_item = StockItem(
            product_id=created_products[3].id,  # Phone Case
            stock_type='in',
            quantity=1,
            purchase_price=300,
            selling_price=800,
            supplier_id=supplier.id,
            status='available',
            batch_number='BATCH-RECENT',
            location='Shelf C3',
            created_at=datetime.utcnow() - timedelta(minutes=30)
        )
        db.session.add(stock_item)
        
        db.session.commit()
        
        flash('Test data created successfully! 8 products, 30 stock items added.', 'success')
        return redirect(url_for('inventory.inventory_dashboard'))
    
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating test data: {str(e)}', 'danger')
        return redirect(url_for('inventory.inventory_dashboard'))

@inventory_bp.route('/category-stats')
@login_required
@staff_required  # Changed from checking 'admin' or 'manager'
def category_stats():
    """API endpoint for category statistics"""
    from ...models import ProductCategory
    
    try:
        categories = ProductCategory.query.all()
        
        stats = []
        for category in categories:
            product_count = Product.query.filter_by(
                category_id=category.id,
                is_active=True
            ).count()
            
            if product_count > 0:
                # Calculate total stock value for this category
                category_products = Product.query.filter_by(
                    category_id=category.id,
                    is_active=True
                ).all()
                
                category_value = 0
                for product in category_products:
                    stock_count = StockItem.query.filter_by(
                        product_id=product.id,
                        status='available'
                    ).count()
                    category_value += stock_count * product.purchase_price
                
                stats.append({
                    'id': category.id,
                    'name': category.name,
                    'count': product_count,
                    'value': category_value,
                    'color': get_category_color(category.id)  # Generate consistent color
                })
        
        return jsonify({'success': True, 'categories': stats})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def get_category_color(category_id):
    """Generate a consistent color for each category"""
    colors = [
        '#FF6B6B', '#4ECDC4', '#FFD166', '#06D6A0', '#118AB2',
        '#EF476F', '#FFD166', '#06D6A0', '#073B4C', '#7209B7'
    ]
    return colors[category_id % len(colors)]