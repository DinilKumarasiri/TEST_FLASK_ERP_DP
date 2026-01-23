from flask import render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from ... import db
from ...models import Customer, Product, StockItem, Invoice, InvoiceItem, Payment
from datetime import datetime
import random
import string
from . import pos_bp

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

@pos_bp.route('/scan-product', methods=['POST'])
@login_required
def scan_product():
    """Scan barcode and find product - IMPROVED VERSION"""
    data = request.get_json()
    barcode = data.get('barcode', '').strip()
    
    if not barcode:
        return jsonify({'success': False, 'message': 'No barcode provided'})
    
    print(f"DEBUG: Scanning barcode: {barcode}")
    
    # First, try to find by stock item barcode (item_barcode)
    stock_item = StockItem.query.filter_by(
        item_barcode=barcode,
        status='available'
    ).first()
    
    if stock_item:
        print(f"DEBUG: Found stock item with barcode: {barcode}")
        product = stock_item.product
        if product and product.is_active:
            # Calculate available stock
            available_stock = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            product_data = {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'selling_price': float(product.selling_price),
                'has_imei': product.has_imei,
                'stock_available': available_stock,
                'stock_item_id': stock_item.id,  # Include stock item ID
                'stock_item_barcode': stock_item.item_barcode,
                'is_specific_item': True,  # Flag that this is a specific stock item
                'message': 'Found specific stock item'
            }
            return jsonify({'success': True, 'product': product_data})
    
    # Try to find by product SKU
    product = Product.query.filter_by(sku=barcode, is_active=True).first()
    
    # Try to find by product barcode
    if not product:
        product = Product.query.filter_by(barcode=barcode, is_active=True).first()
    
    # Try to find by IMEI in stock items
    if not product:
        stock_item = StockItem.query.filter_by(imei=barcode, status='available').first()
        if stock_item:
            product = stock_item.product
            # This is also a specific stock item
            available_stock = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            product_data = {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'selling_price': float(product.selling_price),
                'has_imei': product.has_imei,
                'stock_available': available_stock,
                'stock_item_id': stock_item.id,
                'stock_item_barcode': stock_item.imei,
                'is_specific_item': True,
                'message': 'Found by IMEI'
            }
            return jsonify({'success': True, 'product': product_data})
    
    if not product:
        print(f"DEBUG: Product not found for barcode: {barcode}")
        return jsonify({'success': False, 'message': f'Product not found for "{barcode}"'})
    
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
        'stock_available': available_stock,
        'is_specific_item': False,  # Not a specific stock item
        'message': 'Found by product barcode/SKU'
    }
    
    return jsonify({'success': True, 'product': product_data})

