import re
import secrets
import string
import time
from datetime import datetime

class BarcodeGenerator:
    @staticmethod
    def generate_batch_barcodes(product, quantity):
        """Generate unique barcodes for a batch of items"""
        barcodes = []
        used_barcodes = set()
        
        # Get existing barcodes from database to avoid duplicates
        from app.models import StockItem
        existing_barcodes = {b.item_barcode for b in StockItem.query.filter(
            StockItem.item_barcode.isnot(None)
        ).all()}
        
        for i in range(quantity):
            max_attempts = 20
            for attempt in range(max_attempts):
                # Generate base barcode
                base_barcode = BarcodeGenerator._generate_single_barcode(product, i)
                
                # Make it unique with timestamp and random part
                timestamp = int(time.time() * 1000) % 1000000
                random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
                unique_barcode = f"{base_barcode[:8]}{timestamp:06d}{random_part}"
                
                # Ensure proper length
                if len(unique_barcode) < 12:
                    unique_barcode = unique_barcode.ljust(12, '0')
                elif len(unique_barcode) > 13:
                    unique_barcode = unique_barcode[:13]
                
                # Add check digit
                unique_barcode = BarcodeGenerator._add_check_digit(unique_barcode)
                
                # Check if this barcode is unique
                if (unique_barcode not in used_barcodes and 
                    unique_barcode not in existing_barcodes):
                    barcodes.append(unique_barcode)
                    used_barcodes.add(unique_barcode)
                    break
                
                if attempt == max_attempts - 1:
                    # Last resort: use timestamp only
                    last_resort = f"U{int(time.time() * 1000000)}{i}"
                    barcodes.append(last_resort[:13])
                    used_barcodes.add(last_resort[:13])
        
        return barcodes
    
    @staticmethod
    def _generate_single_barcode(product, index):
        """Generate a single barcode for a product"""
        try:
            if product.sku:
                # Clean SKU to create barcode (remove special characters)
                base = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                if len(base) < 6:
                    base = base.ljust(6, 'X')
                return base[:6] + f"{index:04d}"
            else:
                return f"P{product.id:06d}{index:04d}"
        except:
            import time
            return f"G{int(time.time() * 1000) % 1000000:06d}{index:04d}"
    
    @staticmethod
    def _add_check_digit(barcode):
        """Add check digit to barcode (EAN-13 style)"""
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
    
    @staticmethod
    def generate_product_barcode(product):
        """Generate barcode for product (not for individual items)"""
        import time
        timestamp = int(time.time() * 1000) % 1000000
        
        if product.sku:
            base = re.sub(r'[^A-Za-z0-9]', '', product.sku)
            if len(base) < 8:
                base = base.ljust(8, '0')
            barcode = f"{base[:8]}{timestamp:06d}"
        else:
            barcode = f"PR{product.id:08d}{timestamp:06d}"
        
        # Ensure length
        if len(barcode) < 12:
            barcode = barcode.ljust(12, '0')
        elif len(barcode) > 13:
            barcode = barcode[:13]
        
        # Add check digit if needed
        if len(barcode) == 12:
            barcode = BarcodeGenerator._add_check_digit(barcode)
        
        return barcode
    
    @staticmethod
    def generate_online_barcode_url(barcode_number, barcode_type='Code128'):
        """Get barcode image from online generator service"""
        return f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code={barcode_type}&dpi=96&dataseparator="