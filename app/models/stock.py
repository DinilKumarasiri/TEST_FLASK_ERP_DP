from .. import db
from datetime import datetime
import re
import secrets
import string
import time

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    item_barcode = db.Column(db.String(100), unique=True, nullable=True)  # Unique per item
    is_serialized = db.Column(db.Boolean, default=False)  # Track if item has unique barcode
    stock_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Integer, default=1)
    purchase_price = db.Column(db.Float, nullable=True) 
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
        """Generate unique barcode for this stock item - FIXED VERSION"""
        try:
            print(f"DEBUG: Generating barcode for stock item ID: {self.id}, Product ID: {self.product_id}")
            
            # Use timestamp with milliseconds for uniqueness
            timestamp = int(time.time() * 1000) % 1000000
            
            # Generate random part
            random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
            
            # Get product info
            from .product import Product
            product = Product.query.get(self.product_id) if self.product_id else None
            
            # Create base from product SKU or ID
            if product and product.sku:
                # Clean SKU to create barcode (remove special characters)
                base = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                if len(base) < 4:
                    base = base.ljust(4, 'X')
                base = base[:6].upper()
                barcode_number = f"{base}{timestamp:06d}{random_part}"
            else:
                # Use product ID and timestamp
                product_id_str = str(self.product_id or 0).zfill(6)
                barcode_number = f"ST{product_id_str}{timestamp:06d}{random_part}"
            
            print(f"DEBUG: Base barcode: {barcode_number}")
            
            # Ensure proper length (12-13 digits)
            if len(barcode_number) < 12:
                barcode_number = barcode_number.ljust(12, '0')
                print(f"DEBUG: Padded to 12: {barcode_number}")
            elif len(barcode_number) > 13:
                barcode_number = barcode_number[:13]
                print(f"DEBUG: Truncated to 13: {barcode_number}")
            
            # Add check digit
            barcode_number = self._add_check_digit(barcode_number)
            print(f"DEBUG: With check digit: {barcode_number}")
            
            # Check if this barcode already exists in database
            existing = StockItem.query.filter_by(item_barcode=barcode_number).first()
            counter = 0
            while existing and counter < 5:
                print(f"DEBUG: Barcode exists, regenerating... Attempt {counter + 1}")
                # Add more randomness and retry
                time.sleep(0.001)  # Small delay for different timestamp
                timestamp = int(time.time() * 1000) % 1000000
                random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
                
                if product and product.sku:
                    base = re.sub(r'[^A-Za-z0-9]', '', product.sku)[:6].upper()
                    if len(base) < 4:
                        base = base.ljust(4, 'X')
                    barcode_number = f"{base}{timestamp:06d}{random_part}"
                else:
                    product_id_str = str(self.product_id or 0).zfill(6)
                    barcode_number = f"ST{product_id_str}{timestamp:06d}{random_part}"
                
                # Ensure length
                if len(barcode_number) < 12:
                    barcode_number = barcode_number.ljust(12, '0')
                elif len(barcode_number) > 13:
                    barcode_number = barcode_number[:13]
                
                barcode_number = self._add_check_digit(barcode_number)
                existing = StockItem.query.filter_by(item_barcode=barcode_number).first()
                counter += 1
            
            if counter >= 5:
                print("DEBUG: Max regeneration attempts reached, using simple barcode")
                # Fallback: simple timestamp-based barcode
                simple_barcode = f"FB{int(time.time() * 1000000)}{self.id if self.id else 0}"
                if len(simple_barcode) < 12:
                    simple_barcode = simple_barcode.ljust(12, '0')
                elif len(simple_barcode) > 13:
                    simple_barcode = simple_barcode[:13]
                return simple_barcode
            
            print(f"DEBUG: Final generated barcode: {barcode_number}")
            return barcode_number
            
        except Exception as e:
            print(f"ERROR in generate_unique_barcode: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Last resort fallback
            fallback = f"ERR{int(time.time() * 1000000)}{self.id if self.id else 0}"
            if len(fallback) < 12:
                fallback = fallback.ljust(12, '0')
            elif len(fallback) > 13:
                fallback = fallback[:13]
            return fallback
    
    def _add_check_digit(self, barcode):
        """Add check digit to barcode (EAN-13 style)"""
        try:
            # For 12-digit barcodes, calculate check digit
            if len(barcode) == 12:
                # Extract only digits for calculation
                digits_str = ''.join(filter(str.isdigit, barcode))
                if len(digits_str) >= 12:
                    digits = [int(d) for d in digits_str[:12]]
                    
                    # Step 1: Multiply odd positions by 3 (starting from 1)
                    odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
                    # Step 2: Sum even positions
                    even_sum = sum(digits[i] for i in range(1, 12, 2))
                    
                    # Step 3: Add both sums
                    total = odd_sum + even_sum
                    
                    # Step 4: Find check digit (smallest number to make total multiple of 10)
                    check_digit = (10 - (total % 10)) % 10
                    
                    return barcode + str(check_digit)
            
            # For other lengths or if calculation fails, return as-is
            return barcode
            
        except Exception as e:
            print(f"ERROR in _add_check_digit: {str(e)}")
            return barcode  # Return original if calculation fails
    
    def generate_simple_barcode(self):
        """Simple reliable barcode generator - use this if the main one fails"""
        import time
        timestamp = int(time.time() * 1000000)
        item_id = self.id if self.id else 0
        
        # Create unique identifier
        unique_id = f"{timestamp}{item_id}"
        
        # Take last 12-13 characters
        if len(unique_id) < 12:
            unique_id = unique_id.zfill(12)
        elif len(unique_id) > 13:
            unique_id = unique_id[-13:]
        
        # Add prefix
        barcode = f"SI{unique_id}"
        
        # Ensure length
        if len(barcode) < 12:
            barcode = barcode.ljust(12, '0')
        elif len(barcode) > 13:
            barcode = barcode[:13]
        
        return barcode
    
    def ensure_barcode(self):
        """Ensure this stock item has a barcode, generate one if not"""
        if not self.item_barcode or self.item_barcode.strip() == '':
            print(f"DEBUG: Generating barcode for item {self.id} (no barcode found)")
            self.item_barcode = self.generate_unique_barcode()
            self.is_serialized = True
            return True
        return False
    
    def get_barcode_image_url(self):
        """Get barcode image URL for this specific item"""
        if self.item_barcode:
            # Clean barcode for URL
            clean_barcode = str(self.item_barcode).strip()
            if clean_barcode:
                return f"https://barcode.tec-it.com/barcode.ashx?data={clean_barcode}&code=Code128&dpi=96"
        return None
    
    @staticmethod
    def fix_all_null_barcodes():
        """Fix all stock items with NULL barcodes"""
        items_without_barcode = StockItem.query.filter(
            (StockItem.item_barcode.is_(None)) | 
            (StockItem.item_barcode == '') |
            (StockItem.item_barcode == 'None')
        ).all()
        
        print(f"Found {len(items_without_barcode)} items without barcodes")
        
        fixed_count = 0
        for item in items_without_barcode:
            try:
                old_barcode = item.item_barcode
                item.item_barcode = item.generate_unique_barcode()
                item.is_serialized = True
                print(f"Fixed item {item.id}: {old_barcode} -> {item.item_barcode}")
                fixed_count += 1
            except Exception as e:
                print(f"Error fixing item {item.id}: {e}")
                # Simple fallback
                import time
                item.item_barcode = f"FIX{int(time.time() * 1000) % 1000000}{item.id}"
                item.is_serialized = True
                fixed_count += 1
        
        try:
            db.session.commit()
            print(f"Successfully fixed {fixed_count} barcodes!")
            return fixed_count
        except Exception as e:
            db.session.rollback()
            print(f"Error committing barcode fixes: {e}")
            return 0
    
    @staticmethod
    def generate_batch_barcodes(product_id, quantity):
        """Generate multiple unique barcodes for a batch of items"""
        from .product import Product
        
        product = Product.query.get(product_id)
        if not product:
            return []
        
        barcodes = []
        used_barcodes = set()
        
        # Get existing barcodes from database
        existing_barcodes = {b.item_barcode for b in StockItem.query.filter(
            StockItem.item_barcode.isnot(None),
            StockItem.item_barcode != ''
        ).all()}
        
        for i in range(quantity):
            # Create a temporary stock item for barcode generation
            temp_item = StockItem(product_id=product_id)
            
            # Generate unique barcode
            max_attempts = 10
            for attempt in range(max_attempts):
                barcode = temp_item.generate_unique_barcode()
                
                # Check if unique
                if (barcode not in used_barcodes and 
                    barcode not in existing_barcodes):
                    barcodes.append(barcode)
                    used_barcodes.add(barcode)
                    break
                
                if attempt == max_attempts - 1:
                    # Last resort
                    import time
                    last_resort = f"L{int(time.time() * 1000000)}{i}"
                    barcodes.append(last_resort[:13])
                    used_barcodes.add(last_resort[:13])
        
        return barcodes
    
    def __repr__(self):
        return f'<StockItem {self.id} - {self.product.name if self.product else "Unknown"} - Barcode: {self.item_barcode or "None"}>'