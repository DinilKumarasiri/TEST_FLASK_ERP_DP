# app/blueprints/employee/employees.py
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
from ... import db
from ...models import User, EmployeeProfile, Attendance, LeaveRequest, Commission, Invoice, RepairJob
from datetime import datetime, date
from .forms import EmployeeForm, EditEmployeeForm
from . import employee_bp

@employee_bp.route('/')
@login_required
def index():
    """Main employee dashboard"""
    return redirect(url_for('employee.employee_list'))

@employee_bp.route('/list')
@login_required
def employee_list():  # KEEP THIS NAME
    if current_user.role not in ['admin', 'staff']:
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
    
    # Get profiles for each employee
    employee_data = []
    for emp in employees:
        try:
            profile = EmployeeProfile.query.filter_by(user_id=emp.id).first()
            employee_data.append({
                'user': emp,
                'profile': profile
            })
        except Exception as e:
            print(f"Error loading profile for employee {emp.id}: {e}")
            employee_data.append({
                'user': emp,
                'profile': None
            })
    
    return render_template('employee/list.html',
                         employees=employee_data,
                         title='Employee List')

@employee_bp.route('/<int:employee_id>')
@login_required
def employee_detail(employee_id):
    if current_user.role not in ['admin', 'staff'] and current_user.id != employee_id:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    employee_profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
    
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
                         employee_profile=employee_profile,
                         attendance_records=attendance_records,
                         present_days=present_days,
                         absent_days=absent_days,
                         leave_days=leave_days,
                         leave_requests=leave_requests,
                         commissions=commissions,
                         total_commission=total_commission,
                         title=f'Employee - {employee.username}')

