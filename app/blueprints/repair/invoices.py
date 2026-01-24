# app/blueprints/repair/invoices.py
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import RepairJob, RepairInvoice, RepairInvoiceItem, RepairPayment, Customer
from datetime import datetime, timedelta
import random
import string
from . import repair_bp

def generate_repair_invoice_number():
    """Generate unique repair invoice number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_str = ''.join(random.choices(string.digits, k=4))
    invoice_number = f'RI-{date_str}-{random_str}'
    
    # Check if exists
    while RepairInvoice.query.filter_by(invoice_number=invoice_number).first():
        random_str = ''.join(random.choices(string.digits, k=4))
        invoice_number = f'RI-{date_str}-{random_str}'
    
    return invoice_number

@repair_bp.route('/job/<int:job_id>/create-repair-invoice', methods=['POST'])
@login_required
def create_repair_invoice(job_id):
    """Create repair invoice for a completed job"""
    try:
        job = RepairJob.query.get_or_404(job_id)
        
        if job.status != 'completed':
            flash('Only completed jobs can be invoiced', 'danger')
            return redirect(url_for('repair.job_detail', job_id=job_id))
        
        # Check if invoice already exists
        existing_invoice = RepairInvoice.query.filter_by(repair_job_id=job_id).first()
        if existing_invoice:
            flash(f'Invoice already exists: {existing_invoice.invoice_number}', 'warning')
            return redirect(url_for('repair.repair_invoice_detail', invoice_id=existing_invoice.id))
        
        # Generate invoice number
        invoice_number = generate_repair_invoice_number()
        
        # Calculate costs
        parts_cost = sum(item.total_price for item in job.repair_items) if job.repair_items else 0
        labor_cost = float(request.form.get('labor_cost', 0))
        total_cost = parts_cost + labor_cost
        advance_paid = job.estimated_cost or 0
        balance_due = total_cost - advance_paid
        
        # Calculate tax and grand total
        tax_rate = float(request.form.get('tax_rate', 0))
        tax_amount = total_cost * tax_rate/100
        grand_total = total_cost + tax_amount
        
        # Create repair invoice
        invoice = RepairInvoice(
            invoice_number=invoice_number,
            repair_job_id=job_id,
            customer_id=job.customer_id,
            customer_name=job.customer.name if job.customer else '',
            customer_phone=job.customer.phone if job.customer else '',
            
            # Device info
            device_type=job.device_type,
            brand=job.brand,
            model=job.model,
            imei=job.imei,
            
            # Financials
            labor_cost=labor_cost,
            parts_cost=parts_cost,
            total_cost=total_cost,
            advance_paid=advance_paid,
            balance_due=balance_due,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            grand_total=grand_total,
            
            # Payment info
            payment_status='pending' if balance_due > 0 else 'paid',
            payment_method=request.form.get('payment_method', 'cash'),
            payment_reference=request.form.get('payment_reference', ''),
            
            # Warranty info
            warranty_period=int(request.form.get('warranty_period', job.warranty_period or 0)),
            warranty_start=datetime.utcnow().date() if request.form.get('warranty_period', '0') != '0' else None,
            
            # Repair details
            issue_description=job.issue_description,
            work_done=job.repair_details or job.diagnosis_details or '',
            technician_notes=request.form.get('technician_notes', ''),
            
            created_by=current_user.id
        )
        
        # Calculate warranty end date
        if invoice.warranty_period > 0 and invoice.warranty_start:
            invoice.warranty_end = invoice.warranty_start + timedelta(days=30 * invoice.warranty_period)
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        
        # Add labor as an invoice item
        if labor_cost > 0:
            labor_item = RepairInvoiceItem(
                invoice_id=invoice.id,
                item_type='labor',
                description='Repair Labor Charges',
                quantity=1,
                unit_price=labor_cost,
                total=labor_cost,
                warranty_info='Covered under warranty' if invoice.warranty_period > 0 else 'No warranty'
            )
            db.session.add(labor_item)
        
        # Add parts as invoice items
        if job.repair_items:
            for repair_item in job.repair_items:
                part_item = RepairInvoiceItem(
                    invoice_id=invoice.id,
                    item_type='part',
                    description=f"{repair_item.product.name if repair_item.product else 'Replacement Part'}",
                    quantity=repair_item.quantity,
                    unit_price=repair_item.unit_price,
                    total=repair_item.total_price,
                    warranty_info=f"{invoice.warranty_period} months warranty" if invoice.warranty_period > 0 else 'No warranty',
                    notes=f"IMEI: {repair_item.stock_item.imei if repair_item.stock_item else 'N/A'}"
                )
                db.session.add(part_item)
        
        # Add any additional items
        additional_items = request.form.get('additional_items', '')
        if additional_items:
            items = additional_items.split('\n')
            for item_line in items:
                if item_line.strip():
                    parts = item_line.strip().split('|')
                    if len(parts) >= 3:
                        description = parts[0]
                        quantity = float(parts[1]) if parts[1] else 1
                        unit_price = float(parts[2]) if parts[2] else 0
                        total = quantity * unit_price
                        
                        additional_item = RepairInvoiceItem(
                            invoice_id=invoice.id,
                            item_type='other',
                            description=description,
                            quantity=quantity,
                            unit_price=unit_price,
                            total=total
                        )
                        db.session.add(additional_item)
                        invoice.total_cost += total
        
        # If advance payment was made, add as payment
        if advance_paid > 0:
            advance_payment = RepairPayment(
                invoice_id=invoice.id,
                amount=advance_paid,
                payment_method='advance',
                reference_number='Advance Payment',
                notes='Advance paid during device intake',
                received_by=current_user.id
            )
            db.session.add(advance_payment)
        
        # If full payment is made now, add payment record
        amount_paid_now = float(request.form.get('amount_paid_now', 0))
        if amount_paid_now > 0:
            current_payment = RepairPayment(
                invoice_id=invoice.id,
                amount=amount_paid_now,
                payment_method=invoice.payment_method,
                reference_number=invoice.payment_reference,
                notes='Payment during invoice creation',
                received_by=current_user.id
            )
            db.session.add(current_payment)
            
            # Update payment status
            total_paid = advance_paid + amount_paid_now
            if total_paid >= invoice.grand_total:
                invoice.payment_status = 'paid'
                invoice.balance_due = 0
            elif total_paid > 0:
                invoice.payment_status = 'partial'
                invoice.balance_due = invoice.grand_total - total_paid
        
        db.session.commit()
        
        flash(f'Repair invoice created successfully: {invoice_number}', 'success')
        
        # Mark job as delivered
        job.status = 'delivered'
        job.delivered_date = datetime.utcnow()
        db.session.commit()
        
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating invoice: {str(e)}', 'danger')
        return redirect(url_for('repair.job_detail', job_id=job_id))

@repair_bp.route('/repair-invoices')
@login_required
def repair_invoices_list():
    """List all repair invoices"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        status = request.args.get('status', 'all')
        search = request.args.get('search', '')
        
        query = RepairInvoice.query
        
        if status != 'all':
            query = query.filter_by(payment_status=status)
        
        if search:
            query = query.filter(
                db.or_(
                    RepairInvoice.invoice_number.contains(search),
                    RepairInvoice.customer_name.contains(search),
                    RepairInvoice.customer_phone.contains(search),
                    RepairInvoice.device_type.contains(search),
                    RepairInvoice.brand.contains(search),
                    RepairInvoice.model.contains(search)
                )
            )
        
        invoices = query.order_by(RepairInvoice.date.desc()).paginate(page=page, per_page=per_page)
        
        # Calculate statistics
        total_invoices = RepairInvoice.query.count()
        total_amount = db.session.query(db.func.sum(RepairInvoice.grand_total)).scalar() or 0
        pending_invoices = RepairInvoice.query.filter_by(payment_status='pending').count()
        paid_invoices = RepairInvoice.query.filter_by(payment_status='paid').count()
        
        return render_template('repair/invoices.html',
                             invoices=invoices,
                             total_invoices=total_invoices,
                             total_amount=total_amount,
                             pending_invoices=pending_invoices,
                             paid_invoices=paid_invoices,
                             title='Repair Invoices')
    except Exception as e:
        flash(f'Error loading invoices: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_dashboard'))

