from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from modules.models import User, Attendance, LeaveRequest, Commission
from datetime import datetime, date, timedelta
from modules.forms import EmployeeForm, AttendanceForm, LeaveRequestForm

employee_bp = Blueprint('employee', __name__)

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
    
    return render_template('employee/dashboard.html',
                         total_employees=total_employees,
                         active_employees=active_employees,
                         technicians=technicians,
                         today_attendance=today_attendance,
                         pending_leaves=pending_leaves,
                         title='Employee Dashboard')

@employee_bp.route('/employees')
@login_required
def employee_list():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employees = User.query.order_by(User.username).all()
    return render_template('employee/list.html',
                         employees=employees,
                         title='Employees')

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
    
    # Get leave requests
    leave_requests = LeaveRequest.query.filter_by(
        employee_id=employee_id
    ).order_by(LeaveRequest.created_at.desc()).all()
    
    # Get commissions
    commissions = Commission.query.filter_by(
        employee_id=employee_id
    ).order_by(Commission.created_at.desc()).limit(10).all()
    
    return render_template('employee/detail.html',
                         employee=employee,
                         attendance_records=attendance_records,
                         leave_requests=leave_requests,
                         commissions=commissions,
                         title=employee.username)

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

@employee_bp.route('/attendance')
@login_required
def attendance():
    if current_user.role not in ['admin', 'manager']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        selected_date = date.today()
    
    attendance_records = Attendance.query.filter_by(date=selected_date).all()
    
    # Get all active employees
    employees = User.query.filter_by(is_active=True).all()
    
    # Create dictionary for easy lookup
    attendance_dict = {record.employee_id: record for record in attendance_records}
    
    return render_template('employee/attendance.html',
                         selected_date=selected_date,
                         employees=employees,
                         attendance_dict=attendance_dict,
                         title='Attendance')

@employee_bp.route('/mark-attendance', methods=['POST'])
@login_required
def mark_attendance():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    employee_id = data.get('employee_id')
    action = data.get('action')  # 'check_in' or 'check_out'
    date_str = data.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        selected_date = date.today()
    
    # Find existing attendance record
    attendance = Attendance.query.filter_by(
        employee_id=employee_id,
        date=selected_date
    ).first()
    
    current_time = datetime.utcnow()
    
    if not attendance:
        attendance = Attendance(
            employee_id=employee_id,
            date=selected_date,
            status='present'
        )
    
    if action == 'check_in':
        attendance.check_in = current_time
    elif action == 'check_out':
        attendance.check_out = current_time
        
        # Calculate total hours
        if attendance.check_in:
            time_diff = current_time - attendance.check_in
            attendance.total_hours = time_diff.total_seconds() / 3600  # Convert to hours
    
    db.session.add(attendance)
    db.session.commit()
    
    return jsonify({'success': True})

@employee_bp.route('/attendance-report')
@login_required
def attendance_report():
    if current_user.role not in (['admin', 'manager']):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    month_str = request.args.get('month', date.today().strftime('%Y-%m'))
    
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
    
    # Get all employees
    employees = User.query.filter_by(is_active=True).all()
    
    # Get attendance data for the month
    attendance_data = []
    
    for employee in employees:
        records = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).all()
        
        # Calculate statistics
        present_days = len([r for r in records if r.status == 'present'])
        absent_days = len([r for r in records if r.status == 'absent'])
        leave_days = len([r for r in records if r.status == 'leave'])
        total_hours = sum(r.total_hours or 0 for r in records)
        
        attendance_data.append({
            'employee': employee,
            'present_days': present_days,
            'absent_days': absent_days,
            'leave_days': leave_days,
            'total_hours': total_hours,
            'records': records
        })
    
    return render_template('employee/attendance_report.html',
                         attendance_data=attendance_data,
                         start_date=start_date,
                         end_date=end_date,
                         title='Attendance Report')

@employee_bp.route('/leave-requests')
@login_required
def leave_requests():
    if current_user.role not in ['admin', 'manager']:
        # Employees can only see their own leave requests
        requests = LeaveRequest.query.filter_by(employee_id=current_user.id).all()
    else:
        status = request.args.get('status', 'pending')
        
        if status == 'all':
            requests = LeaveRequest.query.all()
        else:
            requests = LeaveRequest.query.filter_by(status=status).all()
    
    return render_template('employee/leave_requests.html',
                         requests=requests,
                         title='Leave Requests')

@employee_bp.route('/apply-leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    form = LeaveRequestForm()
    
    if form.validate_on_submit():
        leave_request = LeaveRequest(
            employee_id=current_user.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
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
    if current_user.role not in ['admin', 'manager']:
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

@employee_bp.route('/commissions')
@login_required
def commissions():
    if current_user.role != 'admin':
        # Employees can only see their own commissions
        commissions = Commission.query.filter_by(employee_id=current_user.id).all()
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
    
    return render_template('employee/commissions.html',
                         commissions=commissions,
                         employees=employees,
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

@employee_bp.route('/user-roles')
@login_required
def user_roles():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employees = User.query.all()
    
    # Define available roles and their permissions
    roles_permissions = {
        'admin': ['Full system access'],
        'manager': ['Manage employees', 'View reports', 'Approve leave'],
        'staff': ['POS access', 'View inventory'],
        'technician': ['Repair management', 'View assigned jobs']
    }
    
    return render_template('employee/user_roles.html',
                         employees=employees,
                         roles_permissions=roles_permissions,
                         title='User Roles & Permissions')