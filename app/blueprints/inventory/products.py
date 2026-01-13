from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import Product, ProductCategory, StockItem
from . import inventory_bp
from ... import db, csrf 

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

@inventory_bp.route('/product/<int:product_id>', methods=['GET'])
@login_required
def product_detail(product_id):
    """Product detail page"""
    try:
        print(f"DEBUG: Accessing product_detail for ID: {product_id}")
        
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
        
        return render_template('inventory/product_detail.html',
                             product=product,
                             stock_items=stock_items,
                             available_stock=available_stock,
                             title=f'{product.name} - Details')
        
    except Exception as e:
        print(f"ERROR in product_detail: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error loading product details: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_list'))

@inventory_bp.route('/stock-in', methods=['GET', 'POST'])
@login_required
def stock_in():
    from ...models import Supplier
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

@inventory_bp.route('/product/<int:product_id>/purchase-history')
@login_required
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
    
@inventory_bp.route('/products/export')
@login_required
def export_products():
    try:
        import csv
        from io import StringIO
        from flask import Response
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['ID', 'Name', 'SKU', 'Category', 'Purchase Price', 
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
        <p>Exists: Yes</p>
        <a href="/inventory/products">Back to Products</a>
        """
    except Exception as e:
        return f"Error: {str(e)}", 500
    
@inventory_bp.route('/add-new-product', methods=['GET', 'POST'])
@login_required
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
            description = request.form.get('description', '').strip()
            category_id = request.form.get('category_id', type=int)
            purchase_price = request.form.get('purchase_price', type=float)
            selling_price = request.form.get('selling_price', type=float)
            wholesale_price = request.form.get('wholesale_price', type=float)
            min_stock_level = request.form.get('min_stock_level', type=int, default=5)
            has_imei = request.form.get('has_imei') == 'on'
            
            # Validation
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
            
            if not purchase_price or purchase_price <= 0:
                flash('Valid purchase price is required', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            if not selling_price or selling_price <= 0:
                flash('Valid selling price is required', 'danger')
                return redirect(url_for('inventory.add_new_product'))
            
            # Create new product
            product = Product(
                name=name,
                sku=sku,
                description=description,
                category_id=category_id if category_id else None,
                purchase_price=purchase_price,
                selling_price=selling_price,
                wholesale_price=wholesale_price,
                min_stock_level=min_stock_level,
                has_imei=has_imei,
                is_active=True
            )
            
            db.session.add(product)
            db.session.commit()
            
            flash(f'Product "{name}" added successfully!', 'success')
            return redirect(url_for('inventory.product_detail', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            return redirect(url_for('inventory.add_new_product'))
    
    # GET request - show form
    categories = ProductCategory.query.all()
    return render_template('inventory/add_product.html',
                         categories=categories,
                         products=recent_products, 
                         title='Add New Product')


@inventory_bp.route('/product/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit existing product"""
    from ...models import ProductCategory
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            product.name = request.form.get('name', '').strip()
            product.sku = request.form.get('sku', '').strip()
            product.description = request.form.get('description', '').strip()
            product.category_id = request.form.get('category_id', type=int)
            product.purchase_price = request.form.get('purchase_price', type=float)
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
            
            if not product.purchase_price or product.purchase_price <= 0:
                flash('Valid purchase price is required', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            if not product.selling_price or product.selling_price <= 0:
                flash('Valid selling price is required', 'danger')
                return redirect(url_for('inventory.edit_product', product_id=product_id))
            
            db.session.commit()
            flash(f'Product "{product.name}" updated successfully!', 'success')
            return redirect(url_for('inventory.product_detail', product_id=product.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            return redirect(url_for('inventory.edit_product', product_id=product_id))
    
    # GET request - show form
    categories = ProductCategory.query.all()
    return render_template('inventory/edit_product.html',
                         product=product,
                         categories=categories,
                         title=f'Edit {product.name}')


@inventory_bp.route('/product/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete a product (soft delete)"""
    if current_user.role != 'admin':
        flash('Only admin can delete products', 'danger')
        return redirect(request.referrer or url_for('inventory.product_list'))
    
    product = Product.query.get_or_404(product_id)
    
    try:
        # Check if product has stock items
        has_stock = StockItem.query.filter_by(product_id=product_id).first() is not None
        
        if has_stock:
            flash('Cannot delete product with existing stock items. Deactivate instead.', 'danger')
            return redirect(url_for('inventory.product_detail', product_id=product_id))
        
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Product "{product.name}" deleted successfully!', 'success')
        return redirect(url_for('inventory.product_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
        return redirect(url_for('inventory.product_detail', product_id=product_id))