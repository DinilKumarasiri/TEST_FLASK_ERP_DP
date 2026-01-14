# models/stock.py - Updated
from .. import db
from datetime import datetime
import re
import secrets
import string

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    item_barcode = db.Column(db.String(100), unique=True, nullable=True)  # Unique per item
    is_serialized = db.Column(db.Boolean, default=False)  # Track if item has unique barcode
    stock_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, default=1)
    purchase_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'))
    batch_number = db.Column(db.String(100))
    imei = db.Column(db.String(50), unique=True, nullable=True)
    location = db.Column(db.String(200))
    status = db.Column(db.String(50), default='available')  # available, sold, damaged, etc.
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', overlaps="stock_items")
    purchase_order = db.relationship('PurchaseOrder', back_populates='stock_items')
    creator = db.relationship('User', backref='stock_items_created')
    invoice_items = db.relationship('InvoiceItem', backref='stock_item', lazy=True)
    repair_items = db.relationship('RepairItem', backref='stock_item', lazy=True)
    
    def generate_unique_barcode(self):
        """Generate unique barcode for this stock item"""
        from app.utils.barcode_generator import BarcodeGenerator
        
        # Generate a unique identifier
        timestamp = int(datetime.utcnow().timestamp() * 1000) % 1000000
        random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
        
        # Base on product SKU if available
        if self.product and self.product.sku:
            base = re.sub(r'[^A-Za-z0-9]', '', self.product.sku)[:6]
            barcode_number = f"{base}{timestamp:06d}{random_part}"
        else:
            barcode_number = f"ST{self.id:08d}{timestamp:06d}{random_part}"
        
        # Ensure proper length (12-13 digits)
        if len(barcode_number) < 12:
            barcode_number = barcode_number.zfill(12)
        elif len(barcode_number) > 13:
            barcode_number = barcode_number[:13]
        
        # Add check digit
        barcode_number = self._add_check_digit(barcode_number)
        
        return barcode_number
    
    def _add_check_digit(self, barcode):
        """Add check digit to barcode (EAN-13 style)"""
        # For 12-digit barcodes, calculate check digit
        if len(barcode) == 12:
            digits = [int(d) for d in barcode]
            
            # Step 1: Multiply odd positions by 3 (starting from 1)
            odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
            # Step 2: Sum even positions
            even_sum = sum(digits[i] for i in range(1, 12, 2))
            
            # Step 3: Add both sums
            total = odd_sum + even_sum
            
            # Step 4: Find check digit (smallest number to make total multiple of 10)
            check_digit = (10 - (total % 10)) % 10
            
            return barcode + str(check_digit)
        return barcode
    
    def get_barcode_image_url(self):
        """Get barcode image URL for this specific item"""
        if self.item_barcode:
            return f"https://barcode.tec-it.com/barcode.ashx?data={self.item_barcode}&code=Code128&dpi=96"
        return None
    
    def __repr__(self):
        return f'<StockItem {self.id} - {self.product.name if self.product else "Unknown"}>'