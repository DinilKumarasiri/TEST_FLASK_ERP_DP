from .. import db
from datetime import datetime

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    stock_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, default=1)
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'))
    batch_number = db.Column(db.String(100))
    imei = db.Column(db.String(50), unique=True, nullable=True)  # Make nullable
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='available')  # available, sold, damaged, etc.
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', overlaps="stock_items")
    purchase_order = db.relationship('PurchaseOrder')
    creator = db.relationship('User', backref='stock_items_created')
    invoice_items = db.relationship('InvoiceItem', backref='stock_item', lazy=True)
    repair_items = db.relationship('RepairItem', backref='stock_item', lazy=True)
