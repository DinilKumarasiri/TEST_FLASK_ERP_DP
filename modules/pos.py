from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from modules.models import (
    Customer, Product, StockItem, Invoice, InvoiceItem, Payment, 
    User, ProductCategory
)
from datetime import datetime
import random
import string

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/')
@login_required
def pos_home():
    # Clear any existing cart in session
    if 'cart' in session:
        session.pop('cart')
    
    categories = ProductCategory.query.all()
    products = Product.query.filter_by(is_active=True).all()
    
    return render_template('pos/pos.html', 
                         categories=categories,
                         products=products,
                         title='POS Terminal')

@pos_bp.route('/dashboard')
@login_required
def dashboard():
    # Get today's sales summary
    today = datetime.utcnow().date()
    
    today_invoices = Invoice.query.filter(
        db.func.date(Invoice.date) == today
    ).all()
    
    today_sales = sum(inv.total for inv in today_invoices)
    today_transactions = len(today_invoices)
    today_cash = sum(inv.total for inv in today_invoices if inv.payment_method == 'cash')
    
    # Get low stock products
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
    
    # Get recent transactions
    recent_invoices = Invoice.query.order_by(
        Invoice.date.desc()
    ).limit(10).all()
    
    return render_template('pos/dashboard.html',
                         now=datetime.utcnow(),
                         today_sales=today_sales,
                         today_transactions=today_transactions,
                         today_cash=today_cash,
                         low_stock_products=low_stock_products,
                         recent_invoices=recent_invoices,
                         title='Dashboard')

@pos_bp.route('/scan-product', methods=['POST'])
@login_required
def scan_product():
    data = request.get_json()
    barcode = data.get('barcode', '').strip()
    
    if not barcode:
        return jsonify({'success': False, 'message': 'No barcode provided'})
    
    # Try to find by SKU
    product = Product.query.filter_by(sku=barcode).first()
    
    # If not found by SKU, try by IMEI in stock items
    if not product:
        stock_item = StockItem.query.filter_by(imei=barcode, status='available').first()
        if stock_item:
            product = stock_item.product
    
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})
    
    # Check stock availability
    available_stock = StockItem.query.filter_by(
        product_id=product.id,
        status='available'
    ).count()
    
    if available_stock <= 0:
        return jsonify({'success': False, 'message': 'Out of stock'})
    
    product_data = {
        'id': product.id,
        'sku': product.sku,
        'name': product.name,
        'selling_price': float(product.selling_price),
        'has_imei': product.has_imei,
        'stock_available': available_stock
    }
    
    return jsonify({'success': True, 'product': product_data})

@pos_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})
    
    # Check stock
    available_stock = StockItem.query.filter_by(
        product_id=product.id,
        status='available'
    ).count()
    
    if quantity > available_stock:
        return jsonify({'success': False, 'message': f'Only {available_stock} items available'})
    
    # Initialize cart if not exists
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    
    # Add or update item in cart
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'quantity': quantity,
            'has_imei': product.has_imei
        }
    
    session['cart'] = cart
    session.modified = True
    
    return jsonify({'success': True, 'cart': cart})

@pos_bp.route('/remove-from-cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    if 'cart' in session and str(product_id) in session['cart']:
        del session['cart'][str(product_id)]
        session.modified = True
    
    return jsonify({'success': True})

@pos_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))
    
    if 'cart' in session and str(product_id) in session['cart']:
        product = Product.query.get(product_id)
        
        # Check stock
        available_stock = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
        
        if quantity <= available_stock:
            session['cart'][str(product_id)]['quantity'] = quantity
            session.modified = True
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': f'Only {available_stock} items available'})
    
    return jsonify({'success': False, 'message': 'Item not found in cart'})

@pos_bp.route('/get-cart', methods=['GET'])
@login_required
def get_cart():
    cart = session.get('cart', {})
    return jsonify({'cart': cart})

@pos_bp.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    if 'cart' in session:
        session.pop('cart')
    return jsonify({'success': True})

@pos_bp.route('/find-customer', methods=['POST'])
@login_required
def find_customer():
    phone = request.json.get('phone', '').strip()
    
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number required'})
    
    customer = Customer.query.filter_by(phone=phone).first()
    
    if customer:
        customer_data = {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email,
            'address': customer.address
        }
        return jsonify({'success': True, 'customer': customer_data})
    
    return jsonify({'success': False, 'message': 'Customer not found'})

@pos_bp.route('/create-customer', methods=['POST'])
@login_required
def create_customer():
    data = request.get_json()
    
    # Check if customer with same phone exists
    existing_customer = Customer.query.filter_by(phone=data['phone']).first()
    if existing_customer:
        return jsonify({'success': False, 'message': 'Customer with this phone already exists'})
    
    customer = Customer(
        name=data['name'],
        phone=data['phone'],
        email=data.get('email', ''),
        address=data.get('address', '')
    )
    
    db.session.add(customer)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'customer': {
            'id': customer.id,
            'name': customer.name,
            'phone': customer.phone
        }
    })

