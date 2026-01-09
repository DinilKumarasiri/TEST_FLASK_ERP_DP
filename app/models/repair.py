from .. import db
from datetime import datetime

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
