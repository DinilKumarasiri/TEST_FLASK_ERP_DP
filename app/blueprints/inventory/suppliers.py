from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import Supplier
from . import inventory_bp
from app.utils.permissions import staff_required  # Add this import

@inventory_bp.route('/suppliers')
@login_required
@staff_required  # Changed: staff can view suppliers
def supplier_list():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('inventory/suppliers.html',
                         suppliers=suppliers,
                         title='Suppliers')

@inventory_bp.route('/supplier/<int:supplier_id>')
@login_required
@staff_required  # Changed: staff can view supplier details
def supplier_detail(supplier_id):
    from ...models import PurchaseOrder
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Get purchase orders for this supplier
    purchase_orders = PurchaseOrder.query.filter_by(
        supplier_id=supplier_id
    ).order_by(PurchaseOrder.order_date.desc()).all()
    
    return render_template('inventory/supplier_detail.html',
                         supplier=supplier,
                         purchase_orders=purchase_orders,
                         title=supplier.name)

# Supplier API endpoints
@inventory_bp.route('/api/suppliers/add', methods=['POST'])
@login_required
@staff_required  # Changed: staff can add suppliers
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
@staff_required  # Changed: staff can get supplier API
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
@staff_required  # Changed: staff can update suppliers
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
    """Delete a supplier"""
    # Changed: Only admin can delete suppliers
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