@pos_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    """
    Add product to cart - handles both JSON and FormData
    """
    print("=" * 50)
    print("DEBUG: /pos/add-to-cart route called")
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            print("DEBUG: Processing as JSON request")
            data = request.get_json()
            product_id = data.get('product_id')
            quantity_str = data.get('quantity', '1')
            stock_item_id = data.get('stock_item_id')  # Handle specific stock item
        else:
            print("DEBUG: Processing as FormData request")
            data = request.form
            product_id = data.get('product_id')
            quantity_str = data.get('quantity', '1')
            stock_item_id = data.get('stock_item_id')  # Handle specific stock item
        
        # Convert quantity to int
        try:
            quantity = int(quantity_str)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid quantity value',
                'error_type': 'invalid_quantity'
            }), 400
        
        # Validate required fields
        if not product_id:
            return jsonify({
                'success': False,
                'message': 'Product ID is required',
                'error_type': 'missing_product_id'
            }), 400
        
        print(f"DEBUG: product_id={product_id}, quantity={quantity}, stock_item_id={stock_item_id}")
        
        # Check if product exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': 'Product not found',
                'error_type': 'product_not_found',
                'product_id': product_id
            }), 404
        
        print(f"DEBUG: Found product: {product.name} (ID: {product.id}, SKU: {product.sku})")
        
        # Check stock availability - MODIFIED to handle specific stock items
        if stock_item_id:
            # Check if specific stock item is available
            stock_item = StockItem.query.filter_by(
                id=stock_item_id,
                product_id=product.id,
                status='available'
            ).first()
            
            if not stock_item:
                return jsonify({
                    'success': False,
                    'message': f'Specific stock item not available',
                    'error_type': 'stock_item_unavailable',
                    'product_name': product.name
                }), 400
                
            available_stock = 1  # Specific item, only 1 available
        else:
            # Check general stock availability
            available_stock = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
        
        print(f"DEBUG: Available stock for {product.name}: {available_stock}")
        
        if available_stock <= 0:
            return jsonify({
                'success': False,
                'message': f'{product.name} is out of stock',
                'error_type': 'out_of_stock',
                'product_name': product.name
            }), 400
        
        if quantity > available_stock:
            return jsonify({
                'success': False,
                'message': f'Only {available_stock} items of {product.name} available',
                'error_type': 'insufficient_stock',
                'available_stock': available_stock,
                'requested_quantity': quantity,
                'product_name': product.name
            }), 400
        
        # Initialize cart if not exists
        if 'cart' not in session:
            print("DEBUG: Initializing new cart in session")
            session['cart'] = {}
        
        cart = session['cart']
        print(f"DEBUG: Current cart before update (items: {len(cart)}): {cart}")
        
        # Generate product key - include stock_item_id if specified
        if stock_item_id:
            product_key = f"item_{stock_item_id}"  # Unique key for specific item
        else:
            product_key = str(product_id)  # Regular product key
        
        # Check if product is already in cart
        if product_key in cart:
            # Update existing item
            current_quantity = cart[product_key]['quantity']
            new_quantity = current_quantity + quantity
            
            # Check if new quantity exceeds stock
            if new_quantity > available_stock:
                max_allowed = available_stock
                cart[product_key]['quantity'] = max_allowed
                print(f"DEBUG: Updated existing item quantity to max allowed: {max_allowed}")
            else:
                cart[product_key]['quantity'] = new_quantity
                print(f"DEBUG: Updated existing item quantity: {current_quantity} -> {new_quantity}")
                
        else:
            # Add new item to cart
            cart_item_data = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': float(product.selling_price),
                'purchase_price': float(product.purchase_price),
                'quantity': quantity,
                'has_imei': product.has_imei,
                'category_id': product.category_id,
                'stock_available': available_stock
            }
            
            # Add stock item info if specific item
            if stock_item_id:
                cart_item_data['stock_item_id'] = stock_item_id
                cart_item_data['stock_item_barcode'] = stock_item.item_barcode if stock_item else None
                cart_item_data['is_specific_item'] = True
            
            cart[product_key] = cart_item_data
            print(f"DEBUG: Added new item to cart: {product.name}")
        
        # Update session
        session['cart'] = cart
        session.modified = True
        
        print(f"DEBUG: Cart after update (items: {len(cart)}): {cart}")
        
        # Calculate cart totals
        item_count = sum(item['quantity'] for item in cart.values())
        subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
        tax = subtotal * 0.15
        total = subtotal + tax
        
        response_data = {
            'success': True,
            'cart': cart,
            'product_key': product_key,
            'cart_summary': {
                'item_count': item_count,
                'subtotal': subtotal,
                'tax': tax,
                'total': total,
                'tax_rate': 0.15
            },
            'product_added': {
                'id': product.id,
                'name': product.name,
                'quantity': quantity,
                'price': float(product.selling_price),
                'total_price': float(product.selling_price) * quantity,
                'stock_item_id': stock_item_id
            },
            'message': f'Added {quantity} × {product.name} to cart'
        }
        
        print(f"DEBUG: Sending successful response")
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"DEBUG: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred',
            'error_type': 'server_error',
            'error_details': str(e)
        }), 500