@pos_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    data = request.get_json()
    
    cart = session.get('cart', {})
    if not cart:
        return jsonify({'success': False, 'message': 'Cart is empty'})
    
    customer_id = data.get('customer_id')
    payment_method = data.get('payment_method', 'cash')
    discount = float(data.get('discount', 0))
    tax_rate = float(data.get('tax_rate', 0.15))
    notes = data.get('notes', '')
    
    # Calculate totals
    subtotal = 0
    for item in cart.values():
        subtotal += item['price'] * item['quantity']
    
    tax = subtotal * tax_rate
    total = subtotal + tax - discount
    
    # Generate invoice number
    invoice_number = generate_invoice_number()
    
    # Create invoice
    invoice = Invoice(
        invoice_number=invoice_number,
        customer_id=customer_id,
        customer_name=data.get('customer_name', 'Walk-in Customer'),
        customer_phone=data.get('customer_phone', ''),
        subtotal=subtotal,
        discount=discount,
        tax=tax,
        total=total,
        payment_status='paid' if payment_method != 'due' else 'pending',
        payment_method=payment_method,
        notes=notes,
        created_by=current_user.id
    )
    
    db.session.add(invoice)
    db.session.flush()  # Get invoice ID
    
    # Process each item in cart
    for product_id, item in cart.items():
        product = Product.query.get(item['id'])
        
        for _ in range(item['quantity']):
            # Find available stock item
            stock_item = None
            if product.has_imei:
                # For products with IMEI, need to assign specific stock item
                stock_item = StockItem.query.filter_by(
                    product_id=product.id,
                    status='available'
                ).first()
                
                if stock_item:
                    stock_item.status = 'sold'
            else:
                # For non-IMEI products, just reduce stock
                pass
            
            # Create invoice item
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                stock_item_id=stock_item.id if stock_item else None,
                quantity=1,
                unit_price=item['price'],
                total=item['price']
            )
            
            db.session.add(invoice_item)
    
    # Create payment record
    if payment_method != 'due':
        payment = Payment(
            invoice_id=invoice.id,
            amount=total,
            payment_method=payment_method,
            received_by=current_user.id
        )
        db.session.add(payment)
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    return jsonify({
        'success': True,
        'invoice_id': invoice.id,
        'invoice_number': invoice_number,
        'total': total
    })

def generate_invoice_number():
    """Generate unique invoice number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=4))
    invoice_number = f'INV-{date_str}-{random_str}'
    
    # Check if exists
    while Invoice.query.filter_by(invoice_number=invoice_number).first():
        random_str = ''.join(random.choices(string.digits, k=4))
        invoice_number = f'INV-{date_str}-{random_str}'
    
    return invoice_number

@pos_bp.route('/daily-sales')
@login_required
def daily_sales():
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        date = datetime.now().date()
    
    # Get sales for the date
    invoices = Invoice.query.filter(
        db.func.date(Invoice.date) == date
    ).order_by(Invoice.date.desc()).all()
    
    # Calculate summary
    total_sales = sum(inv.total for inv in invoices)
    total_discount = sum(inv.discount for inv in invoices)
    total_tax = sum(inv.tax for inv in invoices)
    
    # Payment method breakdown
    payment_methods = {}
    for inv in invoices:
        if inv.payment_method:
            payment_methods[inv.payment_method] = payment_methods.get(inv.payment_method, 0) + inv.total
    
    return render_template('pos/daily_sales.html',
                         date=date,
                         invoices=invoices,
                         total_sales=total_sales,
                         total_discount=total_discount,
                         total_tax=total_tax,
                         payment_methods=payment_methods,
                         title='Daily Sales')

@pos_bp.route('/invoices')
@login_required
def invoices_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    invoices = Invoice.query.order_by(
        Invoice.date.desc()
    ).paginate(page=page, per_page=per_page)
    
    return render_template('pos/invoices.html',
                         invoices=invoices,
                         title='Invoices')

@pos_bp.route('/invoice/<int:invoice_id>')
@login_required
def invoice_details(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('pos/invoice_detail.html',
                         invoice=invoice,
                         title=f'Invoice {invoice.invoice_number}')

@pos_bp.route('/test/create-invoice')
@login_required
def create_test_invoice():
    """Create a test invoice for debugging"""
    try:
        # Check if we have a customer
        customer = Customer.query.first()
        if not customer:
            # Create a test customer
            customer = Customer(
                name='Test Customer',
                phone='1234567890',
                email='test@example.com'
            )
            db.session.add(customer)
            db.session.flush()
        
        # Generate invoice number
        invoice_number = generate_invoice_number()
        
        # Create test invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=customer.id,
            customer_name=customer.name,
            customer_phone=customer.phone,
            subtotal=1000.00,
            tax=150.00,
            total=1150.00,
            payment_status='paid',
            payment_method='cash',
            created_by=current_user.id
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Add some test items
        products = Product.query.limit(3).all()
        for i, product in enumerate(products):
            item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                quantity=1,
                unit_price=product.selling_price,
                total=product.selling_price
            )
            db.session.add(item)
        
        # Add payment record
        payment = Payment(
            invoice_id=invoice.id,
            amount=1150.00,
            payment_method='cash',
            received_by=current_user.id
        )
        db.session.add(payment)
        
        db.session.commit()
        
        flash(f'Test invoice created: {invoice_number} (ID: {invoice.id})', 'success')
        return redirect(url_for('pos.invoice_details', invoice_id=invoice.id))
    except Exception as e:
        flash(f'Error creating test invoice: {str(e)}', 'danger')
        return redirect(url_for('pos.dashboard'))

@pos_bp.route('/add-payment/<int:invoice_id>', methods=['POST'])
@login_required
def add_payment(invoice_id):
    try:
        data = request.get_json()
        invoice = Invoice.query.get_or_404(invoice_id)
        
        amount = data.get('amount', 0)
        method = data.get('method', 'cash')
        reference = data.get('reference', '')
        
        # Create payment
        payment = Payment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=method,
            reference_number=reference,
            received_by=current_user.id
        )
        
        db.session.add(payment)
        
        # Update invoice status
        if amount >= invoice.total:
            invoice.payment_status = 'paid'
        elif amount > 0:
            invoice.payment_status = 'partial'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Payment added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})