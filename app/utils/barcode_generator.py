# app/utils/barcode_generator.py - Updated
import os
import base64
from io import BytesIO
import re
import secrets
import string
from datetime import datetime

class BarcodeGenerator:
    """Barcode generator for products and stock items"""
    
    @staticmethod
    def generate_product_barcode(product):
        """Generate barcode number for product"""
        try:
            if product.sku:
                barcode = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                if len(barcode) < 8:
                    barcode = barcode.zfill(12)
                return barcode[:12]
            else:
                return str(product.id).zfill(12)
        except Exception as e:
            print(f"Error generating product barcode: {e}")
            return str(product.id).zfill(12)
    
    @staticmethod
    def generate_stock_item_barcode(stock_item, product=None):
        """Generate unique barcode for stock item"""
        try:
            # Use existing item_barcode if it exists
            if stock_item.item_barcode:
                return stock_item.item_barcode
            
            # Get product info
            if not product and hasattr(stock_item, 'product'):
                product = stock_item.product
            
            timestamp = int(datetime.utcnow().timestamp() * 1000) % 1000000
            random_part = ''.join(secrets.choice(string.digits) for _ in range(4))
            
            if product and product.sku:
                base = re.sub(r'[^A-Za-z0-9]', '', product.sku)[:6]
                barcode_number = f"{base}{timestamp:06d}{random_part}"
            else:
                barcode_number = f"ST{stock_item.id:08d}{timestamp:06d}{random_part}"
            
            # Ensure proper length
            if len(barcode_number) < 12:
                barcode_number = barcode_number.zfill(12)
            elif len(barcode_number) > 13:
                barcode_number = barcode_number[:13]
            
            # Add check digit
            barcode_number = BarcodeGenerator._add_check_digit(barcode_number)
            
            return barcode_number
            
        except Exception as e:
            print(f"Error generating stock item barcode: {e}")
            # Fallback: use timestamp + random
            return f"IT{int(datetime.utcnow().timestamp())}{secrets.randbelow(10000):04d}"
    
    @staticmethod
    def _add_check_digit(barcode):
        """Add EAN-13 check digit"""
        if len(barcode) == 12:
            try:
                digits = [int(d) for d in barcode]
                odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
                even_sum = sum(digits[i] for i in range(1, 12, 2))
                total = odd_sum + even_sum
                check_digit = (10 - (total % 10)) % 10
                return barcode + str(check_digit)
            except:
                return barcode
        return barcode
    
    @staticmethod
    def generate_online_barcode_url(barcode_number, barcode_type='Code128'):
        """Get barcode image from online generator service"""
        return f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code={barcode_type}&dpi=96&dataseparator="
    
    @staticmethod
    def generate_batch_barcodes(product, quantity=1):
        """Generate multiple unique barcodes for batch creation"""
        barcodes = []
        for i in range(quantity):
            # Create a mock stock item for barcode generation
            class MockStockItem:
                def __init__(self, product):
                    self.id = 0
                    self.product = product
                    self.item_barcode = None
            
            mock_item = MockStockItem(product)
            barcode = BarcodeGenerator.generate_stock_item_barcode(mock_item, product)
            barcodes.append(barcode)
        
        return barcodes
    
    @staticmethod
    def validate_barcode(barcode_number):
        """Validate barcode format"""
        if not barcode_number:
            return False
        
        # Check if it's alphanumeric and reasonable length
        if len(barcode_number) < 8 or len(barcode_number) > 20:
            return False
        
        # Basic validation
        return bool(re.match(r'^[A-Za-z0-9]+$', barcode_number))