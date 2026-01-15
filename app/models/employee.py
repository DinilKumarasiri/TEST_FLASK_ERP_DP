# app/models/employee.py
from .. import db
from datetime import datetime

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
    user = db.relationship('User', foreign_keys=[user_id], backref='employee_profile')
    reporting_manager = db.relationship('User', foreign_keys=[reporting_manager_id])
    
    def __repr__(self):
        return f'<EmployeeProfile {self.full_name} - {self.employee_code}>'