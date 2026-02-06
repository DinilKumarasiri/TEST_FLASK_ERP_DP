from flask import render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from ... import db
from ...models import Customer, Product, StockItem, Invoice, InvoiceItem, Payment
from datetime import datetime
import random
import string
from . import pos_bp
from ...utils.permissions import staff_required

def generate_invoice_number():
    last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()

    if last_invoice and last_invoice.invoice_number:
        # Extract number from INV-000001
        last_number = int(last_invoice.invoice_number.split('-')[1])
        next_number = last_number + 1
    else:
        next_number = 1

    invoice_number = f"INV-{next_number:06d}"
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
    
    # FIRST: Look for stock item by barcode (item_barcode or IMEI)
    stock_item = StockItem.query.filter(
        (StockItem.item_barcode == barcode) | (StockItem.imei == barcode),
        StockItem.status == 'available'
    ).first()
    
    if stock_item:
        print(f"DEBUG: Found SPECIFIC stock item: {stock_item.id}, Product: {stock_item.product.name if stock_item.product else 'Unknown'}")
        
        product = stock_item.product
        if not product or not product.is_active:
            return jsonify({'success': False, 'message': 'Product not active'})
        
        # Check if this specific item is already in cart
        cart = session.get('cart', {})
        for key, item in cart.items():
            if item.get('stock_item_id') == stock_item.id:
                return jsonify({
                    'success': False,
                    'message': f'This specific {product.name} (Barcode: {barcode}) is already in your cart'
                })
        
        # Calculate available stock for this product
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
            'stock_item_id': stock_item.id,  # CRITICAL: Include stock item ID
            'stock_item_barcode': stock_item.item_barcode or stock_item.imei,
            'imei': stock_item.imei,
            'is_specific_item': True,  # Flag that this is a specific stock item
            'message': f'Found specific item: {stock_item.item_barcode or stock_item.imei}'
        }
        return jsonify({'success': True, 'product': product_data})
    
    # If no specific stock item found, try product SKU/barcode
    product = Product.query.filter(
        (Product.sku == barcode) | (Product.barcode == barcode),
        Product.is_active == True
    ).first()
    
    if product:
        print(f"DEBUG: Found product by SKU/barcode: {product.name}")
        
        # For serialized products, require scanning each item
        if product.has_imei:
            return jsonify({
                'success': False,
                'message': f'{product.name} requires serialization. Please scan each item\'s barcode/IMEI individually.'
            })
        
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
            'is_specific_item': False,
            'message': 'Found by product barcode/SKU'
        }
        return jsonify({'success': True, 'product': product_data})
    
    return jsonify({'success': False, 'message': f'Product not found for "{barcode}"'})

