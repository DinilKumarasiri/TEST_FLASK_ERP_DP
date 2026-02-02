from .. import db
from datetime import datetime

class ProductCategory(db.Model):
    __tablename__ = 'product_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __init__(self, name, description=None):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f'<ProductCategory {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(100), unique=True, nullable=True)
    barcode_image = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('product_categories.id'))
    description = db.Column(db.Text)
    purchase_price = db.Column(db.Float, nullable=True, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    wholesale_price = db.Column(db.Float, default=0.0)
    min_stock_level = db.Column(db.Integer, default=5)
    has_imei = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock_items = db.relationship('StockItem', backref='product', lazy=True)
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)
    repair_items = db.relationship('RepairItem', backref='product', lazy=True)
    purchase_order_items = db.relationship('PurchaseOrderItem', back_populates='product', lazy=True)
    
    def get_barcode_image_url(self):
        """Get URL for barcode image"""
        if self.barcode_image:
            if self.barcode_image.startswith('http'):
                return self.barcode_image
            return f"/static/{self.barcode_image}"
        return None
    
    def __repr__(self):
        return f'<Product {self.sku}: {self.name}>'