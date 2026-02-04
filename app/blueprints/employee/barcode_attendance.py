# app/blueprints/employee/barcode_attendance.py
from flask import render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from ... import db
from ...models.user import User
from ...models.employee import EmployeeProfile, Attendance, AttendanceLog
from datetime import datetime, date, timedelta
import pytz
import json
from . import employee_bp

# Sri Lanka timezone
SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

def get_sri_lanka_time():
    """Get current time in Sri Lanka"""
    return datetime.now(SRI_LANKA_TZ)

def get_sri_lanka_date():
    """Get current date in Sri Lanka"""
    return get_sri_lanka_time().date()

@employee_bp.route('/barcode-attendance')
@login_required
def barcode_attendance_interface():
    """Admin interface for barcode scanning attendance"""
    if current_user.role not in ['admin', 'staff']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get Sri Lanka date for display
    today_sl = get_sri_lanka_date()
    
    return render_template('employee/barcode_attendance.html',
                         today_sl=today_sl,
                         title='Barcode Attendance Scanner')


@employee_bp.route('/api/barcode-scan', methods=['POST'])
@login_required
def process_barcode_scan():
    """API endpoint to process barcode scans from physical scanner"""
    if current_user.role not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode:
            return jsonify({'success': False, 'message': 'No barcode provided'})
        
        # Find employee by barcode
        employee_profile = EmployeeProfile.query.filter_by(
            employee_barcode=barcode
        ).first()
        
        if not employee_profile:
            # Try alternative barcode formats
            employee_profile = EmployeeProfile.query.filter(
                (EmployeeProfile.employee_code == barcode) |
                (EmployeeProfile.user.has(User.username == barcode))
            ).first()
        
        if not employee_profile:
            return jsonify({
                'success': False,
                'message': f'Employee not found for barcode: {barcode}',
                'sound': 'error'
            })
        
        employee = employee_profile.user
        
        if not employee.is_active:
            return jsonify({
                'success': False,
                'message': f'Employee {employee.username} is inactive',
                'sound': 'warning'
            })
        
        # Use Sri Lanka time
        today_sl = get_sri_lanka_date()
        now_sl = get_sri_lanka_time()
        
        # Get today's attendance record
        attendance = Attendance.query.filter_by(
            employee_id=employee.id,
            date=today_sl
        ).first()
        
        # Determine if this should be check-in or check-out
        # Logic based on Sri Lanka business hours
        scan_type = 'check_in'
        current_hour = now_sl.hour
        
        if attendance:
            if attendance.check_in and not attendance.check_out:
                # If checked in but not out, and it's after 12:00 PM, check out
                if current_hour >= 12:
                    scan_type = 'check_out'
                else:
                    scan_type = 'check_in'  # Allow re-check in before noon
            elif attendance.check_in and attendance.check_out:
                # Both already recorded
                if current_hour < 12:
                    scan_type = 'check_in'  # New day check-in
                else:
                    scan_type = 'check_out'  # Corrections
        
        # Create or update attendance record
        if not attendance:
            attendance = Attendance(
                employee_id=employee.id,
                date=today_sl,
                status='present'
            )
        
        if scan_type == 'check_in':
            attendance.check_in = now_sl
            message = f'Checked in: {employee.username} at {now_sl.strftime("%H:%M")}'
        else:
            attendance.check_out = now_sl
            # Calculate total hours
            if attendance.check_in:
                time_diff = now_sl - attendance.check_in
                attendance.total_hours = time_diff.total_seconds() / 3600
            message = f'Checked out: {employee.username} at {now_sl.strftime("%H:%M")}'
        
        # Log the barcode scan with Sri Lanka time
        attendance_log = AttendanceLog(
            employee_id=employee.id,
            scan_type=scan_type,
            scan_time=now_sl,
            barcode_used=barcode,
            location=request.remote_addr
        )
        
        # Update scan count
        employee_profile.increment_scan_count()
        
        # Save to database
        db.session.add(attendance)
        db.session.add(attendance_log)
        db.session.commit()
        
        # Return success response
        return jsonify({
            'success': True,
            'message': message,
            'employee': {
                'id': employee.id,
                'username': employee.username,
                'full_name': employee_profile.full_name,
                'role': employee.role
            },
            'scan_type': scan_type,
            'time': now_sl.strftime('%H:%M'),
            'date': today_sl.strftime('%Y-%m-%d'),
            'sound': 'success'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error processing scan: {str(e)}',
            'sound': 'error'
        })