@repair_bp.route('/repair-invoice/<int:invoice_id>')
@login_required
def repair_invoice_detail(invoice_id):
    """View repair invoice details"""
    try:
        invoice = RepairInvoice.query.get_or_404(invoice_id)
        return render_template('repair/invoice_detail.html',
                             invoice=invoice,
                             title=f'Repair Invoice {invoice.invoice_number}')
    except Exception as e:
        flash(f'Error loading invoice: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_invoices_list'))

# @repair_bp.route('/repair-invoice/<int:invoice_id>/print')
# @login_required
# def print_repair_invoice(invoice_id):
#     """Print repair invoice"""
#     try:
#         invoice = RepairInvoice.query.get_or_404(invoice_id)
        
#         # Force print header
#         response = make_response(render_template('repair/print_invoice.html',
#                              invoice=invoice,
#                              title=f'Print Invoice {invoice.invoice_number}'))
        
#         # Add headers to disable caching
#         response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#         response.headers['Pragma'] = 'no-cache'
#         response.headers['Expires'] = '0'
        
#         return response
        
#     except Exception as e:
#         flash(f'Error printing invoice: {str(e)}', 'danger')
#         return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))

@repair_bp.route('/repair-invoice/<int:invoice_id>/add-payment', methods=['POST'])
@login_required
def add_repair_payment(invoice_id):
    """Add payment to repair invoice"""
    try:
        invoice = RepairInvoice.query.get_or_404(invoice_id)
        
        amount = float(request.form.get('amount', 0))
        payment_method = request.form.get('payment_method', 'cash')
        reference = request.form.get('reference_number', '')
        notes = request.form.get('notes', '')
        
        if amount <= 0:
            flash('Please enter a valid amount', 'danger')
            return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))
        
        # Create payment record
        payment = RepairPayment(
            invoice_id=invoice_id,
            amount=amount,
            payment_method=payment_method,
            reference_number=reference,
            notes=notes,
            received_by=current_user.id
        )
        
        db.session.add(payment)
        
        # Calculate total paid
        total_paid = db.session.query(db.func.sum(RepairPayment.amount)).filter(
            RepairPayment.invoice_id == invoice_id
        ).scalar() or 0
        
        # Update invoice payment status
        if total_paid >= invoice.grand_total:
            invoice.payment_status = 'paid'
            invoice.balance_due = 0
        elif total_paid > 0:
            invoice.payment_status = 'partial'
            invoice.balance_due = invoice.grand_total - total_paid
        
        db.session.commit()
        
        flash(f'Payment of Rs.{amount:.2f} added successfully', 'success')
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding payment: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))

