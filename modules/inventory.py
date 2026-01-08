from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from modules.models import (
    Product, ProductCategory, Supplier, StockItem, 
    PurchaseOrder, PurchaseOrderItem, User
)
from datetime import datetime
import random
import string

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/')
@login_required
def inventory_dashboard():
    # Get inventory summary
    total_products = Product.query.filter_by(is_active=True).count()
    
    # Calculate total stock value
    total_value = 0
    for product in Product.query.filter_by(is_active=True).all():
        # Use raw SQL to avoid column issues
        from sqlalchemy import text
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

@inventory_bp.route('/products')
@login_required
def product_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    query = Product.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    products = query.order_by(Product.name).paginate(page=page, per_page=per_page)
    categories = ProductCategory.query.all()
    
    # Get stock counts for each product
    for product in products.items:
        product.stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
    
    return render_template('inventory/products.html',
                         products=products,
                         categories=categories,
                         title='Products')

@inventory_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Get stock items
    stock_items = StockItem.query.filter_by(
        product_id=product_id
    ).order_by(StockItem.created_at.desc()).all()
    
    # Get stock history
    stock_history = StockItem.query.filter_by(
        product_id=product_id
    ).order_by(StockItem.created_at.desc()).limit(50).all()
    
    return render_template('inventory/product_detail.html',
                         product=product,
                         stock_items=stock_items,
                         stock_history=stock_history,
                         title=product.name)

@inventory_bp.route('/stock-in', methods=['GET', 'POST'])
@login_required
def stock_in():
    if request.method == 'POST':
        try:
            print("DEBUG: POST request received for stock-in")  # Debug
            print(f"DEBUG: Form data: {dict(request.form)}")  # Debug
            
            product_id = request.form.get('product_id', type=int)
            quantity = request.form.get('quantity', type=int, default=1)
            purchase_price = request.form.get('purchase_price', type=float)
            selling_price = request.form.get('selling_price', type=float)
            supplier_id = request.form.get('supplier_id', type=int)
            batch_number = request.form.get('batch_number', '')
            location = request.form.get('location', '')
            notes = request.form.get('notes', '')
            
            print(f"DEBUG: product_id={product_id}, quantity={quantity}, purchase_price={purchase_price}")  # Debug
            
            # Validation
            if not product_id:
                flash('Please select a product', 'danger')
                print("DEBUG: No product selected")  # Debug
                return redirect(url_for('inventory.stock_in'))
            
            if not purchase_price or purchase_price <= 0:
                flash('Please enter a valid purchase price', 'danger')
                print(f"DEBUG: Invalid purchase price: {purchase_price}")  # Debug
                return redirect(url_for('inventory.stock_in'))
            
            if not selling_price or selling_price <= 0:
                flash('Please enter a valid selling price', 'danger')
                print(f"DEBUG: Invalid selling price: {selling_price}")  # Debug
                return redirect(url_for('inventory.stock_in'))
            
            product = Product.query.get(product_id)
            if not product:
                flash('Product not found', 'danger')
                print(f"DEBUG: Product not found: {product_id}")  # Debug
                return redirect(url_for('inventory.stock_in'))
            
            print(f"DEBUG: Product found: {product.name}, has_imei={product.has_imei}")  # Debug
            
            # Check for IMEI validation if product requires it
            if product.has_imei:
                print("DEBUG: Product requires IMEI, validating...")  # Debug
                # Validate all IMEI numbers are provided
                for i in range(quantity):
                    imei = request.form.get(f'imei_{i}', '').strip()
                    print(f"DEBUG: IMEI {i}: {imei}")  # Debug
                    if not imei:
                        flash(f'IMEI #{i+1} is required for this product', 'danger')
                        print(f"DEBUG: Missing IMEI #{i}")  # Debug
                        return redirect(url_for('inventory.stock_in'))
                    
                    # Check for duplicate IMEI in database
                    existing = StockItem.query.filter_by(imei=imei).first()
                    if existing:
                        flash(f'IMEI {imei} already exists in database', 'danger')
                        print(f"DEBUG: Duplicate IMEI: {imei}")  # Debug
                        return redirect(url_for('inventory.stock_in'))
            
            print(f"DEBUG: Adding {quantity} stock items...")  # Debug
            
            # Add stock items
            for i in range(quantity):
                stock_item = StockItem(
                    product_id=product_id,
                    stock_type='in',
                    quantity=1,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    supplier_id=supplier_id if supplier_id else None,
                    batch_number=batch_number,
                    location=location,
                    status='available',
                    notes=notes
                )
                
                # Add IMEI if product has it
                if product.has_imei:
                    imei = request.form.get(f'imei_{i}', '').strip()
                    stock_item.imei = imei
                    print(f"DEBUG: Added IMEI {imei} to stock item")  # Debug
                
                db.session.add(stock_item)
            
            db.session.commit()
            print("DEBUG: Database commit successful")  # Debug
            flash(f'{quantity} items added to stock successfully', 'success')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error occurred: {str(e)}")  # Debug
            import traceback
            traceback.print_exc()  # Print full traceback
            flash(f'Error adding stock: {str(e)}', 'danger')
            return redirect(url_for('inventory.stock_in'))
    
    # GET request
    products = Product.query.filter_by(is_active=True).all()
    suppliers = Supplier.query.all()
    categories = ProductCategory.query.all()
    
    # Add stock count to each product for display
    for product in products:
        product.stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
    
    return render_template('inventory/stock_in.html',
                         products=products,
                         suppliers=suppliers,
                         categories=categories,
                         title='Stock In')

