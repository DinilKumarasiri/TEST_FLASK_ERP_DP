from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import Invoice
from . import pos_bp

@pos_bp.route('/invoice/<int:invoice_id>/receipt')
@login_required
def invoice_receipt(invoice_id):
    """Generate receipt for invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verify the invoice belongs to current user or has permission
    if invoice.created_by != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to view this receipt', 'error')
        return redirect(url_for('pos.pos_home'))
    
    return render_template('pos/receipt.html',
                         invoice=invoice,
                         title=f'Receipt {invoice.invoice_number}')

@pos_bp.route('/invoice/<int:invoice_id>/print')
@login_required
def print_receipt(invoice_id):
    """Print receipt for invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verify permission
    if invoice.created_by != current_user.id and current_user.role != 'admin':
        flash('You do not have permission to print this receipt', 'error')
        return redirect(url_for('pos.pos_home'))
    
    return render_template('pos/print_receipt.html',
                         invoice=invoice,
                         title=f'Print Receipt {invoice.invoice_number}')

@pos_bp.route('/invoices')
@login_required
def invoices_list():
    """List all invoices"""
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
def invoice_detail(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('pos/invoice_detail.html',
                         invoice=invoice,
                         title=f'Invoice {invoice.invoice_number}')