@repair_bp.route('/repair-invoice/<int:invoice_id>/void', methods=['POST'])
@login_required
def void_repair_invoice(invoice_id):
    """Void a repair invoice (admin only)"""
    try:
        if current_user.role not in ['admin', 'manager']:
            flash('Permission denied', 'danger')
            return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))
        
        invoice = RepairInvoice.query.get_or_404(invoice_id)
        
        # Check if invoice is already paid
        if invoice.payment_status == 'paid':
            flash('Cannot void a paid invoice. Issue refund first.', 'danger')
            return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))
        
        # Mark as voided
        invoice.payment_status = 'voided'
        
        # Revert job status to completed
        if invoice.repair_job:
            invoice.repair_job.status = 'completed'
            invoice.repair_job.delivered_date = None
        
        db.session.commit()
        
        flash(f'Invoice {invoice.invoice_number} has been voided', 'success')
        return redirect(url_for('repair.repair_invoices_list'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error voiding invoice: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))

@repair_bp.route('/repair-invoice/<int:invoice_id>/email', methods=['POST'])
@login_required
def email_repair_invoice(invoice_id):
    """Email repair invoice to customer"""
    try:
        invoice = RepairInvoice.query.get_or_404(invoice_id)
        
        # TODO: Implement email sending logic
        flash(f'Invoice would be emailed to customer', 'info')
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))
        
    except Exception as e:
        flash(f'Error preparing email: {str(e)}', 'danger')
        return redirect(url_for('repair.repair_invoice_detail', invoice_id=invoice_id))