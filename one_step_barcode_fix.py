#!/usr/bin/env python
"""
One-step solution for barcode generation
"""
import sqlite3
import os
import re

def main():
    db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🚀 Starting barcode generation...")
    
    # Step 1: Add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN barcode VARCHAR(100)")
        print("✅ Added 'barcode' column")
    except:
        print("ℹ️  'barcode' column already exists")
    
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN barcode_image VARCHAR(200)")
        print("✅ Added 'barcode_image' column")
    except:
        print("ℹ️  'barcode_image' column already exists")
    
    conn.commit()
    
    # Step 2: Generate barcodes for all products
    cursor.execute("SELECT id, name, sku FROM products WHERE is_active = 1")
    products = cursor.fetchall()
    
    print(f"\n📊 Processing {len(products)} active products...")
    
    updated = 0
    for product_id, name, sku in products:
        try:
            # Generate barcode
            if sku:
                barcode = re.sub(r'[^A-Za-z0-9]', '', sku)
                if len(barcode) < 8:
                    barcode = barcode.zfill(12)
                barcode_number = barcode[:12]
            else:
                barcode_number = str(product_id).zfill(12)
            
            # Update database
            cursor.execute("UPDATE products SET barcode = ?, barcode_image = ? WHERE id = ?",
                          (barcode_number, f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code=Code128&dpi=96", product_id))
            
            updated += 1
            print(f"  ✓ {name}: {barcode_number}")
            
        except Exception as e:
            print(f"  ✗ Error with {name}: {e}")
    
    # Commit changes
    conn.commit()
    
    # Show summary
    print(f"\n✅ Successfully updated {updated} products")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM products WHERE barcode IS NOT NULL AND barcode != ''")
    with_barcodes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    total = cursor.fetchone()[0]
    
    print(f"\n📊 Final Statistics:")
    print(f"  Total active products: {total}")
    print(f"  Products with barcodes: {with_barcodes}")
    print(f"  Coverage: {(with_barcodes/total*100):.1f}%")
    
    conn.close()
    
    print("\n🎉 Done! Barcodes have been generated for all products.")

if __name__ == '__main__':
    main()