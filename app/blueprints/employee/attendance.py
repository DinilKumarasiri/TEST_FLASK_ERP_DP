from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from ... import db
from ...models import User, Attendance
from datetime import datetime, date, timedelta
from . import employee_bp

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
    
    # Create list of all employees with their attendance status
    employee_attendance = []
    for employee in employees:
        record = attendance_dict.get(employee.id)
        employee_attendance.append({
            'employee': employee,
            'record': record
        })
    
    return render_template('employee/attendance.html',
                         selected_date=selected_date,
                         employee_attendance=employee_attendance,
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

@employee_bp.route('/update-attendance', methods=['POST'])
@login_required
def update_attendance():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    attendance_id = data.get('attendance_id')
    employee_id = data.get('employee_id')
    date_str = data.get('date')
    status = data.get('status')
    check_in_str = data.get('check_in')
    check_out_str = data.get('check_out')
    notes = data.get('notes')
    
    # If we have attendance_id, edit existing record
    if attendance_id:
        attendance = Attendance.query.get_or_404(attendance_id)
        
        # Check permission
        if current_user.role not in ['admin', 'manager'] and current_user.id != attendance.employee_id:
            return jsonify({'success': False, 'message': 'Access denied'})
    else:
        # Create new record
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = date.today()
        
        # Find or create attendance record
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=selected_date
        ).first()
        
        if not attendance:
            attendance = Attendance(
                employee_id=employee_id,
                date=selected_date,
                status=status
            )
    
    # Update fields
    if status:
        attendance.status = status
    if notes is not None:
        attendance.notes = notes
    
    if check_in_str:
        try:
            check_in_time = datetime.strptime(check_in_str, '%H:%M').time()
            selected_date = attendance.date if hasattr(attendance, 'date') else selected_date
            attendance.check_in = datetime.combine(selected_date, check_in_time)
        except:
            pass
    
    if check_out_str:
        try:
            check_out_time = datetime.strptime(check_out_str, '%H:%M').time()
            selected_date = attendance.date if hasattr(attendance, 'date') else selected_date
            attendance.check_out = datetime.combine(selected_date, check_out_time)
        except:
            pass
    
    # Calculate total hours if both check in and check out are set
    if attendance.check_in and attendance.check_out:
        time_diff = attendance.check_out - attendance.check_in
        attendance.total_hours = time_diff.total_seconds() / 3600
    
    db.session.add(attendance)
    db.session.commit()
    
    return jsonify({'success': True})

@employee_bp.route('/attendance-report')
@login_required
def attendance_report():
    if current_user.role not in ['admin', 'manager']:
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
                         month_str=month_str,
                         title='Attendance Report')

@employee_bp.route('/attendance-history')
@login_required
def attendance_history():
    employee_id = request.args.get('employee_id', current_user.id)
    
    # Check permission
    if current_user.role not in ['admin', 'manager'] and current_user.id != int(employee_id):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    employee = User.query.get_or_404(employee_id)
    
    # Get date range
    start_date_str = request.args.get('start_date', (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except:
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
    
    # Get attendance records
    attendance_records = Attendance.query.filter(
        Attendance.employee_id == employee_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date.desc()).all()
    
    # Calculate statistics
    total_days = (end_date - start_date).days + 1
    present_days = len([r for r in attendance_records if r.status == 'present'])
    absent_days = len([r for r in attendance_records if r.status == 'absent'])
    leave_days = len([r for r in attendance_records if r.status == 'leave'])
    
    return render_template('employee/attendance_history.html',
                         employee=employee,
                         attendance_records=attendance_records,
                         start_date=start_date,
                         end_date=end_date,
                         total_days=total_days,
                         present_days=present_days,
                         absent_days=absent_days,
                         leave_days=leave_days,
                         title=f'Attendance History - {employee.username}')
