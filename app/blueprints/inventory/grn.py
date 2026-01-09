from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import PurchaseOrder, StockItem
from . import inventory_bp

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
