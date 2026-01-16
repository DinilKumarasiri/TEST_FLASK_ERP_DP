from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import Commission, User
from datetime import datetime, date, timedelta
from . import employee_bp

@employee_bp.route('/commissions')
@login_required
def commissions():
    if current_user.role != 'admin':
        # Employees can only see their own commissions
        commissions = Commission.query.filter_by(employee_id=current_user.id).order_by(Commission.created_at.desc()).all()
    else:
        employee_id = request.args.get('employee_id', type=int)
        status = request.args.get('status', 'all')
        
        query = Commission.query
        
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        
        if status != 'all':
            query = query.filter_by(status=status)
        
        commissions = query.order_by(Commission.created_at.desc()).all()
    
    employees = User.query.filter_by(is_active=True).all()
    
    # Calculate totals
    total_pending = sum(c.commission_amount for c in commissions if c.status == 'pending')
    total_paid = sum(c.commission_amount for c in commissions if c.status == 'paid')
    
    return render_template('employee/commissions.html',
                         commissions=commissions,
                         employees=employees,
                         total_pending=total_pending,
                         total_paid=total_paid,
                         title='Commissions')

@employee_bp.route('/calculate-commission', methods=['POST'])
@login_required
def calculate_commission():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee_id = request.form.get('employee_id', type=int)
    month_str = request.form.get('month', date.today().strftime('%Y-%m'))
    
    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
    except:
        start_date = date(date.today().year, date.today().month, 1)
        end_date = date.today()
    
    # Get employee's sales for the month
    # This would need to be implemented based on your commission structure
    # For now, we'll just show a placeholder
    
    flash('Commission calculation would be implemented based on your business rules', 'info')
    return redirect(url_for('employee.commissions'))

@employee_bp.route('/pay-commission/<int:commission_id>', methods=['POST'])
@login_required
def pay_commission(commission_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    commission = Commission.query.get_or_404(commission_id)
    
    if commission.status == 'pending':
        commission.status = 'paid'
        commission.payment_date = datetime.utcnow()
        db.session.commit()
        flash('Commission marked as paid', 'success')
    
    return redirect(url_for('employee.commissions'))

@employee_bp.route('/commission-details/<int:commission_id>')
@login_required
def commission_details(commission_id):
    commission = Commission.query.get_or_404(commission_id)
    
    # Check permission
    if current_user.role != 'admin' and current_user.id != commission.employee_id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    # Render details HTML
    html = f"""
    <div class="commission-details">
        <div class="row">
            <div class="col-md-6">
                <h6>Commission Information</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Commission ID:</th>
                        <td>#{commission.id}</td>
                    </tr>
                    <tr>
                        <th>Employee:</th>
                        <td>{commission.employee.username} ({commission.employee.role})</td>
                    </tr>
                    <tr>
                        <th>Status:</th>
                        <td>
                            <span class="badge bg-{'success' if commission.status == 'paid' else 'warning'}">
                                {commission.status.title()}
                            </span>
                        </td>
                    </tr>
                    <tr>
                        <th>Created:</th>
                        <td>{commission.created_at.strftime('%Y-%m-%d %H:%M')}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>Financial Details</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Sale Amount:</th>
                        <td>Rs.{commission.sale_amount:.2f}</td>
                    </tr>
                    <tr>
                        <th>Commission Rate:</th>
                        <td>{commission.commission_rate}%</td>
                    </tr>
                    <tr>
                        <th>Commission Amount:</th>
                        <td><strong>Rs.{commission.commission_amount:.2f}</strong></td>
                    </tr>
                    <tr>
                        <th>Payment Date:</th>
                        <td>{commission.payment_date.strftime('%Y-%m-%d') if commission.payment_date else 'Not Paid'}</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="row mt-3">
            <div class="col-12">
                <h6>Source Information</h6>
                <table class="table table-sm">
                    <tr>
                        <th>Source Type:</th>
                        <td>
                            {'Sale' if commission.invoice_id else 'Repair' if commission.repair_job_id else 'Other'}
                        </td>
                    </tr>
                    <tr>
                        <th>Reference:</th>
                        <td>
                            {commission.invoice.invoice_number if commission.invoice else 
                             commission.repair_job.job_number if commission.repair_job else 'N/A'}
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="mt-3">
            <h6>Notes</h6>
            <p class="text-muted">{commission.notes or 'No notes available'}</p>
        </div>
    </div>
    """
    
    return jsonify({'success': True, 'html': html})
