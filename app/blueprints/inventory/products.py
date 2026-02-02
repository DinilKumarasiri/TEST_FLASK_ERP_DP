from flask import render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from ... import db
from ...models import Product, ProductCategory, StockItem
from . import inventory_bp
from ... import db, csrf 
from app.utils.permissions import staff_required  # Add this import
import sys
import os
import re

# Import barcode generator
try:
    from app.utils.barcode_generator import BarcodeGenerator
    BARCODE_AVAILABLE = True
except ImportError as e:
    print(f"✗ Error importing BarcodeGenerator: {e}")
    BARCODE_AVAILABLE = False
    
    # Fallback BarcodeGenerator class
    class BarcodeGenerator:
        @staticmethod
        def generate_barcode_number(product):
            """Generate barcode number from product SKU or ID"""
            try:
                if product.sku:
                    # Clean SKU to create barcode (remove special characters)
                    barcode = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                    if len(barcode) < 8:
                        barcode = barcode.zfill(12)
                    return barcode[:12]  # Standard barcode length
                else:
                    # Use product ID padded to 12 digits
                    return str(product.id).zfill(12)
            except Exception as e:
                print(f"Error generating barcode number: {e}")
                return str(product.id).zfill(12)
        
        @staticmethod
        def generate_online_barcode_url(barcode_number, barcode_type='Code128'):
            """Get barcode image from online generator service"""
            return f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code={barcode_type}&dpi=96&dataseparator="
        
        @staticmethod
        def save_barcode_locally(barcode_number, product_id):
            """Save barcode image locally (simplified version)"""
            try:
                # Create barcode directory
                barcode_dir = os.path.join(current_app.static_folder, 'barcodes')
                if not os.path.exists(barcode_dir):
                    os.makedirs(barcode_dir)
                
                # Create a simple text file for now
                filename = f"product_{product_id}.txt"
                filepath = os.path.join(barcode_dir, filename)
                
                with open(filepath, 'w') as f:
                    f.write(f"Barcode: {barcode_number}\n")
                    f.write(f"Product ID: {product_id}\n")
                
                return f"barcodes/{filename}"
                
            except Exception as e:
                print(f"Error saving barcode locally: {e}")
                return None
        
        @staticmethod
        def validate_barcode(barcode_number):
            """Validate barcode format"""
            if not barcode_number:
                return False
            
            # Check if it's alphanumeric and reasonable length
            if len(barcode_number) < 8 or len(barcode_number) > 20:
                return False
            
            # Basic validation - can be enhanced
            return True

@inventory_bp.route('/products')
@login_required
@staff_required  # Changed: staff can view products
def product_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    barcode_status = request.args.get('barcode_status', '')
    
    query = Product.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%'),
                Product.barcode.ilike(f'%{search}%')
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Filter by barcode status
    if barcode_status == 'with_barcode':
        query = query.filter(Product.barcode != None, Product.barcode != '')
    elif barcode_status == 'without_barcode':
        query = query.filter((Product.barcode == None) | (Product.barcode == ''))
    
    products = query.order_by(Product.name).paginate(page=page, per_page=per_page)
    
    # MAKE SURE CATEGORIES ARE QUERIED
    categories = ProductCategory.query.order_by(ProductCategory.name).all()
    
    # Get stock counts for each product
    for product in products.items:
        product.stock_count = StockItem.query.filter_by(
            product_id=product.id,
            status='available'
        ).count()
    
    return render_template('inventory/products.html',
                         products=products,
                         categories=categories,  # This is important!
                         title='Products',
                         barcode_status=barcode_status)