@employee_bp.route('/employee/my-barcode')
@login_required
def my_barcode():
    """Display employee's own barcode"""
    # Import here to avoid circular imports
    from ...models.employee import EmployeeProfile
    
    employee_profile = EmployeeProfile.query.filter_by(user_id=current_user.id).first()
    
    if not employee_profile:
        flash('Employee profile not found', 'danger')
        return redirect(url_for('employee.employee_detail', employee_id=current_user.id))
    
    # Generate barcode if not exists
    if not employee_profile.employee_barcode:
        employee_profile.generate_barcode()
        employee_profile.get_barcode_image_url()
        db.session.commit()
    
    return render_template('employee/my_barcode.html',
                         employee_profile=employee_profile,
                         title='My Barcode')


@employee_bp.route('/employee/<int:employee_id>/barcode')
@login_required
def view_employee_barcode(employee_id):
    """View specific employee's barcode (admin/staff only)"""
    if current_user.role not in ['admin', 'staff'] and current_user.id != employee_id:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Import here to avoid circular imports
    from ...models.employee import EmployeeProfile
    
    employee_profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
    
    if not employee_profile:
        flash('Employee profile not found', 'danger')
        return redirect(url_for('employee.employee_detail', employee_id=employee_id))
    
    return render_template('employee/employee_barcode.html',
                         employee_profile=employee_profile,
                         title=f'Barcode - {employee_profile.full_name}')


@employee_bp.route('/employee/<int:employee_id>/regenerate-barcode', methods=['POST'])
@login_required
def regenerate_employee_barcode(employee_id):
    """Regenerate employee barcode (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Import here to avoid circular imports
    from ...models.employee import EmployeeProfile
    
    employee_profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
    
    if not employee_profile:
        return jsonify({'success': False, 'message': 'Employee not found'})
    
    try:
        # Generate new barcode
        old_barcode = employee_profile.employee_barcode
        employee_profile.employee_barcode = None
        employee_profile.generate_barcode()
        employee_profile.get_barcode_image_url()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Barcode regenerated successfully',
            'new_barcode': employee_profile.employee_barcode
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


@employee_bp.route('/api/attendance-logs')
@login_required
def get_attendance_logs():
    """Get attendance logs for reporting"""
    if current_user.role not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    # Import here to avoid circular imports
    from ...models.employee import AttendanceLog
    
    date_filter = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    employee_id = request.args.get('employee_id', type=int)
    
    try:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
    except:
        filter_date = date.today()
    
    query = AttendanceLog.query.filter(
        db.func.date(AttendanceLog.scan_time) == filter_date
    ).order_by(AttendanceLog.scan_time.desc())
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    logs = query.limit(100).all()
    
    logs_data = []
    for log in logs:
        # Safely resolve employee full name (support both scalar and list backrefs)
        emp_profile = getattr(log.employee, 'employee_profile', None)
        full_name = ''
        if emp_profile:
            if isinstance(emp_profile, list):
                full_name = emp_profile[0].full_name if len(emp_profile) else ''
            else:
                full_name = emp_profile.full_name

        logs_data.append({
            'id': log.id,
            'employee_id': log.employee.id,
            'employee_name': log.employee.username,
            'full_name': full_name,
            'scan_type': log.scan_type,
            'scan_time': log.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
            'barcode_used': log.barcode_used,
            'location': log.location
        })
    
    return jsonify({'success': True, 'logs': logs_data})


@employee_bp.route('/barcode-scanning-guide')
@login_required
def barcode_scanning_guide():
    """Guide for setting up barcode scanner"""
    if current_user.role not in ['admin', 'staff']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    return render_template('employee/barcode_scanning_guide.html',
                         title='Barcode Scanner Setup Guide')


# Add barcode details endpoint
@employee_bp.route('/employee/<int:employee_id>/barcode-details')
@login_required
def employee_barcode_details(employee_id):
    """Get barcode details for employee"""
    if current_user.role not in ['admin', 'staff'] and current_user.id != employee_id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    # Import here to avoid circular imports
    from ...models.employee import EmployeeProfile
    
    employee_profile = EmployeeProfile.query.filter_by(user_id=employee_id).first()
    
    if not employee_profile:
        return jsonify({'success': False, 'message': 'Employee not found'})
    
    if not employee_profile.employee_barcode:
        return jsonify({'success': False, 'message': 'Employee has no barcode'})
    
    return jsonify({
        'success': True,
        'barcode': employee_profile.employee_barcode,
        'barcode_image': employee_profile.barcode_image,
        'generated_at': employee_profile.barcode_generated_at.strftime('%Y-%m-%d %H:%M:%S') if employee_profile.barcode_generated_at else None,
        'scans_count': employee_profile.barcode_scans_count or 0
    })