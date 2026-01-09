from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import PurchaseOrder, PurchaseOrderItem, Supplier, Product, User
from datetime import datetime
import random
import string
from . import inventory_bp

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