@pos_bp.route('/get-cart', methods=['GET'])
@login_required
def get_cart():
    """Get current cart contents"""
    print("DEBUG: /pos/get-cart route called")
    
    try:
        cart = session.get('cart', {})
        
        # Calculate totals
        item_count = sum(item.get('quantity', 0) for item in cart.values())
        subtotal = sum(item.get('price', 0) * item.get('quantity', 0) for item in cart.values())
        tax = subtotal * 0.15
        total = subtotal + tax
        
        response_data = {
            'success': True,
            'cart': cart,
            'cart_summary': {
                'item_count': item_count,
                'subtotal': subtotal,
                'tax': tax,
                'total': total,
                'tax_rate': 0.15
            }
        }
        
        print(f"DEBUG: Cart contains {item_count} items")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting cart: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'cart': {}
        }), 500

@pos_bp.route('/remove-from-cart/<string:product_key>', methods=['POST'])  # Changed from int to string
@login_required
def remove_from_cart(product_key):
    """Remove item from cart"""
    print(f"DEBUG: /pos/remove-from-cart/{product_key} route called")
    
    try:
        if 'cart' in session and product_key in session['cart']:
            # Get product name before removing (for response message)
            item = session['cart'][product_key]
            product_name = item.get('name', 'Product')
            
            # Remove item
            del session['cart'][product_key]
            session.modified = True
            
            print(f"DEBUG: Removed {product_name} from cart (key: {product_key})")
            
            return jsonify({
                'success': True, 
                'cart': session.get('cart', {}),
                'message': f'Removed {product_name} from cart'
            })
        else:
            return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
            
    except Exception as e:
        print(f"Error removing from cart: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@pos_bp.route('/update-cart', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity"""
    print("DEBUG: /pos/update-cart route called")
    
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        product_key = data.get('product_key')  # Changed from product_id
        quantity_str = data.get('quantity', '1')
        
        # Validate input
        if not product_key:
            return jsonify({'success': False, 'message': 'Product key is required'}), 400
        
        try:
            quantity = int(quantity_str)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid quantity value'}), 400
        
        if quantity < 0:
            return jsonify({'success': False, 'message': 'Quantity cannot be negative'}), 400
        
        # Check if cart exists and item exists
        if 'cart' not in session or product_key not in session['cart']:
            return jsonify({'success': False, 'message': 'Item not found in cart'}), 404
        
        item = session['cart'][product_key]
        
        # Check if this is a specific stock item or regular product
        if 'stock_item_id' in item:
            # Specific stock item - always quantity 1
            if quantity > 1:
                return jsonify({
                    'success': False,
                    'message': f'{item["name"]} is a specific serialized item, quantity must be 1'
                }), 400
            item['quantity'] = 1
        else:
            # Regular product - check stock availability
            product = Product.query.get(item['id'])
            if not product:
                return jsonify({'success': False, 'message': 'Product not found'}), 404
            
            # Check stock availability
            available_stock = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            # If quantity is 0, remove from cart
            if quantity == 0:
                del session['cart'][product_key]
                session.modified = True
                return jsonify({'success': True, 'cart': session.get('cart', {})})
            
            # Check if requested quantity exceeds available stock
            if quantity > available_stock:
                return jsonify({
                    'success': False, 
                    'message': f'Only {available_stock} items available',
                    'available_stock': available_stock
                }), 400
            
            item['quantity'] = quantity
        
        session.modified = True
        
        return jsonify({'success': True, 'cart': session['cart']})
        
    except Exception as e:
        print(f"Error updating cart: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@pos_bp.route('/clear-cart', methods=['POST'])
@login_required
def clear_cart():
    """Clear all items from cart"""
    print("DEBUG: /pos/clear-cart route called")
    
    try:
        if 'cart' in session:
            # Get cart info before clearing
            cart_items = len(session['cart'])
            
            # Clear cart
            session.pop('cart')
            session.modified = True
            
            print(f"DEBUG: Cleared {cart_items} items from cart")
            
            return jsonify({
                'success': True,
                'message': f'Cleared {cart_items} items from cart',
                'cart': {}
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Cart was already empty',
                'cart': {}
            })
            
    except Exception as e:
        print(f"Error clearing cart: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@pos_bp.route('/find-customer', methods=['POST'])
@login_required
def find_customer():
    """Find customer by phone"""
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
    """Create new customer"""
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
    """Process checkout and create invoice"""
    print("=" * 50)
    print("DEBUG: /pos/checkout route called")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Content-Type: {request.content_type}")
    print(f"DEBUG: Current user: {current_user.username}")
    
    try:
        # Check if request is JSON
        if not request.is_json:
            print("DEBUG: Request is not JSON")
            print(f"DEBUG: Content-Type header: {request.content_type}")
            return jsonify({
                'success': False, 
                'message': 'Request must be JSON',
                'error': 'Content-Type must be application/json'
            }), 415
        
        data = request.get_json()
        print(f"DEBUG: Received data: {data}")
        
        cart = session.get('cart', {})
        if not cart:
            print("DEBUG: Cart is empty")
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        customer_id = data.get('customer_id')
        customer_name = data.get('customer_name', '')
        customer_phone = data.get('customer_phone', '')
        payment_method = data.get('payment_method', 'cash')
        discount = float(data.get('discount', 0))
        tax_rate = float(data.get('tax_rate', 0.15))
        notes = data.get('notes', '')
        payment_reference = data.get('payment_reference', '')
        
        print(f"DEBUG: Customer Name: {customer_name}")
        print(f"DEBUG: Payment Method: {payment_method}")
        print(f"DEBUG: Discount: {discount}")
        
        # Calculate totals
        subtotal = 0
        for item in cart.values():
            subtotal += item['price'] * item['quantity']
        
        tax = subtotal * tax_rate
        total = subtotal + tax - discount
        
        print(f"DEBUG: Subtotal: {subtotal}, Tax: {tax}, Total: {total}")
        
        # Generate invoice number
        invoice_number = generate_invoice_number()
        print(f"DEBUG: Generated invoice number: {invoice_number}")
        
        # Start transaction
        try:
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_id=customer_id if customer_id else None,
                customer_name=customer_name or 'Walk-in Customer',
                customer_phone=customer_phone,
                subtotal=subtotal,
                discount=discount,
                tax=tax,
                total=total,
                payment_status='paid' if payment_method != 'due' else 'pending',
                payment_method=payment_method,
                notes=notes,
                created_by=current_user.id
            )
            
            print(f"DEBUG: Created invoice object: {invoice}")
            
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID
            
            print(f"DEBUG: Invoice ID: {invoice.id}")
            
            # Process each item in cart
            for product_id, item in cart.items():
                product = Product.query.get(item['id'])
                print(f"DEBUG: Processing product: {product.name}, Quantity: {item['quantity']}")
                
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
                            print(f"DEBUG: Marked stock item {stock_item.id} as sold")
                    else:
                        # For non-IMEI products, create a stock record
                        stock_item = StockItem(
                            product_id=product.id,
                            status='sold',
                            notes=f"Sold in invoice {invoice_number}"
                        )
                        db.session.add(stock_item)
                        db.session.flush()
                        print(f"DEBUG: Created stock record for non-IMEI product")
                    
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
                    print(f"DEBUG: Created invoice item for {product.name}")
            
            # Create payment record
            if payment_method != 'due':
                payment = Payment(
                    invoice_id=invoice.id,
                    amount=total,
                    payment_method=payment_method,
                    received_by=current_user.id,
                    reference_number=payment_reference,
                    notes=f"POS sale - {invoice_number}"
                )
                db.session.add(payment)
                print(f"DEBUG: Created payment record")
            
            db.session.commit()
            print(f"DEBUG: Database commit successful")
            
            # Clear cart
            session.pop('cart', None)
            session.modified = True
            
            print(f"DEBUG: Cleared cart from session")
            
            return jsonify({
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice_number,
                'total': total,
                'message': f'Sale completed successfully! Invoice #{invoice_number}'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Database error: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'message': f'Error processing sale: {str(e)}'
            }), 500
            
    except Exception as e:
        print(f"DEBUG: General error in checkout: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error in checkout process: {str(e)}'
        }), 500

@pos_bp.route('/checkout-form')
@login_required
def checkout_form():
    """Return checkout form HTML"""
    return render_template('pos/checkout_modal.html')

@pos_bp.route('/daily-sales')
@login_required
def daily_sales():
    """Daily sales report"""
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
