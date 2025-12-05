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
        stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        total_value += stock_count * product.purchase_price
    
    # Low stock products
    low_stock_products = []
    for product in Product.query.filter_by(is_active=True).all():
        stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        
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
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int, default=1)
        purchase_price = request.form.get('purchase_price', type=float)
        selling_price = request.form.get('selling_price', type=float)
        supplier_id = request.form.get('supplier_id', type=int)
        batch_number = request.form.get('batch_number', '')
        location = request.form.get('location', '')
        notes = request.form.get('notes', '')
        
        product = Product.query.get(product_id)
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('inventory.stock_in'))
        
        for i in range(quantity):
            stock_item = StockItem(
                product_id=product_id,
                stock_type='in',
                quantity=1,
                purchase_price=purchase_price,
                selling_price=selling_price or product.selling_price,
                supplier_id=supplier_id if supplier_id else None,
                batch_number=batch_number,
                location=location,
                status='available',
                notes=notes
            )
            
            # If product has IMEI, get from form array
            if product.has_imei:
                imei_field = f'imei_{i}'
                if imei_field in request.form:
                    stock_item.imei = request.form[imei_field]
            
            db.session.add(stock_item)
        
        db.session.commit()
        flash(f'{quantity} items added to stock', 'success')
        return redirect(url_for('inventory.product_detail', product_id=product_id))
    
    products = Product.query.filter_by(is_active=True).all()
    suppliers = Supplier.query.all()
    
    return render_template('inventory/stock_in.html',
                         products=products,
                         suppliers=suppliers,
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
    
    return render_template('inventory/purchase_orders.html',
                         purchase_orders=purchase_orders,
                         status=status,
                         title='Purchase Orders')

@inventory_bp.route('/create-purchase-order', methods=['GET', 'POST'])
@login_required
def create_purchase_order():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id', type=int)
        expected_date = request.form.get('expected_date')
        notes = request.form.get('notes', '')
        
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
        
        for i in range(item_count):
            product_id = request.form.get(f'items[{i}][product_id]', type=int)
            quantity = request.form.get(f'items[{i}][quantity]', type=int)
            unit_price = request.form.get(f'items[{i}][unit_price]', type=float)
            
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
    
    suppliers = Supplier.query.all()
    products = Product.query.filter_by(is_active=True).all()
    
    return render_template('inventory/create_purchase_order.html',
                         suppliers=suppliers,
                         products=products,
                         title='Create Purchase Order')

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