@employee_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_employee():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    form = EmployeeForm()
    
    managers = User.query.filter(User.role.in_(['admin', 'staff']), User.is_active == True).all()
    form.reporting_manager_id.choices = [(0, 'None')] + [(m.id, f"{m.username} ({m.role})") for m in managers]
    
    if form.validate_on_submit():
        existing_user = User.query.filter(
            db.or_(User.username == form.username.data, User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('employee/create.html', form=form, title='Create Employee')
        
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                role=form.role.data,
                is_active=form.is_active.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.flush()
            
            employee_code = form.employee_code.data
            if not employee_code:
                employee_code = f"EMP{user.id:04d}"
            
            profile = EmployeeProfile(
                user_id=user.id,
                full_name=form.full_name.data,
                date_of_birth=form.date_of_birth.data,
                gender=form.gender.data,
                personal_phone=form.personal_phone.data,
                personal_email=form.personal_email.data,
                emergency_contact=form.emergency_contact.data,
                emergency_phone=form.emergency_phone.data,
                address=form.address.data,
                aadhar_number=form.aadhar_number.data,
                pan_number=form.pan_number.data,
                employee_code=employee_code,
                job_title=form.job_title.data,
                department=form.department.data,
                employment_type=form.employment_type.data,
                date_of_joining=form.date_of_joining.data,
                probation_end_date=form.probation_end_date.data,
                work_location=form.work_location.data,
                shift_timing=form.shift_timing.data,
                reporting_manager_id=form.reporting_manager_id.data if form.reporting_manager_id.data != 0 else None,
                basic_salary=form.basic_salary.data or 0.0,
                commission_rate=form.commission_rate.data or 0.0,
                bank_name=form.bank_name.data,
                account_number=form.account_number.data,
                ifsc_code=form.ifsc_code.data,
                education=form.education.data,
                certifications=form.certifications.data,
                skills=form.skills.data,
                experience_years=form.experience_years.data,
                sales_target_monthly=form.sales_target_monthly.data or 0.0
            )
            
            db.session.add(profile)
            db.session.commit()
            
            flash(f'Employee {user.username} created successfully', 'success')
            return redirect(url_for('employee.employee_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating employee: {str(e)}', 'danger')
    
    return render_template('employee/create.html', form=form, title='Create Employee')

@employee_bp.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
    
    if not profile:
        profile = EmployeeProfile(user_id=employee_id, full_name=employee.username)
        db.session.add(profile)
        db.session.commit()
    
    form = EditEmployeeForm(obj=profile)
    
    managers = User.query.filter(User.role.in_(['admin', 'staff']), User.is_active == True, User.id != employee_id).all()
    form.reporting_manager_id.choices = [(0, 'None')] + [(m.id, f"{m.username} ({m.role})") for m in managers]
    
    if request.method == 'GET':
        form.username.data = employee.username
        form.email.data = employee.email
        form.role.data = employee.role
        form.is_active.data = employee.is_active
        form.reporting_manager_id.data = profile.reporting_manager_id or 0
    
    if form.validate_on_submit():
        try:
            existing_user = User.query.filter(
                db.or_(User.username == form.username.data, User.email == form.email.data),
                User.id != employee_id
            ).first()
            
            if existing_user:
                flash('Username or email already exists', 'danger')
                return render_template('employee/edit.html', form=form, employee=employee, profile=profile, title='Edit Employee')
            
            employee.username = form.username.data
            employee.email = form.email.data
            employee.role = form.role.data
            employee.is_active = form.is_active.data
            
            if form.password.data:
                employee.set_password(form.password.data)
            
            profile.full_name = form.full_name.data
            profile.date_of_birth = form.date_of_birth.data
            profile.gender = form.gender.data
            profile.personal_phone = form.personal_phone.data
            profile.personal_email = form.personal_email.data
            profile.emergency_contact = form.emergency_contact.data
            profile.emergency_phone = form.emergency_phone.data
            profile.address = form.address.data
            profile.aadhar_number = form.aadhar_number.data
            profile.pan_number = form.pan_number.data
            
            if not profile.employee_code and form.employee_code.data:
                profile.employee_code = form.employee_code.data
            
            profile.job_title = form.job_title.data
            profile.department = form.department.data
            profile.employment_type = form.employment_type.data
            profile.date_of_joining = form.date_of_joining.data
            profile.probation_end_date = form.probation_end_date.data
            profile.work_location = form.work_location.data
            profile.shift_timing = form.shift_timing.data
            profile.reporting_manager_id = form.reporting_manager_id.data if form.reporting_manager_id.data != 0 else None
            
            profile.basic_salary = form.basic_salary.data or 0.0
            profile.commission_rate = form.commission_rate.data or 0.0
            profile.bank_name = form.bank_name.data
            profile.account_number = form.account_number.data
            profile.ifsc_code = form.ifsc_code.data
            
            profile.education = form.education.data
            profile.certifications = form.certifications.data
            profile.skills = form.skills.data
            profile.experience_years = form.experience_years.data
            profile.sales_target_monthly = form.sales_target_monthly.data or 0.0
            
            db.session.commit()
            
            flash(f'Employee {employee.username} updated successfully', 'success')
            return redirect(url_for('employee.employee_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'danger')
    
    return render_template('employee/edit.html', form=form, employee=employee, profile=profile, title='Edit Employee')

@employee_bp.route('/delete-employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    """Delete employee with password verification"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'})
    
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({'success': False, 'message': 'Admin password is required'})
    
    # Verify admin password
    if not check_password_hash(current_user.password_hash, password):
        return jsonify({'success': False, 'message': 'Invalid admin password'})
    
    employee = User.query.get_or_404(employee_id)
    
    # Don't allow deleting yourself
    if employee.id == current_user.id:
        return jsonify({'success': False, 'message': 'You cannot delete your own account'})
    
    try:
        # Store employee info for logging
        employee_name = employee.username
        
        # Check if employee has created any records that should be reassigned
        # For invoices created by this employee
        invoices_created = Invoice.query.filter_by(created_by=employee_id).all()
        if invoices_created:
            # Reassign to current admin or set to NULL
            for invoice in invoices_created:
                invoice.created_by = None
        
        # For repair jobs created by this employee
        repair_jobs_created = RepairJob.query.filter_by(created_by=employee_id).all()
        if repair_jobs_created:
            for job in repair_jobs_created:
                job.created_by = None
        
        # For repair jobs assigned to this employee as technician
        repair_jobs_assigned = RepairJob.query.filter_by(technician_id=employee_id).all()
        if repair_jobs_assigned:
            for job in repair_jobs_assigned:
                job.technician_id = None
        
        # Delete related records
        Attendance.query.filter_by(employee_id=employee_id).delete()
        LeaveRequest.query.filter_by(employee_id=employee_id).delete()
        LeaveRequest.query.filter_by(approved_by=employee_id).update({'approved_by': None})
        Commission.query.filter_by(employee_id=employee_id).delete()
        
        # Delete employee profile
        EmployeeProfile.query.filter_by(user_id=employee_id).delete()
        
        # Finally delete the user
        db.session.delete(employee)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Employee {employee_name} has been permanently deleted'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting employee: {str(e)}'})

@employee_bp.route('/deactivate/<int:employee_id>', methods=['POST'])
@login_required
def deactivate_employee(employee_id):
    """Soft delete - deactivate employee"""
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    
    # Don't allow deactivating yourself
    if employee.id == current_user.id:
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('employee.employee_list'))
    
    try:
        employee.is_active = False
        
        profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
        if profile:
            profile.is_active = False
        
        db.session.commit()
        
        flash(f'Employee {employee.username} has been deactivated', 'success')
        return jsonify({'success': True, 'message': f'Employee {employee.username} has been deactivated'})
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deactivating employee: {str(e)}', 'danger')
        return jsonify({'success': False, 'message': str(e)})

@employee_bp.route('/reactivate/<int:employee_id>', methods=['POST'])
@login_required
def reactivate_employee(employee_id):
    """Reactivate employee"""
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    
    try:
        employee.is_active = True
        
        profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
        if profile:
            profile.is_active = True
        
        db.session.commit()
        
        flash(f'Employee {employee.username} has been reactivated', 'success')
        return jsonify({'success': True, 'message': f'Employee {employee.username} has been reactivated'})
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error reactivating employee: {str(e)}', 'danger')
        return jsonify({'success': False, 'message': str(e)})