@inventory_bp.route('/stock-out', methods=['POST'])
@login_required
def stock_out():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', type=int, default=1)
    reason = request.form.get('reason', '')
    notes = request.form.get('notes', '')
    
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found', 'danger')
        return redirect(request.referrer)
    
    # Get available stock items
    available_items = StockItem.query.filter_by(
        product_id=product_id,
        status='available'
    ).limit(quantity).all()
    
    if len(available_items) < quantity:
        flash(f'Only {len(available_items)} items available', 'danger')
        return redirect(request.referrer)
    
    for item in available_items:
        item.status = 'sold' if reason == 'sale' else reason
        item.notes = notes
        item.stock_type = 'out'
    
    db.session.commit()
    flash(f'{quantity} items marked as {reason}', 'success')
    return redirect(request.referrer)

@inventory_bp.route('/suppliers')
@login_required
def supplier_list():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('inventory/suppliers.html',
                         suppliers=suppliers,
                         title='Suppliers')

@inventory_bp.route('/supplier/<int:supplier_id>')
@login_required
def supplier_detail(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Get purchase orders for this supplier
    purchase_orders = PurchaseOrder.query.filter_by(
        supplier_id=supplier_id
    ).order_by(PurchaseOrder.order_date.desc()).all()
    
    return render_template('inventory/supplier_detail.html',
                         supplier=supplier,
                         purchase_orders=purchase_orders,
                         title=supplier.name)

@inventory_bp.route('/purchase-orders')
@login_required
def purchase_order_list():
    status = request.args.get('status', 'all')
    
    query = PurchaseOrder.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    purchase_orders = query.order_by(PurchaseOrder.order_date.desc()).all()
    
    # Get all suppliers for the filter
    suppliers = Supplier.query.all()
    
    return render_template('inventory/purchase_orders.html',
                         purchase_orders=purchase_orders,
                         suppliers=suppliers,
                         status=status,
                         title='Purchase Orders')

@inventory_bp.route('/add-product', methods=['POST'])
@login_required
def add_product():
    try:
        name = request.form.get('name')
        sku = request.form.get('sku')
        category_id = request.form.get('category_id', type=int)
        purchase_price = request.form.get('purchase_price', type=float)
        selling_price = request.form.get('selling_price', type=float)
        
        # Check if SKU already exists
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product:
            flash(f'Product with SKU {sku} already exists', 'danger')
            return redirect(url_for('inventory.stock_in'))
        
        product = Product(
            sku=sku,
            name=name,
            category_id=category_id if category_id else None,
            purchase_price=purchase_price,
            selling_price=selling_price,
            min_stock_level=5,
            is_active=True
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash(f'Product {name} added successfully', 'success')
        return redirect(url_for('inventory.stock_in'))
    except Exception as e:
        flash(f'Error adding product: {str(e)}', 'danger')
        return redirect(url_for('inventory.stock_in'))

@inventory_bp.route('/create-purchase-order', methods=['GET', 'POST'])
@login_required
def create_purchase_order():
    try:
        print("DEBUG: Entering create_purchase_order route")  # Debug
        
        if request.method == 'POST':
            print("DEBUG: POST request received")  # Debug
            supplier_id = request.form.get('supplier_id', type=int)
            expected_date = request.form.get('expected_date')
            notes = request.form.get('notes', '')
            
            print(f"DEBUG: supplier_id={supplier_id}, expected_date={expected_date}")  # Debug
            
            # Generate PO number
            po_number = generate_po_number()
            
            purchase_order = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier_id,
                expected_date=datetime.strptime(expected_date, '%Y-%m-%d') if expected_date else None,
                notes=notes,
                created_by=current_user.id
            )
            
            db.session.add(purchase_order)
            db.session.flush()  # Get PO ID
            
            # Process items
            total_amount = 0
            item_count = int(request.form.get('item_count', 0))
            
            print(f"DEBUG: item_count={item_count}")  # Debug
            
            for i in range(item_count):
                product_id = request.form.get(f'items[{i}][product_id]', type=int)
                quantity = request.form.get(f'items[{i}][quantity]', type=int)
                unit_price = request.form.get(f'items[{i}][unit_price]', type=float)
                
                print(f"DEBUG: Item {i}: product_id={product_id}, quantity={quantity}, unit_price={unit_price}")  # Debug
                
                if product_id and quantity and unit_price:
                    item = PurchaseOrderItem(
                        purchase_order_id=purchase_order.id,
                        product_id=product_id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=quantity * unit_price
                    )
                    db.session.add(item)
                    total_amount += item.total_price
            
            purchase_order.total_amount = total_amount
            db.session.commit()
            
            flash(f'Purchase order {po_number} created successfully', 'success')
            return redirect(url_for('inventory.purchase_order_detail', po_id=purchase_order.id))
        
        print("DEBUG: GET request - rendering template")  # Debug
        suppliers = Supplier.query.all()
        products = Product.query.filter_by(is_active=True).all()
        
        print(f"DEBUG: Found {len(suppliers)} suppliers, {len(products)} products")  # Debug
        
        return render_template('inventory/create_purchase_order.html',
                             suppliers=suppliers,
                             products=products,
                             title='Create Purchase Order')
    except Exception as e:
        print(f"DEBUG: Error in create_purchase_order: {str(e)}")  # Debug
        import traceback
        traceback.print_exc()  # Print full traceback
        flash(f'Error creating purchase order: {str(e)}', 'danger')
        return redirect(url_for('inventory.purchase_order_list'))


@inventory_bp.route('/purchase-order/<int:po_id>')
@login_required
def purchase_order_detail(po_id):
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    return render_template('inventory/purchase_order_detail.html',
                         purchase_order=purchase_order,
                         title=f'PO {purchase_order.po_number}')

@inventory_bp.route('/receive-grn/<int:po_id>', methods=['GET', 'POST'])
@login_required
def receive_grn(po_id):
    purchase_order = PurchaseOrder.query.get_or_404(po_id)
    
    if request.method == 'POST':
        for item in purchase_order.po_items:
            received_qty = request.form.get(f'received_qty_{item.id}', type=int)
            
            if received_qty and received_qty > 0:
                item.received_quantity = received_qty
                
                # Create stock items
                for _ in range(received_qty):
                    stock_item = StockItem(
                        product_id=item.product_id,
                        stock_type='in',
                        quantity=1,
                        purchase_price=item.unit_price,
                        selling_price=item.product.selling_price,
                        supplier_id=purchase_order.supplier_id,
                        purchase_order_id=po_id,
                        status='available'
                    )
                    db.session.add(stock_item)
        
        # Update PO status
        all_received = all(item.received_quantity >= item.quantity for item in purchase_order.po_items)
        purchase_order.status = 'received' if all_received else 'partial'
        
        db.session.commit()
        flash('Goods received successfully', 'success')
        return redirect(url_for('inventory.purchase_order_detail', po_id=po_id))
    
    return render_template('inventory/receive_grn.html',
                         purchase_order=purchase_order,
                         title='Receive Goods')

def generate_po_number():
    """Generate unique purchase order number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=4))
    po_number = f'PO-{date_str}-{random_str}'
    
    # Check if exists
    while PurchaseOrder.query.filter_by(po_number=po_number).first():
        random_str = ''.join(random.choices(string.digits, k=4))
        po_number = f'PO-{date_str}-{random_str}'
    
    return po_number

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

# Supplier API endpoints
@inventory_bp.route('/api/suppliers/add', methods=['POST'])
@login_required
def api_add_supplier():
    try:
        data = request.get_json()
        
        supplier = Supplier(
            name=data['name'],
            contact_person=data.get('contact_person'),
            phone=data.get('phone'),
            email=data.get('email'),
            address=data.get('address'),
            gst_number=data.get('gst_number')
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        return jsonify({'success': True, 'supplier_id': supplier.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@inventory_bp.route('/api/suppliers/<int:supplier_id>')
@login_required
def api_get_supplier(supplier_id):
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        return jsonify({
            'success': True,
            'supplier': {
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'phone': supplier.phone,
                'email': supplier.email,
                'address': supplier.address,
                'gst_number': supplier.gst_number
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@inventory_bp.route('/api/suppliers/<int:supplier_id>/update', methods=['PUT'])
@login_required
def api_update_supplier(supplier_id):
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        data = request.get_json()
        
        supplier.name = data['name']
        supplier.contact_person = data.get('contact_person')
        supplier.phone = data.get('phone')
        supplier.email = data.get('email')
        supplier.address = data.get('address')
        supplier.gst_number = data.get('gst_number')
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@inventory_bp.route('/api/suppliers/<int:supplier_id>/delete', methods=['DELETE'])
@login_required
def api_delete_supplier(supplier_id):
    try:
        supplier = Supplier.query.get_or_404(supplier_id)
        
        # Check if supplier has purchase orders
        if supplier.purchase_orders:
            return jsonify({
                'success': False, 
                'message': 'Cannot delete supplier with existing purchase orders'
            })
        
        db.session.delete(supplier)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Additional routes for PO management
@inventory_bp.route('/po/<int:po_id>/update-status', methods=['POST'])
@login_required
def update_po_status(po_id):
    """Update purchase order status"""
    try:
        purchase_order = PurchaseOrder.query.get_or_404(po_id)
        new_status = request.form.get('status')
        
        valid_statuses = ['pending', 'approved', 'partial', 'received', 'cancelled']
        
        if new_status in valid_statuses:
            purchase_order.status = new_status
            db.session.commit()
            flash(f'PO status updated to {new_status}', 'success')
        else:
            flash('Invalid status', 'danger')
        
        return redirect(url_for('inventory.purchase_order_detail', po_id=po_id))
    except Exception as e:
        flash(f'Error updating PO status: {str(e)}', 'danger')
        return redirect(url_for('inventory.purchase_order_detail', po_id=po_id))

@inventory_bp.route('/api/products/search')
@login_required
def api_search_products():
    """API endpoint for product search in PO creation"""
    try:
        search = request.args.get('q', '')
        
        if not search:
            return jsonify({'success': True, 'products': []})
        
        products = Product.query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%')
            ),
            Product.is_active == True
        ).limit(10).all()
        
        product_list = []
        for product in products:
            # Get current stock
            stock_count = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            product_list.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'purchase_price': product.purchase_price,
                'selling_price': product.selling_price,
                'stock_count': stock_count,
                'min_stock_level': product.min_stock_level
            })
        
        return jsonify({'success': True, 'products': product_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Add a route to get all purchase orders for a specific product
@inventory_bp.route('/product/<int:product_id>/purchase-history')
@login_required
def product_purchase_history(product_id):
    """Show purchase history for a specific product"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get all PO items for this product
        po_items = PurchaseOrderItem.query.filter_by(
            product_id=product_id
        ).order_by(PurchaseOrderItem.id.desc()).all()
        
        return render_template('inventory/product_purchase_history.html',
                             product=product,
                             po_items=po_items,
                             title=f'Purchase History - {product.name}')
    except Exception as e:
        flash(f'Error loading purchase history: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

# Add test data creation route for debugging
@inventory_bp.route('/test/create-test-data')
@login_required
def create_test_data():
    """Create test data for inventory module"""
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
    
@inventory_bp.route('/product/<int:product_id>/info')
@login_required
def product_info(product_id):
    """Get product information for AJAX requests"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get current stock count
        stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'category_name': product.category.name if product.category else None,
                'stock_count': stock_count,
                'min_stock_level': product.min_stock_level,
                'has_imei': product.has_imei,
                'purchase_price': float(product.purchase_price),
                'selling_price': float(product.selling_price),
                'wholesale_price': float(product.wholesale_price)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500