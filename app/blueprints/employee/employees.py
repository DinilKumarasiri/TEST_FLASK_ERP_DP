from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ... import db
from ...models import User, Attendance, LeaveRequest, Commission
from datetime import datetime, date
from .forms import EmployeeForm
from . import employee_bp

@employee_bp.route('/employees')
@login_required
def employee_list():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    employees = query.order_by(User.username).all()
    
    return render_template('employee/list.html',
                         employees=employees,
                         title='Employee List')

@employee_bp.route('/employee/<int:employee_id>')
@login_required
def employee_detail(employee_id):
    if current_user.role not in ['admin', 'manager'] and current_user.id != employee_id:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    
    # Get attendance for current month
    month_start = date(date.today().year, date.today().month, 1)
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= month_start
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate attendance statistics
    present_days = len([r for r in attendance_records if r.status == 'present'])
    absent_days = len([r for r in attendance_records if r.status == 'absent'])
    leave_days = len([r for r in attendance_records if r.status == 'leave'])
    
    # Get leave requests
    leave_requests = LeaveRequest.query.filter_by(
        employee_id=employee_id
    ).order_by(LeaveRequest.created_at.desc()).all()
    
    # Get commissions
    commissions = Commission.query.filter_by(
        employee_id=employee_id
    ).order_by(Commission.created_at.desc()).limit(10).all()
    
    # Calculate total commission
    total_commission = sum(commission.commission_amount for commission in commissions if commission.status == 'paid')
    
    return render_template('employee/detail.html',
                         employee=employee,
                         attendance_records=attendance_records,
                         present_days=present_days,
                         absent_days=absent_days,
                         leave_days=leave_days,
                         leave_requests=leave_requests,
                         commissions=commissions,
                         total_commission=total_commission,
                         title=f'Employee - {employee.username}')

@employee_bp.route('/create-employee', methods=['GET', 'POST'])
@login_required
def create_employee():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    form = EmployeeForm()
    
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            db.or_(User.username == form.username.data, User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('employee/create.html', form=form, title='Create Employee')
        
        employee = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
            is_active=form.is_active.data
        )
        employee.set_password(form.password.data)
        
        db.session.add(employee)
        db.session.commit()
        
        flash(f'Employee {employee.username} created successfully', 'success')
        return redirect(url_for('employee.employee_list'))
    
    return render_template('employee/create.html', form=form, title='Create Employee')

@employee_bp.route('/edit-employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    form = EmployeeForm(obj=employee)
    
    if form.validate_on_submit():
        # Check if username or email already exists (excluding current employee)
        existing_user = User.query.filter(
            db.or_(User.username == form.username.data, User.email == form.email.data),
            User.id != employee_id
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('employee/edit.html', form=form, employee=employee, title='Edit Employee')
        
        employee.username = form.username.data
        employee.email = form.email.data
        employee.role = form.role.data
        employee.is_active = form.is_active.data
        
        if form.password.data:
            employee.set_password(form.password.data)
        
        db.session.commit()
        
        flash(f'Employee {employee.username} updated successfully', 'success')
        return redirect(url_for('employee.employee_list'))
    
    return render_template('employee/edit.html', form=form, employee=employee, title='Edit Employee')

@employee_bp.route('/delete-employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    
    # Don't allow deleting yourself
    if employee.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('employee.employee_list'))
    
    # Soft delete by deactivating
    employee.is_active = False
    db.session.commit()
    
    flash(f'Employee {employee.username} has been deactivated', 'success')
    return redirect(url_for('employee.employee_list'))
