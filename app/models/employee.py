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
