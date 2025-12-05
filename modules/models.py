from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False, default='staff')  # admin, manager, staff, technician
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - specify foreign_keys explicitly
    attendances = db.relationship('Attendance', backref='employee', lazy=True, 
                                 foreign_keys='Attendance.employee_id')
    repair_jobs_as_technician = db.relationship('RepairJob', backref='technician', lazy=True,
                                               foreign_keys='RepairJob.technician_id')
    repair_jobs_created = db.relationship('RepairJob', backref='creator', lazy=True,
                                         foreign_keys='RepairJob.created_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True)
    repair_jobs = db.relationship('RepairJob', backref='customer', lazy=True)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    gst_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class ProductCategory(db.Model):
    __tablename__ = 'product_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'))
    description = db.Column(db.Text)
    purchase_price = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    wholesale_price = db.Column(db.Float, default=0.0)
    min_stock_level = db.Column(db.Integer, default=5)
    has_imei = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    stock_items = db.relationship('StockItem', backref='product', lazy=True)
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    imei = db.Column(db.String(20), unique=True)
    serial_number = db.Column(db.String(50))
    batch_number = db.Column(db.String(50))
    stock_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, nullable=False, default=1)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'))
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='available')  # available, sold, reserved, defective
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', backref='stock_items')
    purchase_order = db.relationship('PurchaseOrder', backref='stock_items')

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, approved, received, cancelled
    total_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    po_items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True)
    creator = db.relationship('User', backref='purchase_orders')

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    received_quantity = db.Column(db.Integer, default=0)

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, partial, paid
    payment_method = db.Column(db.String(20))  # cash, card, online, due
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', backref='invoices')

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, nullable=False)
    warranty_period = db.Column(db.Integer)  # in months

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, online, due
    reference_number = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    receiver = db.relationship('User', backref='payments_received')

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

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(30), nullable=False)  # sick, casual, annual, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - specify foreign_keys explicitly
    employee = db.relationship('User', foreign_keys=[employee_id], backref='commissions')
    invoice = db.relationship('Invoice', backref='commissions')
    repair_job = db.relationship('RepairJob', backref='commissions')