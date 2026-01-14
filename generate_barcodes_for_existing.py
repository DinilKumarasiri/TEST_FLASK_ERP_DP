#!/usr/bin/env python
"""
Script to generate barcodes for existing products
Location: Place this file in your project root directory (same level as run.py)
"""
import sys
import os
import re

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def generate_barcodes_for_existing():
    """Generate barcodes for all existing products"""
    try:
        # Import after adding to path
        from app import create_app, db
        from app.models import Product
        
        app = create_app()
        
        with app.app_context():
            # Get all products without barcodes
            products = Product.query.filter(
                (Product.barcode == None) | (Product.barcode == ''),
                Product.is_active == True
            ).all()
            
            print(f"=== Generating Barcodes for Existing Products ===")
            print(f"Found {len(products)} products without barcodes")
            print("-" * 50)
            
            if not products:
                print("No products need barcodes. All products already have barcodes!")
                return
            
            updated_count = 0
            skipped_count = 0
            
            for i, product in enumerate(products, 1):
                try:
                    print(f"\n[{i}/{len(products)}] Processing: {product.name}")
                    print(f"  SKU: {product.sku}")
                    print(f"  ID: {product.id}")
                    
                    # Generate barcode from SKU or ID
                    if product.sku:
                        # Clean SKU to create barcode (remove special characters)
                        barcode = re.sub(r'[^A-Za-z0-9]', '', product.sku)
                        if len(barcode) < 8:
                            barcode = barcode.zfill(12)
                        barcode_number = barcode[:12]
                        print(f"  Generated from SKU: {barcode_number}")
                    else:
                        # Use product ID padded to 12 digits
                        barcode_number = str(product.id).zfill(12)
                        print(f"  Generated from ID: {barcode_number}")
                    
                    # Generate online barcode URL
                    barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code=Code128&dpi=96"
                    
                    # Update product
                    product.barcode = barcode_number
                    product.barcode_image = barcode_url
                    
                    updated_count += 1
                    print(f"  ✅ Barcode assigned: {barcode_number}")
                    
                except Exception as e:
                    skipped_count += 1
                    print(f"  ❌ Error: {e}")
                    continue
            
            try:
                db.session.commit()
                print("\n" + "=" * 50)
                print(f"✅ SUCCESS: Generated barcodes for {updated_count} products")
                if skipped_count > 0:
                    print(f"⚠️  Skipped {skipped_count} products due to errors")
                print("=" * 50)
                
                # Show summary
                if updated_count > 0:
                    print("\n📊 Summary of updated products:")
                    updated_products = Product.query.filter(
                        Product.id.in_([p.id for p in products[:10]])  # Show first 10
                    ).all()
                    
                    for prod in updated_products[:10]:  # Show first 10
                        print(f"  - {prod.name}: {prod.barcode}")
                    
                    if len(updated_products) > 10:
                        print(f"  ... and {len(updated_products) - 10} more")
                
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ ERROR committing changes: {e}")
                return False
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def verify_barcodes():
    """Verify barcode generation results"""
    try:
        from app import create_app, db
        from app.models import Product
        
        app = create_app()
        
        with app.app_context():
            total_products = Product.query.filter_by(is_active=True).count()
            products_with_barcode = Product.query.filter(
                Product.barcode != None,
                Product.barcode != '',
                Product.is_active == True
            ).count()
            
            print("\n" + "=" * 50)
            print("📊 BARCODE VERIFICATION REPORT")
            print("=" * 50)
            print(f"Total active products: {total_products}")
            print(f"Products with barcode: {products_with_barcode}")
            print(f"Products without barcode: {total_products - products_with_barcode}")
            
            if total_products > 0:
                percentage = (products_with_barcode / total_products) * 100
                print(f"Barcode coverage: {percentage:.1f}%")
            
            # Show sample of products without barcodes
            products_without = Product.query.filter(
                (Product.barcode == None) | (Product.barcode == ''),
                Product.is_active == True
            ).limit(5).all()
            
            if products_without:
                print(f"\n📝 Sample products still needing barcodes (max 5):")
                for prod in products_without:
                    print(f"  - {prod.name} (ID: {prod.id}, SKU: {prod.sku})")
    
    except Exception as e:
        print(f"Error in verification: {e}")

if __name__ == '__main__':
    print("🚀 Starting Barcode Generation Process")
    print("=" * 60)
    
    success = generate_barcodes_for_existing()
    
    if success:
        verify_barcodes()
        
        print("\n" + "=" * 60)
        print("✅ Barcode generation process completed!")
        print("\n📋 Next steps:")
        print("1. Check products in the inventory")
        print("2. Use barcode scanning in POS")
        print("3. Print barcode labels if needed")
        print("=" * 60)
    else:
        print("\n❌ Barcode generation failed!")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure you're in the project root directory")
        print("2. Check if database is accessible")
        print("3. Verify the app structure is correct")
        print("=" * 60)