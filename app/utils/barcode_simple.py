# app/utils/barcode_simple.py
import os
from flask import current_app
import base64
from io import BytesIO

class SimpleBarcodeGenerator:
    @staticmethod
    def generate_barcode_for_product(product):
        """Generate a simple barcode number from product"""
        try:
            # Use SKU or ID for barcode
            if product.sku:
                # Clean SKU: remove special characters, keep alphanumeric
                barcode = ''.join(c for c in product.sku if c.isalnum())
                if len(barcode) < 8:
                    barcode = barcode.zfill(12)
                return barcode[:12]  # Standard barcode length
            else:
                # Use product ID padded to 12 digits
                return str(product.id).zfill(12)
        except Exception as e:
            print(f"Error generating barcode number: {e}")
            return str(product.id).zfill(12)
    
    @staticmethod
    def create_barcode_image(barcode_number):
        """Create a simple text-based barcode image (fallback)"""
        try:
            # For now, create a simple text representation
            # You can enhance this later with actual barcode generation
            from PIL import Image, ImageDraw, ImageFont
            import qrcode  # Optional: install with 'pip install qrcode[pil]'
            
            # Try to generate QR code as fallback
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(barcode_number)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{img_base64}"
            
        except ImportError:
            # If PIL/qrcode not installed, return None
            return None
        except Exception as e:
            print(f"Error creating barcode image: {e}")
            return None