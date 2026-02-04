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

def convert_to_sri_lanka_time(dt):
    """Convert a datetime to Sri Lanka timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:  # If naive datetime, assume it's UTC
        dt = pytz.utc.localize(dt)
    return dt.astimezone(SRI_LANKA_TZ)

@employee_bp.route('/barcode-attendance')
@login_required
def barcode_attendance_interface():
    """Admin interface for barcode scanning attendance"""
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Get Sri Lanka date for display
    today_sl = get_sri_lanka_date()
    
    return render_template('employee/barcode_attendance.html',
                         today_sl=today_sl,
                         now=get_sri_lanka_time(),
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
        
        # Determine scan type based on existing attendance
        scan_type = None
        message = ""
        
        # Check for existing logs for today to enforce one check-in/one check-out
        today_logs = AttendanceLog.query.filter(
            AttendanceLog.employee_id == employee.id,
            db.func.date(AttendanceLog.scan_time) == today_sl
        ).order_by(AttendanceLog.scan_time).all()
        
        # Count check-ins and check-outs for today
        checkin_count = sum(1 for log in today_logs if log.scan_type == 'check_in')
        checkout_count = sum(1 for log in today_logs if log.scan_type == 'check_out')
        
        if not attendance:
            # No attendance record for today
            
            if checkin_count > 0:
                # Should not happen, but handle edge case
                return jsonify({
                    'success': False,
                    'message': f'{employee.username} already checked in today',
                    'sound': 'warning'
                })
            
            # This should be the first check-in for today
            scan_type = 'check_in'
            message = f'Checked in: {employee.username} at {now_sl.strftime("%H:%M")}'
            
        else:
            # Attendance record exists
            
            if attendance.check_in and not attendance.check_out:
                # Already checked in but not out
                
                if checkout_count > 0:
                    # Should not happen, but handle edge case
                    return jsonify({
                        'success': False,
                        'message': f'{employee.username} already checked out today',
                        'sound': 'warning'
                    })
                
                # This should be the first and only check-out
                scan_type = 'check_out'
                message = f'Checked out: {employee.username} at {now_sl.strftime("%H:%M")}'
                
            elif attendance.check_in and attendance.check_out:
                # Both check-in and check-out already recorded for today
                
                # Check if this is a duplicate check-in attempt
                if checkin_count >= 1 and checkout_count >= 1:
                    return jsonify({
                        'success': False,
                        'message': f'{employee.username} already completed attendance for today (Check-in: {convert_to_sri_lanka_time(attendance.check_in).strftime("%H:%M")}, Check-out: {convert_to_sri_lanka_time(attendance.check_out).strftime("%H:%M")})',
                        'sound': 'warning'
                    })
                elif checkin_count >= 1 and checkout_count == 0:
                    # Has check-in but not check-out in logs (edge case)
                    scan_type = 'check_out'
                    message = f'Checked out: {employee.username} at {now_sl.strftime("%H:%M")}'
                else:
                    # Edge case: attendance exists but logs don't match
                    scan_type = 'check_in'
                    message = f'Re-checked in: {employee.username} at {now_sl.strftime("%H:%M")} (System correction)'
                    
            else:
                # Edge case: has attendance record but no check_in
                if checkin_count > 0:
                    return jsonify({
                        'success': False,
                        'message': f'{employee.username} already checked in today',
                        'sound': 'warning'
                    })
                
                scan_type = 'check_in'
                message = f'Checked in: {employee.username} at {now_sl.strftime("%H:%M")}'
        
        # Enforce one check-in and one check-out maximum
        if scan_type == 'check_in' and checkin_count >= 1:
            # Get the existing check-in time for the message
            existing_checkin_time = None
            for log in today_logs:
                if log.scan_type == 'check_in':
                    existing_checkin_time = convert_to_sri_lanka_time(log.scan_time).strftime("%H:%M")
                    break
            
            return jsonify({
                'success': False,
                'message': f'{employee.username} already checked in today at {existing_checkin_time or "unknown time"}. Only one check-in allowed per day.',
                'sound': 'warning'
            })
        
        if scan_type == 'check_out' and checkout_count >= 1:
            # Get the existing check-out time for the message
            existing_checkout_time = None
            for log in today_logs:
                if log.scan_type == 'check_out':
                    existing_checkout_time = convert_to_sri_lanka_time(log.scan_time).strftime("%H:%M")
                    break
            
            return jsonify({
                'success': False,
                'message': f'{employee.username} already checked out today at {existing_checkout_time or "unknown time"}. Only one check-out allowed per day.',
                'sound': 'warning'
            })
        
        # Create or update attendance record
        if not attendance:
            attendance = Attendance(
                employee_id=employee.id,
                date=today_sl,
                status='present'
            )
        
        if scan_type == 'check_in':
            attendance.check_in = now_sl.astimezone(pytz.UTC)  # Store as UTC
        else:  # check_out
            attendance.check_out = now_sl.astimezone(pytz.UTC)  # Store as UTC
            
            # Calculate total hours - ensure both datetimes are in the same timezone
            if attendance.check_in:
                # Convert check_in to Sri Lanka time for calculation
                check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
                check_out_sl = convert_to_sri_lanka_time(attendance.check_out)
                
                # Now both are in Sri Lanka timezone
                time_diff = check_out_sl - check_in_sl
                attendance.total_hours = time_diff.total_seconds() / 3600  # Convert to hours
        
        # Log the barcode scan with Sri Lanka time (store in UTC)
        attendance_log = AttendanceLog(
            employee_id=employee.id,
            scan_type=scan_type,
            scan_time=now_sl.astimezone(pytz.UTC),  # Store in UTC
            barcode_used=barcode,
            location=request.remote_addr
        )
        
        # Update scan count
        employee_profile.increment_scan_count()
        
        # Save to database
        db.session.add(attendance)
        db.session.add(attendance_log)
        db.session.commit()
        
        # Format times for display (in Sri Lanka time)
        check_in_display = None
        check_out_display = None
        
        if attendance.check_in:
            check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
            check_in_display = check_in_sl.strftime('%H:%M')
        
        if attendance.check_out:
            check_out_sl = convert_to_sri_lanka_time(attendance.check_out)
            check_out_display = check_out_sl.strftime('%H:%M')
        
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
            'check_in_time': check_in_display,
            'check_out_time': check_out_display,
            'total_hours': attendance.total_hours,
            'sound': 'success'
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in process_barcode_scan: {str(e)}")
        print(traceback.format_exc())
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
    limit = request.args.get('limit', 100, type=int)
    
    try:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
    except:
        filter_date = date.today()
    
    query = AttendanceLog.query.filter(
        db.func.date(AttendanceLog.scan_time) == filter_date
    ).order_by(AttendanceLog.scan_time.desc())
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
    
    logs = query.limit(limit).all()
    
    logs_data = []
    for log in logs:
        # Safely resolve employee full name
        emp_profile = getattr(log.employee, 'employee_profile', None)
        full_name = ''
        if emp_profile:
            if isinstance(emp_profile, list):
                full_name = emp_profile[0].full_name if len(emp_profile) else ''
            else:
                full_name = emp_profile.full_name
        
        # Convert scan time to Sri Lanka time for display
        scan_time_sl = convert_to_sri_lanka_time(log.scan_time)
        
        logs_data.append({
            'id': log.id,
            'employee_id': log.employee.id,
            'employee_name': log.employee.username,
            'full_name': full_name,
            'scan_type': log.scan_type,
            'scan_time': scan_time_sl.strftime('%Y-%m-%d %H:%M:%S'),
            'barcode_used': log.barcode_used,
            'location': log.location
        })
    
    return jsonify({'success': True, 'logs': logs_data})

@employee_bp.route('/api/employee-attendance-status/<int:employee_id>')
@login_required
def get_employee_attendance_status(employee_id):
    """Get today's attendance status for a specific employee"""
    if current_user.role not in ['admin', 'staff'] and current_user.id != employee_id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    today_sl = get_sri_lanka_date()
    
    employee = User.query.get(employee_id)
    if not employee:
        return jsonify({'success': False, 'message': 'Employee not found'})
    
    attendance = Attendance.query.filter_by(
        employee_id=employee_id,
        date=today_sl
    ).first()
    
    # Get today's logs for this employee
    today_logs = AttendanceLog.query.filter(
        AttendanceLog.employee_id == employee_id,
        db.func.date(AttendanceLog.scan_time) == today_sl
    ).order_by(AttendanceLog.scan_time).all()
    
    checkin_count = sum(1 for log in today_logs if log.scan_type == 'check_in')
    checkout_count = sum(1 for log in today_logs if log.scan_type == 'check_out')
    
    check_in_display = None
    check_out_display = None
    hours = 0.0
    
    if attendance:
        if attendance.check_in:
            check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
            check_in_display = check_in_sl.strftime('%H:%M')
        
        if attendance.check_out:
            check_out_sl = convert_to_sri_lanka_time(attendance.check_out)
            check_out_display = check_out_sl.strftime('%H:%M')
            
            # Calculate hours if both exist
            if attendance.check_in:
                check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
                time_diff = check_out_sl - check_in_sl
                hours = round(time_diff.total_seconds() / 3600, 1)
    
    # Determine next action
    next_action = None
    if checkin_count == 0:
        next_action = 'check_in'
    elif checkin_count >= 1 and checkout_count == 0:
        next_action = 'check_out'
    else:
        next_action = 'completed'
    
    return jsonify({
        'success': True,
        'employee_id': employee_id,
        'username': employee.username,
        'check_in_time': check_in_display,
        'check_out_time': check_out_display,
        'total_hours': hours,
        'checkin_count': checkin_count,
        'checkout_count': checkout_count,
        'next_action': next_action,
        'date': today_sl.strftime('%Y-%m-%d'),
        'status': attendance.status if attendance else 'not_scanned'
    })

