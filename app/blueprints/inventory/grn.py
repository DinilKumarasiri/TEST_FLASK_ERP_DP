from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import PurchaseOrder, StockItem, Product
from . import inventory_bp
from app.utils.permissions import staff_required  # Add this import

@inventory_bp.route('/receive-grn/<int:po_id>', methods=['GET', 'POST'])
@login_required
@staff_required  # Changed: staff can receive goods
def receive_grn(po_id):
    try:
        print(f"DEBUG: Entering receive_grn route for PO ID: {po_id}")
        
        purchase_order = PurchaseOrder.query.get_or_404(po_id)
        print(f"DEBUG: Found PO: {purchase_order.po_number}")
        print(f"DEBUG: PO has {len(purchase_order.po_items)} items")
        
        if request.method == 'POST':
            print(f"DEBUG: POST request received for receive_grn")
            print(f"DEBUG: Form data keys: {list(request.form.keys())}")
            
            for item in purchase_order.po_items:
                received_qty = request.form.get(f'received_qty_{item.id}', type=int)
                print(f"DEBUG: Processing item {item.id}: received_qty={received_qty}")
                
                if received_qty is not None and received_qty > 0:
                    # Update received quantity
                    current_received = item.received_quantity or 0
                    item.received_quantity = current_received + received_qty
                    
                    print(f"DEBUG: Creating {received_qty} stock items for product {item.product_id}")
                    
                    # Create stock items
                    for i in range(received_qty):
                        stock_item = StockItem(
                            product_id=item.product_id,
                            stock_type='in',
                            quantity=1,
                            purchase_price=item.unit_price,
                            selling_price=item.product.selling_price if item.product else 0,
                            supplier_id=purchase_order.supplier_id,
                            purchase_order_id=po_id,
                            status='available',
                            batch_number=f"PO-{purchase_order.po_number}-{item.id}",
                            location='Warehouse'
                        )
                        db.session.add(stock_item)
                        print(f"DEBUG: Created stock item {i+1}/{received_qty}")
            
            # Update PO status
            all_received = True
            for item in purchase_order.po_items:
                required_qty = item.quantity or 0
                received_qty = item.received_quantity or 0
                if received_qty < required_qty:
                    all_received = False
                    break
            
            purchase_order.status = 'received' if all_received else 'partial'
            print(f"DEBUG: Setting PO status to: {purchase_order.status}")
            
            db.session.commit()
            print(f"DEBUG: Database commit successful")
            flash('Goods received successfully', 'success')
            return redirect(url_for('inventory.purchase_order_detail', po_id=po_id))
        
        # GET request - show the form
        print(f"DEBUG: Rendering receive_grn.html template")
        return render_template('inventory/receive_grn.html',
                             purchase_order=purchase_order,
                             title='Receive Goods')
    
    except Exception as e:
        db.session.rollback()
        print(f"ERROR in receive_grn: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error receiving goods: {str(e)}', 'danger')
        return redirect(url_for('inventory.purchase_order_detail', po_id=po_id))