@inventory_bp.route('/product/<int:product_id>', methods=['GET'])
@login_required
@staff_required  # Changed: staff can view product details
def product_detail(product_id):
    """Product detail page"""
    try:
        from ...models import Supplier  # Add this import
        
        # Get product
        product = Product.query.get(product_id)
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('inventory.product_list'))
        
        # Get stock items
        stock_items = StockItem.query.filter_by(
            product_id=product_id
        ).order_by(StockItem.created_at.desc()).all()
        
        # Get available stock count
        available_stock = StockItem.query.filter_by(
            product_id=product_id,
            status='available'
        ).count()
        
        # Get suppliers for the dropdown
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        return render_template('inventory/product_detail.html',
                             product=product,
                             stock_items=stock_items,
                             available_stock=available_stock,
                             suppliers=suppliers,  # Pass suppliers to template
                             title=f'{product.name} - Details')
        
    except Exception as e:
        print(f"ERROR in product_detail: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading product details: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/stock-in', methods=['GET', 'POST'])
@login_required
@staff_required
def stock_in():
    from ...models import Supplier, Product, ProductCategory, StockItem
    import time
    
    if request.method == 'POST':
        try:
            print("DEBUG: POST request received for stock-in")
            print(f"DEBUG: Form data: {dict(request.form)}")
            
            product_id = request.form.get('product_id', type=int)
            quantity = request.form.get('quantity', type=int, default=1)
            selling_price = request.form.get('selling_price', type=float)
            supplier_id = request.form.get('supplier_id', type=int)
            batch_number = request.form.get('batch_number', '')
            location = request.form.get('location', '')
            notes = request.form.get('notes', '')
            generate_individual_barcodes = True
            
            # Only admin can set purchase price
            if current_user.role == 'admin':
                purchase_price = request.form.get('purchase_price', type=float)
            else:
                purchase_price = None  # Non-admin cannot set purchase price
            
            if 'generate_individual_barcodes' in request.form:
                generate_individual_barcodes = request.form.get('generate_individual_barcodes') == 'on'
            
            # Validation
            if not product_id:
                flash('Please select a product', 'danger')
                return redirect(url_for('inventory.stock_in'))
            
            if not selling_price or selling_price <= 0:
                flash('Valid selling price is required', 'danger')
                return redirect(url_for('inventory.stock_in'))
            
            print(f"DEBUG: Product found: {product.name}, has_imei={product.has_imei}")
            
            # Generate batch barcodes if requested
            individual_barcodes = []
            if generate_individual_barcodes:
                print(f"DEBUG: Generating {quantity} individual barcodes...")
                
                # Get all existing barcodes to avoid duplicates
                existing_barcodes = set()
                existing_items = StockItem.query.filter(StockItem.item_barcode.isnot(None)).all()
                for item in existing_items:
                    if item.item_barcode:
                        existing_barcodes.add(item.item_barcode)
                
                print(f"DEBUG: Found {len(existing_barcodes)} existing barcodes in database")
                
                # Generate unique barcodes for each item
                for i in range(quantity):
                    max_attempts = 20  # Increased attempts
                    barcode_generated = False
                    
                    for attempt in range(max_attempts):
                        try:
                            # Generate barcode with more randomness
                            timestamp = int(time.time() * 1000) % 1000000
                            random_suffix = ''.join([str(time.time_ns() % 10) for _ in range(4)])
                            
                            if product.sku:
                                base = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                                if len(base) < 4:
                                    base = base.ljust(4, 'X')
                                barcode = f"{base[:4]}{timestamp:08d}{random_suffix}"
                            else:
                                barcode = f"P{product.id:04d}{timestamp:08d}{random_suffix}"
                            
                            # Ensure proper length (12-13 digits)
                            if len(barcode) < 12:
                                barcode = barcode.ljust(12, '0')
                            elif len(barcode) > 13:
                                barcode = barcode[:13]
                            
                            # Add check digit
                            if len(barcode) == 12:
                                digits = [int(d) for d in barcode if d.isdigit()]
                                if len(digits) == 12:
                                    odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
                                    even_sum = sum(digits[i] for i in range(1, 12, 2))
                                    total = odd_sum + even_sum
                                    check_digit = (10 - (total % 10)) % 10
                                    barcode = barcode + str(check_digit)
                            
                            # Check if barcode already exists
                            if barcode in existing_barcodes:
                                print(f"DEBUG: Barcode {barcode} already exists, generating new one...")
                                time.sleep(0.001)  # Small delay for different timestamp
                                continue
                            
                            # Check in database
                            existing = StockItem.query.filter_by(item_barcode=barcode).first()
                            if existing:
                                print(f"DEBUG: Barcode {barcode} exists in DB, generating new one...")
                                existing_barcodes.add(barcode)
                                time.sleep(0.001)
                                continue
                            
                            # Valid unique barcode found
                            individual_barcodes.append(barcode)
                            existing_barcodes.add(barcode)
                            print(f"DEBUG: Generated unique barcode {i+1}/{quantity}: {barcode}")
                            barcode_generated = True
                            break
                            
                        except Exception as e:
                            print(f"DEBUG: Error generating barcode: {e}")
                            # Fallback barcode
                            fallback = f"F{int(time.time() * 1000000)}{i}"
                            individual_barcodes.append(fallback)
                            existing_barcodes.add(fallback)
                            barcode_generated = True
                            break
                    
                    if not barcode_generated:
                        # Last resort
                        last_resort = f"L{int(time.time() * 1000000)}{i}"
                        individual_barcodes.append(last_resort)
                        print(f"DEBUG: Using last resort barcode: {last_resort}")
            
            # Check for IMEI validation if product requires it
            if product.has_imei:
                print("DEBUG: Product requires IMEI, validating...")
                # Validate all IMEI numbers are provided
                for i in range(quantity):
                    imei = request.form.get(f'imei_{i}', '').strip()
                    print(f"DEBUG: IMEI {i}: {imei}")
                    if not imei:
                        flash(f'IMEI #{i+1} is required for this product', 'danger')
                        print(f"DEBUG: Missing IMEI #{i}")
                        return redirect(url_for('inventory.stock_in'))
                    
                    # Check for duplicate IMEI in database
                    existing = StockItem.query.filter_by(imei=imei).first()
                    if existing:
                        flash(f'IMEI {imei} already exists in database', 'danger')
                        print(f"DEBUG: Duplicate IMEI: {imei}")
                        return redirect(url_for('inventory.stock_in'))
            
            print(f"DEBUG: Adding {quantity} stock items...")
            
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
                    notes=notes,
                    is_serialized=generate_individual_barcodes  # Mark as serialized
                )
                
                # Add IMEI if product has it
                if product.has_imei:
                    imei = request.form.get(f'imei_{i}', '').strip()
                    stock_item.imei = imei
                    print(f"DEBUG: Added IMEI {imei} to stock item")
                
                # Generate unique barcode if requested
                if generate_individual_barcodes:
                    if i < len(individual_barcodes):
                        stock_item.item_barcode = individual_barcodes[i]
                    else:
                        # Generate a unique barcode on the fly with more randomness
                        timestamp = int(time.time() * 1000000)
                        stock_item.item_barcode = f"{product.sku if product.sku else 'ITEM'}{timestamp}{i}"
                    
                    # Double-check for duplicate before committing
                    existing = StockItem.query.filter_by(item_barcode=stock_item.item_barcode).first()
                    if existing:
                        # Regenerate if duplicate found
                        timestamp = int(time.time() * 1000000) + i
                        stock_item.item_barcode = f"{product.sku if product.sku else 'ITEM'}{timestamp}{i}"
                        print(f"DEBUG: Regenerated duplicate barcode to: {stock_item.item_barcode}")
                    
                    print(f"DEBUG: Added unique barcode {stock_item.item_barcode} to stock item")
                
                db.session.add(stock_item)
            
            db.session.commit()
            
            # Update product barcode if not exists
            if not product.barcode:
                product.barcode = BarcodeGenerator.generate_product_barcode(product)
                product.barcode_image = BarcodeGenerator.generate_online_barcode_url(product.barcode)
                db.session.commit()
            
            print("DEBUG: Database commit successful")
            flash(f'{quantity} items added to stock successfully', 'success')
            
            # If individual barcodes were generated, show them
            if generate_individual_barcodes:
                return render_template('inventory/stock_item_barcode.html',
                                    product=product,
                                    barcodes=individual_barcodes,
                                    quantity=quantity)
            
            return redirect(url_for('inventory.product_detail', product_id=product_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"DEBUG: Error occurred: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error adding stock: {str(e)}', 'danger')
            return redirect(url_for('inventory.stock_in'))
    
    # ============ GET REQUEST ============
    # GET request - show the form
    try:
        print("DEBUG: GET request received for stock-in")
        
        # Get all active products
        products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
        
        # Calculate stock count for each product
        for product in products:
            product.stock_count = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
        
        # Get all suppliers
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        # Get all categories
        categories = ProductCategory.query.order_by(ProductCategory.name).all()
        
        # Get product ID from query string if provided
        product_id = request.args.get('product_id', type=int)
        
        print(f"DEBUG: Found {len(products)} products, {len(suppliers)} suppliers, {len(categories)} categories")
        
        return render_template('inventory/stock_in.html',
                             products=products,
                             suppliers=suppliers,
                             categories=categories,
                             selected_product_id=product_id,
                             title='Stock In')
        
    except Exception as e:
        print(f"ERROR in stock_in (GET): {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading stock in form: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/stock-out', methods=['POST'])
@login_required
@staff_required  # Changed: staff can remove stock
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

@inventory_bp.route('/add-product', methods=['POST'])
@login_required
@staff_required  # Changed: staff can add products
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

@inventory_bp.route('/api/products/search')
@login_required
@staff_required  # Changed: staff can search products
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
                'barcode': product.barcode,
                'purchase_price': product.purchase_price,
                'selling_price': product.selling_price,
                'stock_count': stock_count,
                'min_stock_level': product.min_stock_level
            })
        
        return jsonify({'success': True, 'products': product_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@inventory_bp.route('/product/<int:product_id>/purchase-history')
@login_required
@staff_required  # Changed: staff can view purchase history
def product_purchase_history(product_id):
    """Show purchase history for a specific product"""
    try:
        from ...models import PurchaseOrderItem
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

@inventory_bp.route('/product/<int:product_id>/info')
@login_required
@staff_required  # Changed: staff can get product info
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
                'barcode': product.barcode,
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

@inventory_bp.route('/products/export')
@login_required
@staff_required  # Changed: staff can export products
def export_products():
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['ID', 'Name', 'SKU', 'Barcode', 'Category', 'Purchase Price', 
                         'Selling Price', 'Current Stock', 'Min Stock', 'Status'])
        
        # Get all active products (or filtered if needed)
        query = Product.query.filter_by(is_active=True)
        
        # Apply filters if any
        search = request.args.get('search', '')
        if search:
            query = query.filter(
                db.or_(
                    Product.name.ilike(f'%{search}%'),
                    Product.sku.ilike(f'%{search}%'),
                    Product.description.ilike(f'%{search}%')
                )
            )
        
        category_id = request.args.get('category_id', type=int)
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        products = query.order_by(Product.name).all()
        
        for product in products:
            # Get current stock count
            stock_count = StockItem.query.filter_by(
                product_id=product.id,
                status='available'
            ).count()
            
            writer.writerow([
                product.id,
                product.name,
                product.sku,
                product.barcode or '',
                product.category.name if product.category else '',
                product.purchase_price,
                product.selling_price,
                stock_count,
                product.min_stock_level,
                'Active' if product.is_active else 'Inactive'
            ])
        
        # Return CSV file
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={
                "Content-disposition": "attachment; filename=products_export.csv",
                "Content-type": "text/csv; charset=utf-8"
            }
        )
    except Exception as e:
        flash(f'Error exporting products: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/test/<int:product_id>')
@login_required
@staff_required  # Changed: staff can access test pages
def test_product_detail(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return f"Product {product_id} not found", 404
        
        return f"""
        <h1>Test Product Page</h1>
        <p>Product ID: {product_id}</p>
        <p>Product Name: {product.name}</p>
        <p>SKU: {product.sku}</p>
        <p>Barcode: {product.barcode or 'No barcode'}</p>
        <p>Exists: Yes</p>
        <a href="/inventory/products">Back to Products</a>
        """
    except Exception as e:
        return f"Error: {str(e)}", 500

@inventory_bp.route('/add-new-product', methods=['GET', 'POST'])
@login_required
@staff_required
def add_new_product():
    """Add new product form"""
    from ...models import ProductCategory
    
    # GET recent products for the sidebar
    recent_products = Product.query.filter_by(is_active=True)\
        .order_by(Product.created_at.desc())\
        .limit(5).all()
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name', '').strip()
            sku = request.form.get('sku', '').strip()
            barcode = request.form.get('barcode', '').strip()
            description = request.form.get('description', '').strip()
            category_id = request.form.get('category_id', type=int)
            purchase_price = request.form.get('purchase_price', type=float)
            selling_price = request.form.get('selling_price', type=float)
            wholesale_price = request.form.get('wholesale_price', type=float)
            min_stock_level = request.form.get('min_stock_level', type=int, default=5)
            has_imei = request.form.get('has_imei') == 'on'
            
            # Validation - REMOVE purchase_price validation
            if not name:
                flash('Product name is required', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            if not sku:
                flash('SKU is required', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            # Check if SKU already exists
            existing_product = Product.query.filter_by(sku=sku).first()
            if existing_product:
                flash(f'Product with SKU "{sku}" already exists', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            # Check if barcode already exists
            if barcode:
                existing_barcode = Product.query.filter_by(barcode=barcode).first()
                if existing_barcode:
                    flash(f'Product with barcode "{barcode}" already exists', 'danger')
                    return redirect(url_for('inventory.add_new_product'))
            
            # REMOVED: Validation for purchase_price
            # if not purchase_price or purchase_price <= 0:
            #     flash('Valid purchase price is required', 'danger')
            #     return redirect(url_for('inventory.add_new_product'))
            
            if not selling_price or selling_price <= 0:
                flash('Valid selling price is required', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            # Create new product
            product = Product(
                name=name,
                sku=sku,
                barcode=barcode if barcode else None,
                description=description,
                category_id=category_id if category_id else None,
                purchase_price=purchase_price,  # Can be None
                selling_price=selling_price,
                wholesale_price=wholesale_price,
                min_stock_level=min_stock_level,
                has_imei=has_imei,
                is_active=True
            )
            
            db.session.add(product)
            db.session.commit()
            
            # Generate barcode if not provided
            if not barcode:
                try:
                    product.barcode = BarcodeGenerator.generate_barcode_number(product)
                    product.barcode_image = BarcodeGenerator.generate_online_barcode_url(product.barcode)
                    db.session.commit()
                except Exception as e:
                    print(f"Warning: Could not generate barcode: {e}")
            
            flash(f'Product "{name}" added successfully!', 'success')
            return redirect(url_for('inventory.product_detail', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            return redirect(url_for('inventory.add_new_product'))
    
    # GET request - show form (no changes needed here)
    categories = ProductCategory.query.all()
    return render_template('inventory/add_product.html',
                         categories=categories,
                         products=recent_products, 
                         title='Add New Product')

@inventory_bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_product(product_id):
    """Edit existing product"""
    from ...models import ProductCategory
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            product.name = request.form.get('name', '').strip()
            product.sku = request.form.get('sku', '').strip()
            product.barcode = request.form.get('barcode', '').strip()
            product.description = request.form.get('description', '').strip()
            product.category_id = request.form.get('category_id', type=int)
            product.purchase_price = request.form.get('purchase_price', type=float)  # Can be None
            product.selling_price = request.form.get('selling_price', type=float)
            product.wholesale_price = request.form.get('wholesale_price', type=float)
            product.min_stock_level = request.form.get('min_stock_level', type=int, default=5)
            product.has_imei = request.form.get('has_imei') == 'on'
            product.is_active = request.form.get('is_active') == 'on'
            
            # Validation
            if not product.name:
                flash('Product name is required', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            if not product.sku:
                flash('SKU is required', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            # Check if SKU already exists (excluding current product)
            existing_product = Product.query.filter(
                Product.sku == product.sku,
                Product.id != product_id
            ).first()
            
            if existing_product:
                flash(f'Product with SKU "{product.sku}" already exists', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            # Check if barcode already exists (excluding current product)
            if product.barcode:
                existing_barcode = Product.query.filter(
                    Product.barcode == product.barcode,
                    Product.id != product_id
                ).first()
                
                if existing_barcode:
                    flash(f'Product with barcode "{product.barcode}" already exists', 'danger')
                    return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            # REMOVED: Validation for purchase_price
            # if not product.purchase_price or product.purchase_price <= 0:
            #     flash('Valid purchase price is required', 'danger')
            #     return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            if not product.selling_price or product.selling_price <= 0:
                flash('Valid selling price is required', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            # Update barcode image if barcode changed
            if product.barcode:
                product.barcode_image = BarcodeGenerator.generate_online_barcode_url(product.barcode)
            
            db.session.commit()
            flash(f'Product "{product.name}" updated successfully!', 'success')
            return redirect(url_for('inventory.product_detail', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            return redirect(url_for('inventory.edit_product', product_id=product_id))
    
    # GET request - show form (no changes needed)
    categories = ProductCategory.query.all()
    return render_template('inventory/edit_product.html',
                         product=product,
                         categories=categories,
                         title=f'Edit {product.name}')

@inventory_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete a product with password confirmation and foreign key handling"""
    try:
        # Only admin can delete products
        if current_user.role != 'admin':
            flash('Only admin can delete products', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        product = Product.query.get_or_404(product_id)
        
        # Get data from form
        password = request.form.get('password', '').strip()
        confirm_delete = request.form.get('confirm_delete')  # Checkbox value
        
        # Basic validation
        if not password:
            flash('Admin password is required', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        if confirm_delete != 'on':  # Checkbox returns 'on' when checked
            flash('Please confirm deletion by checking the confirmation box', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        # Verify admin password
        from ...models import User
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user.check_password(password):
            flash('Incorrect admin password', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        # Check for related records that prevent deletion
        from ...models import InvoiceItem, RepairItem, PurchaseOrderItem
        
        # Check all related tables
        has_invoice_items = InvoiceItem.query.filter_by(product_id=product_id).first() is not None
        has_repair_items = RepairItem.query.filter_by(product_id=product_id).first() is not None
        has_purchase_order_items = PurchaseOrderItem.query.filter_by(product_id=product_id).first() is not None
        has_stock_items = StockItem.query.filter_by(product_id=product_id).first() is not None
        
        # If there are any related records, we cannot delete - only deactivate
        if has_invoice_items or has_repair_items or has_purchase_order_items or has_stock_items:
            # Show specific message about what's preventing deletion
            reasons = []
            if has_invoice_items:
                reasons.append("invoice items")
            if has_repair_items:
                reasons.append("repair items")
            if has_purchase_order_items:
                reasons.append("purchase order items")
            if has_stock_items:
                reasons.append("stock items")
            
            reason_message = ", ".join(reasons)
            
            # Deactivate the product instead
            product.is_active = False
            db.session.commit()
            
            flash(f'Product "{product.name}" has been deactivated. Cannot delete because it has related {reason_message}.', 'warning')
        else:
            # Safe to delete - no related records
            db.session.delete(product)
            db.session.commit()
            flash(f'Product "{product.name}" has been permanently deleted!', 'success')
        
        return redirect(url_for('inventory.product_list'))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting product: {str(e)}")  # For debugging
        flash(f'Error deleting product: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

# ============ BARCODE ROUTES ============

@inventory_bp.route('/product/<int:product_id>/generate-barcode', methods=['POST'])
@login_required
@staff_required  # Changed: staff can generate barcodes
def generate_product_barcode(product_id):
    """Generate barcode for a product"""
    try:
        product = Product.query.get_or_404(product_id)
        
        print(f"Generating barcode for product: {product.name} (ID: {product.id})")
        
        # Generate barcode number
        barcode_number = BarcodeGenerator.generate_barcode_number(product)
        
        # Generate online barcode URL
        barcode_url = BarcodeGenerator.generate_online_barcode_url(barcode_number)
        
        # Save to product
        product.barcode = barcode_number
        product.barcode_image = barcode_url
        
        db.session.commit()
        
        flash(f'✅ Barcode generated successfully: {barcode_number}', 'success')
        return redirect(url_for('inventory.product_detail', product_id=product_id))
        
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in generate_product_barcode: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error generating barcode: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

@inventory_bp.route('/product/<int:product_id>/print-barcode')
@login_required
@staff_required  # Changed: staff can print barcodes
def print_product_barcode(product_id):
    """Print barcode label"""
    try:
        product = Product.query.get_or_404(product_id)
        
        if not product.barcode:
            flash('Product does not have a barcode. Generate one first.', 'warning')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        return render_template('inventory/print_barcode.html',
                             product=product,
                             title=f'Print Barcode - {product.name}')
        
    except Exception as e:
        flash(f'Error printing barcode: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

@inventory_bp.route('/api/products/barcode-scan', methods=['POST'])
@login_required
@staff_required  # Changed: staff can scan barcodes
def api_barcode_scan():
    """API endpoint for barcode scanning"""
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({'success': False, 'message': 'No barcode provided'})
        
        print(f"DEBUG: Scanning barcode: {barcode}")
        
        # Search product by barcode
        product = Product.query.filter_by(barcode=barcode, is_active=True).first()
        
        if not product:
            # Try searching by SKU
            product = Product.query.filter_by(sku=barcode, is_active=True).first()
            if product:
                print(f"DEBUG: Found product by SKU: {product.name}")
        
        if product:
            # Get current stock
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
                    'barcode': product.barcode,
                    'selling_price': float(product.selling_price),
                    'stock_count': stock_count,
                    'has_imei': product.has_imei,
                    'category': product.category.name if product.category else None
                }
            })
        else:
            print(f"DEBUG: Product not found for barcode: {barcode}")
            return jsonify({
                'success': False, 
                'message': 'Product not found'
            })
            
    except Exception as e:
        print(f"ERROR in api_barcode_scan: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@inventory_bp.route('/product/<int:product_id>/edit-barcode', methods=['POST'])
@login_required
@staff_required  # Changed: staff can edit barcodes
def edit_product_barcode(product_id):
    """Manually edit product barcode"""
    try:
        product = Product.query.get_or_404(product_id)
        
        new_barcode = request.form.get('barcode', '').strip()
        
        if not new_barcode:
            flash('Barcode cannot be empty', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        # Check if barcode already exists for another product
        existing = Product.query.filter(
            Product.barcode == new_barcode,
            Product.id != product_id
        ).first()
        
        if existing:
            flash(f'Barcode {new_barcode} already exists for product: {existing.name}', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        # Update barcode
        product.barcode = new_barcode
        product.barcode_image = BarcodeGenerator.generate_online_barcode_url(new_barcode)
        
        db.session.commit()
        
        flash(f'Barcode updated to: {new_barcode}', 'success')
        return redirect(url_for('inventory.product_detail', product_id=product_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating barcode: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

@inventory_bp.route('/bulk-generate-barcodes', methods=['POST'])
@login_required
def bulk_generate_barcodes():
    """Generate barcodes for all products without barcodes"""
    # Changed: Only admin can generate bulk barcodes
    if current_user.role != 'admin':
        flash('Only admin can generate barcodes in bulk', 'danger')
        return redirect(url_for('inventory.product_list'))
    
    try:
        products_without_barcode = Product.query.filter(
            (Product.barcode == None) | (Product.barcode == ''),
            Product.is_active == True
        ).all()
        
        count = 0
        for product in products_without_barcode:
            barcode_number = BarcodeGenerator.generate_barcode_number(product)
            barcode_url = BarcodeGenerator.generate_online_barcode_url(barcode_number)
            
            product.barcode = barcode_number
            product.barcode_image = barcode_url
            count += 1
        
        db.session.commit()
        
        flash(f'Generated barcodes for {count} products', 'success')
        return redirect(url_for('inventory.product_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating barcodes in bulk: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/product/<int:product_id>/barcode-info')
@login_required
@staff_required  # Changed: staff can get barcode info
def product_barcode_info(product_id):
    """Get barcode information for a product"""
    try:
        product = Product.query.get_or_404(product_id)
        
        return jsonify({
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'barcode': product.barcode,
                'barcode_image': product.get_barcode_image_url() if hasattr(product, 'get_barcode_image_url') else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
# Add to products.py

@inventory_bp.route('/product/<int:product_id>/serialized-items')
@login_required
@staff_required  # Changed: staff can view serialized items
def serialized_items(product_id):
    """View all serialized stock items for a product"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get serialized items (items with individual barcodes)
        serialized_items = StockItem.query.filter_by(
            product_id=product_id,
            is_serialized=True
        ).order_by(StockItem.created_at.desc()).all()
        
        # Get non-serialized items count
        non_serialized_count = StockItem.query.filter_by(
            product_id=product_id,
            is_serialized=False,
            status='available'
        ).count()
        
        return render_template('inventory/serialized_items.html',
                             product=product,
                             serialized_items=serialized_items,
                             non_serialized_count=non_serialized_count,
                             title=f'Serialized Items - {product.name}')
        
    except Exception as e:
        flash(f'Error loading serialized items: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))

@inventory_bp.route('/stock-item/<int:item_id>/generate-barcode', methods=['POST'])
@login_required
@staff_required  # Changed: staff can generate item barcodes
def generate_stock_item_barcode(item_id):
    """Generate unique barcode for individual stock item"""
    try:
        stock_item = StockItem.query.get_or_404(item_id)
        
        if stock_item.item_barcode:
            flash('This item already has a barcode', 'warning')
            return redirect(request.referrer or url_for('inventory.product_detail', product_id=stock_item.product_id))
        
        # Generate unique barcode
        stock_item.item_barcode = stock_item.generate_unique_barcode()
        stock_item.is_serialized = True
        
        db.session.commit()
        
        flash(f'✅ Unique barcode generated: {stock_item.item_barcode}', 'success')
        return redirect(request.referrer or url_for('inventory.product_detail', product_id=stock_item.product_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error generating barcode: {str(e)}', 'danger')
        return redirect(request.referrer)

# ============ CATEGORY ROUTES ============

@inventory_bp.route('/categories')
@login_required
@staff_required  # Changed: staff can view categories
def category_list():
    """View all product categories"""
    try:
        categories = ProductCategory.query.order_by(ProductCategory.name).all()
        
        # Count products in each category
        for category in categories:
            category.product_count = Product.query.filter_by(
                category_id=category.id,
                is_active=True
            ).count()
        
        return render_template('inventory/categories.html',
                             categories=categories,
                             title='Product Categories')
        
    except Exception as e:
        flash(f'Error loading categories: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/add-category', methods=['POST'])
@login_required
@staff_required  # Changed: staff can add categories
def add_category():
    """Add new product category - Simple and robust version"""
    try:
        print("\n" + "="*60)
        print("🔄 ADD CATEGORY REQUEST STARTED")
        print("="*60)
        
        # Get form data
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        redirect_to = request.form.get('redirect_to', 'products')
        
        print(f"📝 Form data received:")
        print(f"  Name: '{name}'")
        print(f"  Description: '{description}'")
        print(f"  Redirect to: '{redirect_to}'")
        
        # Validation
        if not name:
            flash('Category name is required', 'danger')
            print("❌ Validation failed: Name is empty")
            return redirect(request.referrer or url_for('inventory.product_list'))
        
        # Check if category already exists
        existing_category = ProductCategory.query.filter_by(name=name).first()
        if existing_category:
            flash(f'Category "{name}" already exists', 'danger')
            print(f"❌ Category '{name}' already exists (ID: {existing_category.id})")
            return redirect(request.referrer or url_for('inventory.product_list'))
        
        print(f"✅ Validation passed. Creating category...")
        
        # Create new category
        category = ProductCategory(
            name=name,
            description=description if description else None
        )
        
        db.session.add(category)
        db.session.flush()  # Get the ID without committing yet
        print(f"📦 Category object created with ID: {category.id}")
        
        db.session.commit()
        print(f"💾 Database committed successfully!")
        
        flash(f'Category "{name}" added successfully!', 'success')
        print(f"✅ Category '{name}' added with ID: {category.id}")
        
        # Return to appropriate page
        if redirect_to == 'products':
            return redirect(url_for('inventory.product_list'))
        else:
            return redirect(url_for('inventory.category_list'))
        
    except Exception as e:
        print(f"\n❌ ERROR in add_category:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60 + "\n")
        
        db.session.rollback()
        flash(f'Error adding category: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('inventory.product_list'))

@inventory_bp.route('/category/<int:category_id>/edit', methods=['POST'])
@login_required
@staff_required  # Changed: staff can edit categories
def edit_category(category_id):
    """Edit existing category"""
    try:
        category = ProductCategory.query.get_or_404(category_id)
        
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Category name is required', 'danger')
            return redirect(url_for('inventory.category_list'))
        
        # Check if name already exists (excluding current category)
        existing_category = ProductCategory.query.filter(
            ProductCategory.name == name,
            ProductCategory.id != category_id
        ).first()
        
        if existing_category:
            flash(f'Category "{name}" already exists', 'danger')
            return redirect(url_for('inventory.category_list'))
        
        # Update category
        category.name = name
        category.description = description
        
        db.session.commit()
        
        flash(f'Category "{name}" updated successfully!', 'success')
        return redirect(url_for('inventory.category_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating category: {str(e)}', 'danger')
        return redirect(url_for('inventory.category_list'))

@inventory_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """Delete a category"""
    # Changed: Only admin can delete categories
    if current_user.role != 'admin':
        flash('Only admin can delete categories', 'danger')
        return redirect(url_for('inventory.category_list'))
    
    try:
        category = ProductCategory.query.get_or_404(category_id)
        
        # Check if category has products
        product_count = Product.query.filter_by(category_id=category_id).count()
        if product_count > 0:
            flash(f'Cannot delete category "{category.name}" because it has {product_count} products. Reassign products first.', 'danger')
            return redirect(url_for('inventory.category_list'))
        
        db.session.delete(category)
        db.session.commit()
        
        flash(f'Category "{category.name}" deleted successfully!', 'success')
        return redirect(url_for('inventory.category_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'danger')
        return redirect(url_for('inventory.category_list'))

@inventory_bp.route('/api/categories')
@login_required
@staff_required  # Changed: staff can get category API
def api_get_categories():
    """API endpoint to get categories for AJAX requests"""
    try:
        categories = ProductCategory.query.order_by(ProductCategory.name).all()
        
        category_list = []
        for category in categories:
            category_list.append({
                'id': category.id,
                'name': category.name,
                'description': category.description
            })
        
        return jsonify({'success': True, 'categories': category_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    
@inventory_bp.route('/fix-barcodes')
@login_required
def fix_barcodes():
    """Fix all NULL barcodes"""
    # Changed: Only admin can fix barcodes
    if current_user.role != 'admin':
        flash('Only admin can fix barcodes', 'danger')
        return redirect(url_for('inventory.product_list'))
    
    fixed_count = StockItem.fix_all_null_barcodes()
    
    flash(f'Fixed {fixed_count} items with NULL barcodes', 'success')
    return redirect(url_for('inventory.product_list'))