@employee_bp.route('/barcode-scanning-guide')
@login_required
def barcode_scanning_guide():
    """Guide for setting up barcode scanner"""
    if current_user.role not in ['admin', 'staff']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    return render_template('employee/barcode_scanning_guide.html',
                         title='Barcode Scanner Setup Guide')

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

@employee_bp.route('/api/today-attendance-status')
@login_required
def today_attendance_status():
    """Get today's attendance status for all employees"""
    if current_user.role not in ['admin', 'staff']:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    today_sl = get_sri_lanka_date()
    
    # Get all active employees
    employees = User.query.filter_by(is_active=True).all()
    
    status_data = []
    for employee in employees:
        attendance = Attendance.query.filter_by(
            employee_id=employee.id,
            date=today_sl
        ).first()
        
        # Get employee profile for full name
        employee_profile = EmployeeProfile.query.filter_by(user_id=employee.id).first()
        
        # Get today's logs for this employee
        today_logs = AttendanceLog.query.filter(
            AttendanceLog.employee_id == employee.id,
            db.func.date(AttendanceLog.scan_time) == today_sl
        ).all()
        
        checkin_count = sum(1 for log in today_logs if log.scan_type == 'check_in')
        checkout_count = sum(1 for log in today_logs if log.scan_type == 'check_out')
        
        check_in_display = None
        check_out_display = None
        hours = 0.0
        
        if attendance:
            if attendance.check_in:
                check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
                check_in_display = check_in_sl.strftime('%H:%M')
            
            if attendance.check_out:
                check_out_sl = convert_to_sri_lanka_time(attendance.check_out)
                check_out_display = check_out_sl.strftime('%H:%M')
                
                # Calculate hours if both exist
                if attendance.check_in:
                    check_in_sl = convert_to_sri_lanka_time(attendance.check_in)
                    time_diff = check_out_sl - check_in_sl
                    hours = round(time_diff.total_seconds() / 3600, 1)
        
        # Determine attendance status
        status = 'not_scanned'
        if checkin_count >= 1 and checkout_count >= 1:
            status = 'completed'
        elif checkin_count >= 1:
            status = 'checked_in'
        
        status_data.append({
            'employee_id': employee.id,
            'username': employee.username,
            'full_name': employee_profile.full_name if employee_profile else employee.username,
            'has_check_in': attendance.check_in is not None if attendance else False,
            'has_check_out': attendance.check_out is not None if attendance else False,
            'check_in_time': check_in_display,
            'check_out_time': check_out_display,
            'hours': hours,
            'checkin_count': checkin_count,
            'checkout_count': checkout_count,
            'status': status
        })
    
    return jsonify({'success': True, 'data': status_data, 'date': today_sl.strftime('%Y-%m-%d')})