@pos_bp.route('/add-to-cart', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart - FIXED DUPLICATE ITEM ISSUE"""
    print("=" * 50)
    print("DEBUG: /pos/add-to-cart - FIXED DUPLICATE ITEM ISSUE")
    
    try:
        # Get request data
        if request.is_json:
            data = request.get_json()
            product_id = data.get('product_id')
            quantity_str = data.get('quantity', '1')
            stock_item_id = data.get('stock_item_id')
        else:
            data = request.form
            product_id = data.get('product_id')
            quantity_str = data.get('quantity', '1')
            stock_item_id = data.get('stock_item_id')
        
        # Convert quantity
        try:
            quantity = int(quantity_str)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid quantity value'
            }), 400
        
        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'Quantity must be at least 1'
            }), 400
        
        print(f"DEBUG: product_id={product_id}, quantity={quantity}, stock_item_id={stock_item_id}")
        
        # Validate product exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': 'Product not found'
            }), 404
        
        print(f"DEBUG: Product: {product.name} (ID: {product.id}), Has IMEI: {product.has_imei}")
        
        # Initialize cart if needed
        if 'cart' not in session:
            session['cart'] = {}
        
        cart = session['cart']
        
        # ========== HANDLE SPECIFIC STOCK ITEM ==========
        if stock_item_id:
            # Get the specific stock item
            stock_item = StockItem.query.get(stock_item_id)
            if not stock_item:
                return jsonify({
                    'success': False,
                    'message': 'Stock item not found'
                }), 404
            
            # Validate stock item belongs to the product
            if stock_item.product_id != product.id:
                return jsonify({
                    'success': False,
                    'message': f'Stock item does not belong to {product.name}'
                }), 400
            
            # Check if stock item is available
            if stock_item.status != 'available':
                return jsonify({
                    'success': False,
                    'message': f'This {product.name} item is not available (status: {stock_item.status})'
                }), 400
            
            # ========== FIXED: Check if this specific stock item is already in cart ==========
            # Look through all cart items to find if this stock_item_id already exists
            stock_item_already_in_cart = False
            for key, item in cart.items():
                if item.get('stock_item_id') == stock_item_id:
                    stock_item_already_in_cart = True
                    break
            
            if stock_item_already_in_cart:
                return jsonify({
                    'success': False,
                    'message': f'This specific {product.name} (Barcode: {stock_item.item_barcode or stock_item.imei}) is already in your cart'
                }), 400
            
            # Also check by barcode (in case barcode was added differently)
            barcode = stock_item.item_barcode or stock_item.imei
            if barcode:
                for key, item in cart.items():
                    if item.get('barcodes') and barcode in item.get('barcodes', []):
                        return jsonify({
                            'success': False,
                            'message': f'This specific {product.name} (Barcode: {barcode}) is already in your cart'
                        }), 400
            
            # Get barcode/IMEI for this item
            barcode = barcode or f"STOCK-{stock_item_id}"
            
            # Create unique key for this specific item
            item_key = f"stock_{stock_item_id}"
            
            cart_item_data = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': float(product.selling_price),
                'purchase_price': float(product.purchase_price) if product.purchase_price else 0.0,
                'quantity': 1,  # Always 1 for specific items
                'has_imei': product.has_imei,
                'stock_item_id': stock_item_id,
                'stock_item_barcode': stock_item.item_barcode,
                'imei': stock_item.imei,
                'barcodes': [barcode],
                'is_specific_item': True
            }
            
            cart[item_key] = cart_item_data
            print(f"DEBUG: Added specific stock item {stock_item_id} ({barcode}) to cart")
            
        # ========== HANDLE REGULAR PRODUCT (NON-SERIALIZED) ==========
        else:
            # For serialized products, you must scan each item individually
            if product.has_imei:
                return jsonify({
                    'success': False,
                    'message': f'{product.name} requires serialization. Please scan each item individually.'
                }), 400
            
            # Check available stock
            available_stock = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            if available_stock <= 0:
                return jsonify({
                    'success': False,
                    'message': f'{product.name} is out of stock'
                }), 400
            
            # Check how many are already in cart
            already_in_cart = 0
            for key, item in cart.items():
                if item.get('id') == product.id and not item.get('is_specific_item'):
                    already_in_cart += item.get('quantity', 0)
            
            print(f"DEBUG: Available stock: {available_stock}, Already in cart: {already_in_cart}")
            
            # Check if we have enough stock
            if already_in_cart + quantity > available_stock:
                remaining = available_stock - already_in_cart
                return jsonify({
                    'success': False,
                    'message': f'Only {remaining} more {product.name} available (you already have {already_in_cart} in cart)'
                }), 400
            
            # Get barcodes for these items
            barcodes = []
            # Get stock items that are NOT already in cart
            all_stock_items = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).all()
            
            # Get barcodes of items already in cart
            barcodes_in_cart = []
            for key, item in cart.items():
                if item.get('id') == product.id and not item.get('is_specific_item'):
                    barcodes_in_cart.extend(item.get('barcodes', []))
            
            # Filter out items already in cart
            available_items = []
            for stock_item in all_stock_items:
                stock_barcode = stock_item.item_barcode or stock_item.imei or f"PROD-{product.id}-{stock_item.id}"
                if stock_barcode not in barcodes_in_cart:
                    available_items.append(stock_item)
                    if len(available_items) >= quantity:
                        break
            
            if len(available_items) < quantity:
                return jsonify({
                    'success': False,
                    'message': f'Not enough unique items available for {product.name}'
                }), 400
            
            # Get barcodes from available items
            for stock_item in available_items:
                barcode = stock_item.item_barcode or stock_item.imei or f"PROD-{product.id}-{stock_item.id}"
                barcodes.append(barcode)
            
            # Create or update cart item
            product_key = f"product_{product_id}"
            
            if product_key in cart:
                # Update existing item
                cart[product_key]['quantity'] += quantity
                cart[product_key]['barcodes'].extend(barcodes)
                print(f"DEBUG: Updated {product.name} quantity to {cart[product_key]['quantity']}")
            else:
                # Add new item
                cart_item_data = {
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'price': float(product.selling_price),
                    'purchase_price': float(product.purchase_price) if product.purchase_price else 0.0,
                    'quantity': quantity,
                    'has_imei': product.has_imei,
                    'barcodes': barcodes,
                    'is_specific_item': False
                }
                
                cart[product_key] = cart_item_data
                print(f"DEBUG: Added {product.name} to cart with quantity {quantity}")
        
        # Update session
        session['cart'] = cart
        session.modified = True
        
        # Calculate cart totals
        item_count = sum(item['quantity'] for item in cart.values())
        subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
        tax = subtotal * 0.15
        total = subtotal + tax
        
        # Prepare response
        response_data = {
            'success': True,
            'cart': cart,
            'cart_summary': {
                'item_count': item_count,
                'subtotal': subtotal,
                'tax': tax,
                'total': total
            },
            'message': f'Added to cart successfully'
        }
        
        print(f"DEBUG: Cart now has {item_count} items, total: Rs.{total:.2f}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"ERROR in add_to_cart: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error adding to cart: {str(e)}'
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

@pos_bp.route('/remove-from-cart/<string:product_key>', methods=['POST'])
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
        
        product_key = data.get('product_key')
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
        
        # Check if this is a specific stock item
        if item.get('is_specific_item') or item.get('stock_item_id'):
            # Specific stock item - always quantity 1
            if quantity != 1:
                return jsonify({
                    'success': False,
                    'message': f'{item["name"]} is a specific serialized item, quantity must be 1'
                }), 400
            item['quantity'] = 1
        else:
            # Regular product
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
    data = request.get_json()
    phone = data.get('phone', '').strip()
    
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
    """Process checkout and create invoice - COMPLETE FIXED VERSION"""
    print("=" * 50)
    print("DEBUG: /pos/checkout - COMPLETE FIXED VERSION")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Content-Type: {request.content_type}")
    
    try:
        # Check if request is JSON
        if not request.is_json:
            print("DEBUG: Request is not JSON")
            return jsonify({
                'success': False, 
                'message': 'Request must be JSON',
                'error': 'Content-Type must be application/json'
            }), 415
        
        data = request.get_json()
        print(f"DEBUG: Received checkout data")
        
        # Get cart from session
        cart = session.get('cart', {})
        if not cart:
            print("DEBUG: Cart is empty")
            return jsonify({'success': False, 'message': 'Cart is empty'}), 400
        
        print(f"DEBUG: Cart has {len(cart)} items")
        
        # Get checkout data
        customer_id = data.get('customer_id')
        customer_name = data.get('customer_name', '').strip() or 'Walk-in Customer'
        customer_phone = data.get('customer_phone', '').strip()
        payment_method = data.get('payment_method', 'cash')
        discount = float(data.get('discount', 0))
        tax_rate = float(data.get('tax_rate', 0.15))
        notes = data.get('notes', '').strip()
        payment_reference = data.get('payment_reference', '').strip()
        
        print(f"DEBUG: Customer: {customer_name}, Payment: {payment_method}, Discount: {discount}")
        
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
        
        # Start database transaction
        try:
            # ========== VALIDATE STOCK AVAILABILITY ==========
            print("DEBUG: Validating stock availability...")
            stock_issues = []
            stock_items_to_sell = []
            
            for product_key, item in cart.items():
                product = Product.query.get(item['id'])
                if not product:
                    stock_issues.append(f"Product {item['id']} not found")
                    continue
                
                # Handle specific stock items
                if item.get('is_specific_item') and item.get('stock_item_id'):
                    stock_item_id = item['stock_item_id']
                    stock_item = StockItem.query.get(stock_item_id)
                    
                    if not stock_item:
                        stock_issues.append(f"Stock item {stock_item_id} not found for {product.name}")
                    elif stock_item.status != 'available':
                        stock_issues.append(f"Stock item {stock_item_id} ({product.name}) is not available (status: {stock_item.status})")
                    elif stock_item.product_id != product.id:
                        stock_issues.append(f"Stock item {stock_item_id} does not belong to product {product.name}")
                    else:
                        stock_items_to_sell.append(stock_item)
                
                # Handle non-specific items
                else:
                    # Check total available stock
                    available_stock = StockItem.query.filter_by(
                        product_id=product.id,
                        status='available'
                    ).count()
                    
                    if available_stock < item['quantity']:
                        stock_issues.append(f"Insufficient stock for {product.name}. Need {item['quantity']}, have {available_stock}")
                    else:
                        # Get available stock items
                        stock_items = StockItem.query.filter_by(
                            product_id=product.id,
                            status='available'
                        ).limit(item['quantity']).all()
                        
                        if len(stock_items) < item['quantity']:
                            stock_issues.append(f"Not enough stock items for {product.name}. Need {item['quantity']}, found {len(stock_items)}")
                        else:
                            stock_items_to_sell.extend(stock_items)
            
            if stock_issues:
                print(f"DEBUG: Stock validation failed: {stock_issues}")
                return jsonify({
                    'success': False,
                    'message': 'Stock validation failed',
                    'errors': stock_issues,
                    'error_type': 'stock_validation'
                }), 400
            
            # ========== CREATE INVOICE ==========
            print("DEBUG: Creating invoice...")
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_id=customer_id if customer_id else None,
                customer_name=customer_name,
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
            
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID
            print(f"DEBUG: Created invoice with ID: {invoice.id}")
            
            # ========== PROCESS CART ITEMS AND UPDATE STOCK ==========
            print("DEBUG: Processing cart items...")
            
            for product_key, item in cart.items():
                product = Product.query.get(item['id'])
                if not product:
                    continue
                
                print(f"DEBUG: Processing {product.name}, Quantity: {item['quantity']}")
                
                # Handle specific stock items
                if item.get('is_specific_item') and item.get('stock_item_id'):
                    stock_item_id = item['stock_item_id']
                    stock_item = StockItem.query.get(stock_item_id)
                    
                    if stock_item and stock_item.status == 'available':
                        # Mark as sold
                        stock_item.status = 'sold'
                        
                        # Create invoice item
                        invoice_item = InvoiceItem(
                            invoice_id=invoice.id,
                            product_id=product.id,
                            stock_item_id=stock_item.id,
                            quantity=1,
                            unit_price=item['price'],
                            total=item['price'],
                            discount=0.0
                        )
                        
                        db.session.add(invoice_item)
                        print(f"DEBUG: Created invoice item for specific stock item {stock_item_id}")
                
                # Handle non-specific items
                else:
                    # Get stock items for this product
                    stock_items = StockItem.query.filter_by(
                        product_id=product.id,
                        status='available'
                    ).limit(item['quantity']).all()
                    
                    for stock_item in stock_items:
                        # Mark as sold
                        stock_item.status = 'sold'
                        
                        # Create invoice item
                        invoice_item = InvoiceItem(
                            invoice_id=invoice.id,
                            product_id=product.id,
                            stock_item_id=stock_item.id,
                            quantity=1,
                            unit_price=item['price'],
                            total=item['price'],
                            discount=0.0
                        )
                        
                        db.session.add(invoice_item)
                    
                    print(f"DEBUG: Marked {len(stock_items)} stock items as sold for {product.name}")
            
            # ========== CREATE PAYMENT RECORD ==========
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
            
            # ========== COMMIT TRANSACTION ==========
            db.session.commit()
            print(f"DEBUG: Database commit successful")
            
            # ========== CLEAR CART ==========
            session.pop('cart', None)
            session.modified = True
            print(f"DEBUG: Cleared cart from session")
            
            # ========== PREPARE SUCCESS RESPONSE ==========
            response_data = {
                'success': True,
                'invoice_id': invoice.id,
                'invoice_number': invoice_number,
                'total': total,
                'subtotal': subtotal,
                'tax': tax,
                'discount': discount,
                'customer_name': customer_name,
                'message': f'Sale completed successfully! Invoice #{invoice_number}'
            }
            
            print(f"DEBUG: Checkout completed successfully")
            return jsonify(response_data)
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Database error during checkout: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                'success': False,
                'message': f'Error processing sale: {str(e)}',
                'error_type': 'database_error'
            }), 500
            
    except Exception as e:
        print(f"DEBUG: General error in checkout: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error in checkout process: {str(e)}',
            'error_type': 'server_error'
        }), 500

@pos_bp.route('/checkout-form')
@login_required
def checkout_form():
    """Return checkout form HTML"""
    return render_template('pos/checkout_modal.html')

@pos_bp.route('/daily-sales')
@login_required
@staff_required  # Only staff and admin can view daily sales
def daily_sales():
    """Daily sales report - only for staff and admin"""
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

@pos_bp.route('/get-available-stock-item', methods=['POST'])
@login_required
def get_available_stock_item():
    """Get an available stock item for a product"""
    data = request.get_json()
    product_id = data.get('product_id')
    
    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID required'})
    
    # Check if product has IMEI
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'})
    
    if not product.has_imei:
        return jsonify({'success': False, 'message': 'Product does not require serialization'})
    
    # Find an available stock item for this product
    stock_item = StockItem.query.filter_by(
        product_id=product_id,
        status='available'
    ).first()
    
    if not stock_item:
        return jsonify({'success': False, 'message': 'No available stock items'})
    
    return jsonify({
        'success': True,
        'stock_item': {
            'id': stock_item.id,
            'item_barcode': stock_item.item_barcode,
            'imei': stock_item.imei
        }
    })
    
@pos_bp.route('/search-customers', methods=['POST'])
@login_required
def search_customers():
    """Search customers by phone or name for autocomplete"""
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'success': True, 'results': []})
    
    # Search in both phone numbers and names
    customers = Customer.query.filter(
        db.or_(
            Customer.phone.ilike(f'%{query}%'),
            Customer.name.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    results = []
    for customer in customers:
        results.append({
            'id': customer.id,
            'phone': customer.phone,
            'name': customer.name,
            'email': customer.email or '',
            'display_text': f'{customer.phone} – {customer.name}'
        })
    
    return jsonify({'success': True, 'results': results})