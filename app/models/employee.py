# app/models/employee.py
from .. import db
from datetime import datetime
import pytz

# Sri Lanka timezone
SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

def get_sri_lanka_time():
    """Get current time in Sri Lanka"""
    return datetime.now(SRI_LANKA_TZ)

class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    total_hours = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='present')  # present, absent, half_day, leave
    notes = db.Column(db.Text)

    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),)

    # Relationship
    employee = db.relationship('User', foreign_keys=[employee_id], backref='attendances')
    
    def get_check_in_sri_lanka(self):
        """Get check-in time in Sri Lanka timezone"""
        if self.check_in:
            if self.check_in.tzinfo is None:
                return SRI_LANKA_TZ.localize(self.check_in)
            return self.check_in.astimezone(SRI_LANKA_TZ)
        return None
    
    def get_check_out_sri_lanka(self):
        """Get check-out time in Sri Lanka timezone"""
        if self.check_out:
            if self.check_out.tzinfo is None:
                return SRI_LANKA_TZ.localize(self.check_out)
            return self.check_out.astimezone(SRI_LANKA_TZ)
        return None
    
    def calculate_hours_sri_lanka(self):
        """Calculate hours based on Sri Lanka time"""
        check_in_sl = self.get_check_in_sri_lanka()
        check_out_sl = self.get_check_out_sri_lanka()
        
        if check_in_sl and check_out_sl:
            time_diff = check_out_sl - check_in_sl
            return time_diff.total_seconds() / 3600
        return 0.0

class AttendanceLog(db.Model):
    """Barcode-based attendance logging"""
    __tablename__ = 'attendance_logs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_type = db.Column(db.String(20), nullable=False)  # 'check_in' or 'check_out'
    scan_time = db.Column(db.DateTime, nullable=False)
    barcode_used = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    employee = db.relationship('User', foreign_keys=[employee_id], backref='attendance_logs')

    def __repr__(self):
        return f'<AttendanceLog {self.id}: {self.employee_id} - {self.scan_type} at {self.scan_time}>'
    
    def get_scan_time_sri_lanka(self):
        """Get scan time in Sri Lanka timezone"""
        if self.scan_time:
            return self.scan_time.astimezone(SRI_LANKA_TZ)
        return None

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(30), nullable=False)  # sick, casual, annual, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    days_requested = db.Column(db.Integer, default=1)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships - specify foreign_keys explicitly
    employee = db.relationship('User', foreign_keys=[employee_id], backref='leaves_requested')
    approver = db.relationship('User', foreign_keys=[approved_by], backref='leaves_approved')


class Commission(db.Model):
    __tablename__ = 'commissions'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'))
    repair_job_id = db.Column(db.Integer, db.ForeignKey('repair_jobs.id'))
    sale_amount = db.Column(db.Float, nullable=False)
    commission_rate = db.Column(db.Float, nullable=False)  # percentage
    commission_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid
    payment_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    employee = db.relationship('User', backref='commissions')
    invoice = db.relationship('Invoice', backref='commissions')
    repair_job = db.relationship('RepairJob', backref='commissions')


class EmployeeProfile(db.Model):
    __tablename__ = 'employee_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    # Personal Information
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))  # Male, Female, Other
    personal_phone = db.Column(db.String(20))
    personal_email = db.Column(db.String(120))
    emergency_contact = db.Column(db.String(100))
    emergency_phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    aadhar_number = db.Column(db.String(20))
    pan_number = db.Column(db.String(20))
    profile_picture = db.Column(db.String(200))

    # Employment Details
    employee_code = db.Column(db.String(50), unique=True)
    job_title = db.Column(db.String(100))
    department = db.Column(db.String(50))  # Sales, Repair, Inventory, Admin
    employment_type = db.Column(db.String(20))  # Full-time, Part-time, Contract
    date_of_joining = db.Column(db.Date)
    probation_end_date = db.Column(db.Date)
    work_location = db.Column(db.String(100))
    shift_timing = db.Column(db.String(50))
    reporting_manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Barcode Information
    employee_barcode = db.Column(db.String(100), unique=True)
    barcode_image = db.Column(db.String(200))
    barcode_generated_at = db.Column(db.DateTime)
    barcode_scans_count = db.Column(db.Integer, default=0)

    # Salary Information
    basic_salary = db.Column(db.Float, default=0.0)
    commission_rate = db.Column(db.Float, default=0.0)  # Percentage
    bank_name = db.Column(db.String(100))
    account_number = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(20))

    # Skills & Qualifications
    education = db.Column(db.Text)
    certifications = db.Column(db.Text)
    skills = db.Column(db.Text)  # JSON or comma-separated
    experience_years = db.Column(db.Integer)
    specialization = db.Column(db.Text)  # For technicians

    # Performance Metrics (for Sales)
    sales_target_monthly = db.Column(db.Float, default=0.0)

    # Documents
    resume_path = db.Column(db.String(200))
    id_proof_path = db.Column(db.String(200))
    address_proof_path = db.Column(db.String(200))

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('employee_profile', uselist=False))
    reporting_manager = db.relationship('User', foreign_keys=[reporting_manager_id])

    def __repr__(self):
        return f'<EmployeeProfile {self.full_name} - {self.employee_code}>'

    def generate_barcode(self):
        """Generate a unique barcode for this employee"""
        import secrets
        import string
        import time
        
        if not self.employee_barcode:
            # Generate unique barcode
            timestamp = int(time.time() * 1000) % 1000000
            random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
            
            # Use employee code or user ID as base
            if self.employee_code:
                base = ''.join(c for c in self.employee_code if c.isalnum())[:6].upper()
            else:
                base = f"EMP{self.user_id:04d}"[:6]
            
            barcode = f"{base}{timestamp:06d}{random_part}"
            
            # Ensure proper length (12-13 digits)
            if len(barcode) < 12:
                barcode = barcode.ljust(12, '0')
            elif len(barcode) > 13:
                barcode = barcode[:13]
            
            # Add check digit
            barcode = self._add_check_digit(barcode)
            
            self.employee_barcode = barcode
            self.barcode_generated_at = datetime.utcnow()
        
        return self.employee_barcode

    def _add_check_digit(self, barcode):
        """Add check digit to barcode (EAN-13 style)"""
        try:
            # For 12-digit barcodes, calculate check digit
            if len(barcode) == 12:
                digits = [int(d) for d in barcode[:12]]
                
                # Step 1: Multiply odd positions by 3 (starting from 1)
                odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
                # Step 2: Sum even positions
                even_sum = sum(digits[i] for i in range(1, 12, 2))
                
                # Step 3: Add both sums
                total = odd_sum + even_sum
                
                # Step 4: Find check digit (smallest number to make total multiple of 10)
                check_digit = (10 - (total % 10)) % 10
                
                return barcode + str(check_digit)
        
        except Exception:
            pass
        
        return barcode

    def get_barcode_image_url(self):
        """Get barcode image URL for employee"""
        if self.employee_barcode:
            # Generate image URL using online service
            barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={self.employee_barcode}&code=Code128&dpi=96"
            self.barcode_image = barcode_url
            return barcode_url
        return None

    def increment_scan_count(self):
        """Increment barcode scan counter"""
        self.barcode_scans_count = (self.barcode_scans_count or 0) + 1
        self.updated_at = datetime.utcnow()