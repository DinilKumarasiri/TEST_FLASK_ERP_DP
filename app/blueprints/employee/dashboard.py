# app/blueprints/employee/dashboard.py
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import User, Attendance, LeaveRequest, Invoice, RepairJob, Commission
from datetime import datetime, date, timedelta
from . import employee_bp

@employee_bp.route('/dashboard')
@login_required
def employee_dashboard():
    """Employee dashboard - separate from index"""
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
    
    # Calculate performance metrics for each employee
    employee_performances = []
    current_month = date.today().month
    current_year = date.today().year
    month_start = date(current_year, current_month, 1)
    
    for employee in employees:
        # Calculate sales this month
        sales_amount = db.session.query(db.func.coalesce(db.func.sum(Invoice.total), 0)).filter(
            Invoice.created_by == employee.id,
            Invoice.date >= month_start
        ).scalar() or 0
        
        # Calculate repairs completed this month
        repairs_completed = RepairJob.query.filter(
            RepairJob.technician_id == employee.id,
            RepairJob.status == 'completed',
            RepairJob.completed_date >= month_start
        ).count()
        
        # Calculate attendance percentage for current month
        attendance_records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= month_start
        ).all()
        
        if attendance_records:
            present_days = len([r for r in attendance_records if r.status == 'present'])
            total_days = len(attendance_records)
            attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        else:
            attendance_percentage = 0
        
        # Calculate performance rating
        performance_score = 0
        performance_text = "Needs Improvement"
        badge_color = "danger"
        
        if attendance_percentage >= 90:
            performance_score += 30
        elif attendance_percentage >= 80:
            performance_score += 20
        elif attendance_percentage >= 70:
            performance_score += 10
        
        if sales_amount > 50000:
            performance_score += 40
        elif sales_amount > 25000:
            performance_score += 30
        elif sales_amount > 10000:
            performance_score += 20
        
        if repairs_completed > 20:
            performance_score += 30
        elif repairs_completed > 10:
            performance_score += 20
        elif repairs_completed > 5:
            performance_score += 10
        
        if performance_score >= 80:
            performance_text = "Excellent"
            badge_color = "success"
        elif performance_score >= 60:
            performance_text = "Good"
            badge_color = "info"
        elif performance_score >= 40:
            performance_text = "Average"
            badge_color = "warning"
        
        employee_performances.append({
            'employee': employee,
            'sales_amount': sales_amount,
            'repairs_completed': repairs_completed,
            'attendance_percentage': attendance_percentage,
            'performance_text': performance_text,
            'badge_color': badge_color
        })
    
    return render_template('employee/dashboard.html',
                         total_employees=total_employees,
                         active_employees=active_employees,
                         technicians=technicians,
                         today_attendance=today_attendance,
                         pending_leaves=pending_leaves,
                         employee_performances=employee_performances,
                         title='Employee Dashboard')

@employee_bp.route('/roles')
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