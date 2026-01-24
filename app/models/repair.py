# app/models/repair.py
from .. import db
from datetime import datetime
from datetime import datetime, timedelta  # Add this import at the top

# Existing RepairJob model - keep this FIRST
class RepairJob(db.Model):
    __tablename__ = 'repair_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    device_type = db.Column(db.String(50), nullable=False)  # mobile, tablet, etc.
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    imei = db.Column(db.String(20))
    serial_number = db.Column(db.String(50))
    issue_description = db.Column(db.Text, nullable=False)
    accessories_received = db.Column(db.Text)
    estimated_cost = db.Column(db.Float, default=0.0)
    final_cost = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='received')  # received, diagnostic, repairing, waiting_parts, completed, delivered
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    diagnosis_details = db.Column(db.Text)
    repair_details = db.Column(db.Text)
    warranty_period = db.Column(db.Integer, default=0)  # in months
    customer_approval = db.Column(db.Boolean, default=False)
    approval_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    delivered_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    repair_items = db.relationship('RepairItem', backref='repair_job', lazy=True, cascade='all, delete-orphan')
    
    # Add these relationships explicitly
    technician = db.relationship('User', foreign_keys=[technician_id], backref='repair_jobs_as_technician')
    creator = db.relationship('User', foreign_keys=[created_by], backref='repair_jobs_created')
    
    # Add relationship to repair invoices
    repair_invoices = db.relationship('RepairInvoice', backref='repair_job', lazy=True)


class RepairItem(db.Model):
    __tablename__ = 'repair_items'
    
    id = db.Column(db.Integer, primary_key=True)
    repair_job_id = db.Column(db.Integer, db.ForeignKey('repair_jobs.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)

# New Repair Invoice models - add these AFTER the existing models
class RepairInvoice(db.Model):
    __tablename__ = 'repair_invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    repair_job_id = db.Column(db.Integer, db.ForeignKey('repair_jobs.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Repair specific fields
    device_type = db.Column(db.String(50))
    brand = db.Column(db.String(50))
    model = db.Column(db.String(100))
    imei = db.Column(db.String(20))
    
    # Financial fields
    labor_cost = db.Column(db.Float, default=0.0)
    parts_cost = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)
    advance_paid = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    
    # Payment fields
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid
    payment_method = db.Column(db.String(20))  # cash, card, online, due
    payment_reference = db.Column(db.String(100))
    
    # Warranty fields
    warranty_period = db.Column(db.Integer, default=0)  # in months
    warranty_start = db.Column(db.Date)
    warranty_end = db.Column(db.Date)
    
    # Additional info
    issue_description = db.Column(db.Text)
    work_done = db.Column(db.Text)
    technician_notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text, default="1. Warranty covers parts and labor for specified period.\n2. Warranty void if device shows physical or liquid damage.\n3. Data backup is customer's responsibility.")
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='repair_invoices')
    creator = db.relationship('User', backref='repair_invoices_created')
    payments = db.relationship('RepairPayment', backref='invoice', cascade='all, delete-orphan')
    items = db.relationship('RepairInvoiceItem', backref='invoice', cascade='all, delete-orphan')


class RepairInvoiceItem(db.Model):
    __tablename__ = 'repair_invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('repair_invoices.id'), nullable=False)
    item_type = db.Column(db.String(20), default='part')  # part, labor, service, other
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    warranty_info = db.Column(db.String(200))  # e.g., "3 months warranty"
    notes = db.Column(db.Text)


class RepairPayment(db.Model):
    __tablename__ = 'repair_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('repair_invoices.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, online, due
    reference_number = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    receiver = db.relationship('User', backref='repair_payments_received')