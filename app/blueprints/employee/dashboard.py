from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import User, Attendance, LeaveRequest
from datetime import datetime, date
from . import employee_bp

@employee_bp.route('/')
@login_required
def employee_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    total_employees = User.query.count()
    active_employees = User.query.filter_by(is_active=True).count()
    technicians = User.query.filter_by(role='technician', is_active=True).count()
    
    # Today's attendance
    today_attendance = Attendance.query.filter(
        db.func.date(Attendance.date) == date.today()
    ).all()
    
    # Pending leave requests
    pending_leaves = LeaveRequest.query.filter_by(
        status='pending'
    ).count()
    
    # Get all active employees for the performance table
    employees = User.query.filter_by(is_active=True).all()
    
    return render_template('employee/dashboard.html',
                         total_employees=total_employees,
                         active_employees=active_employees,
                         technicians=technicians,
                         today_attendance=today_attendance,
                         pending_leaves=pending_leaves,
                         employees=employees,
                         title='Employee Dashboard')

@employee_bp.route('/user-roles')
@login_required
def user_roles():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employees = User.query.all()
    
    # Define available roles and their permissions
    roles_permissions = {
        'admin': ['Full system access', 'Manage all users', 'View all reports', 'System configuration'],
        'manager': ['Manage employees', 'View reports', 'Approve leave', 'Manage inventory', 'Process sales'],
        'staff': ['POS access', 'View inventory', 'Process sales', 'Customer management'],
        'technician': ['Repair management', 'View assigned jobs', 'Update repair status', 'Spare parts management']
    }
    
    return render_template('employee/user_roles.html',
                         employees=employees,
                         roles_permissions=roles_permissions,
                         title='User Roles & Permissions')

@employee_bp.route('/my-profile')
@login_required
def my_profile():
    # Redirect to employee detail page for current user
    return redirect(url_for('employee.employee_detail', employee_id=current_user.id))
