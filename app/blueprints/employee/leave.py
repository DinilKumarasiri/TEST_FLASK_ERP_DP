from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import LeaveRequest, Attendance
from datetime import datetime, timedelta
from .forms import LeaveRequestForm
from . import employee_bp

@employee_bp.route('/leave-requests')
@login_required
def leave_requests():
    status = request.args.get('status', 'pending')
    
    # Changed from: if current_user.role not in ['admin', 'manager']:
    if current_user.role not in ['admin', 'staff']:  # Updated
        # Employees can only see their own leave requests
        query = LeaveRequest.query.filter_by(employee_id=current_user.id)
    else:
        query = LeaveRequest.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Add eager loading to avoid N+1 queries
    requests = query.order_by(LeaveRequest.created_at.desc()).all()
    
    # Calculate counts for the template
    pending_count = len([r for r in requests if r.status == 'pending'])
    approved_count = len([r for r in requests if r.status == 'approved'])
    rejected_count = len([r for r in requests if r.status == 'rejected'])
    
    return render_template('employee/leave_requests.html',
                         requests=requests,
                         pending_count=pending_count,
                         approved_count=approved_count,
                         rejected_count=rejected_count,
                         title='Leave Requests')

@employee_bp.route('/apply-leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        # Calculate number of days
        days_requested = (form.end_date.data - form.start_date.data).days + 1
        
        leave_request = LeaveRequest(
            employee_id=current_user.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            days_requested=days_requested,
            reason=form.reason.data
        )
        
        db.session.add(leave_request)
        db.session.commit()
        
        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('employee.leave_requests'))
    
    return render_template('employee/apply_leave.html', form=form, title='Apply for Leave')

@employee_bp.route('/approve-leave/<int:leave_id>', methods=['POST'])
@login_required
def approve_leave(leave_id):
    # Changed from: if current_user.role not in ['admin', 'manager']:
    if current_user.role not in ['admin', 'staff']:  # Updated
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    leave_request = LeaveRequest.query.get_or_404(leave_id)
    action = request.form.get('action')  # 'approve' or 'reject'
    
    if action == 'approve':
        leave_request.status = 'approved'
        leave_request.approved_by = current_user.id
        leave_request.approved_date = datetime.utcnow()
        
        # Create attendance records for leave days
        current_date = leave_request.start_date
        while current_date <= leave_request.end_date:
            attendance = Attendance.query.filter_by(
                employee_id=leave_request.employee_id,
                date=current_date
            ).first()
            
            if not attendance:
                attendance = Attendance(
                    employee_id=leave_request.employee_id,
                    date=current_date,
                    status='leave'
                )
                db.session.add(attendance)
            
            current_date += timedelta(days=1)
        
        flash('Leave request approved', 'success')
    elif action == 'reject':
        leave_request.status = 'rejected'
        leave_request.approved_by = current_user.id
        leave_request.approved_date = datetime.utcnow()
        flash('Leave request rejected', 'warning')
    
    db.session.commit()
    return redirect(url_for('employee.leave_requests'))