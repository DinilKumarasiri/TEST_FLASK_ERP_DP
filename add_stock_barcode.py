#!/usr/bin/env python
"""
Add barcode support to stock items
"""
import sqlite3
import os
import re

def migrate_stock_barcodes():
    """Add barcode columns to stock_items table"""
    db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🛠️  Adding barcode support to stock_items table...")
        
        # Check current columns
        cursor.execute("PRAGMA table_info(stock_items)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add item_barcode column (unique per stock item)
        if 'item_barcode' not in columns:
            print("  Adding 'item_barcode' column...")
            cursor.execute("ALTER TABLE stock_items ADD COLUMN item_barcode VARCHAR(100) UNIQUE")
            print("  ✅ 'item_barcode' column added")
        else:
            print("  ⚠️  'item_barcode' column already exists")
        
        # Add is_serialized column
        if 'is_serialized' not in columns:
            print("  Adding 'is_serialized' column...")
            cursor.execute("ALTER TABLE stock_items ADD COLUMN is_serialized BOOLEAN DEFAULT 0")
            print("  ✅ 'is_serialized' column added")
        else:
            print("  ⚠️  'is_serialized' column already exists")
        
        conn.commit()
        
        # Verify changes
        print("\n🔍 Verifying stock_items table structure...")
        cursor.execute("PRAGMA table_info(stock_items)")
        new_columns = cursor.fetchall()
        
        print("\n📋 Updated stock_items table structure:")
        for col in new_columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Count stock items
        cursor.execute("SELECT COUNT(*) FROM stock_items")
        total = cursor.fetchone()[0]
        print(f"\n📊 Total stock items: {total}")
        
        conn.close()
        
        print("\n✅ Stock item barcode columns added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_stock_item_barcodes():
    """Generate unique barcodes for existing stock items"""
    db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔧 Generating unique barcodes for stock items...")
        
        # Get all stock items without barcodes
        cursor.execute("""
            SELECT si.id, si.product_id, p.sku, p.name 
            FROM stock_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.item_barcode IS NULL OR si.item_barcode = ''
            AND si.status = 'available'
        """)
        
        stock_items = cursor.fetchall()
        
        if not stock_items:
            print("✅ All stock items already have unique barcodes!")
            conn.close()
            return True
        
        print(f"Found {len(stock_items)} stock items without unique barcodes")
        print("-" * 50)
        
        updated_count = 0
        
        for idx, (stock_id, product_id, sku, product_name) in enumerate(stock_items, 1):
            try:
                print(f"\n[{idx}/{len(stock_items)}] Processing: {product_name}")
                print(f"  Stock ID: {stock_id}")
                print(f"  Product SKU: {sku}")
                
                # Generate unique barcode
                # Format: SKU + StockID + Check digit
                base_code = f"{re.sub(r'[^A-Za-z0-9]', '', sku)}{stock_id:06d}"
                
                # Add check digit (simple Luhn-like algorithm)
                check_digit = sum(int(d) for d in base_code if d.isdigit()) % 10
                barcode_number = f"{base_code}{check_digit}"
                
                # Ensure 12-13 digits for standard barcode
                if len(barcode_number) < 12:
                    barcode_number = barcode_number.zfill(12)
                elif len(barcode_number) > 13:
                    barcode_number = barcode_number[:13]
                
                print(f"  Generated unique barcode: {barcode_number}")
                
                # Update stock item
                cursor.execute("""
                    UPDATE stock_items 
                    SET item_barcode = ?, is_serialized = 1
                    WHERE id = ?
                """, (barcode_number, stock_id))
                
                updated_count += 1
                print(f"  ✅ Barcode assigned")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
        
        conn.commit()
        
        print(f"\n✅ Generated unique barcodes for {updated_count} stock items")
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM stock_items WHERE item_barcode IS NOT NULL")
        with_barcodes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM stock_items")
        total_stock = cursor.fetchone()[0]
        
        print(f"\n📊 Stock Item Barcode Statistics:")
        print(f"  Total stock items: {total_stock}")
        print(f"  Items with unique barcodes: {with_barcodes}")
        print(f"  Coverage: {(with_barcodes/total_stock*100):.1f}%")
        
        # Show sample
        print("\n📝 Sample serialized items:")
        cursor.execute("""
            SELECT p.name, si.item_barcode 
            FROM stock_items si
            JOIN products p ON si.product_id = p.id
            WHERE si.item_barcode IS NOT NULL
            LIMIT 5
        """)
        samples = cursor.fetchall()
        for name, barcode in samples:
            print(f"  {name}: {barcode}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 Adding Unique Barcode Support for Stock Items")
    print("=" * 60)
    
    # Step 1: Add columns
    print("\n📋 Step 1: Adding database columns...")
    if not migrate_stock_barcodes():
        print("\n❌ Failed to add columns!")
        exit(1)
    
    # Step 2: Generate barcodes
    print("\n📋 Step 2: Generating unique barcodes...")
    if not generate_stock_item_barcodes():
        print("\n❌ Failed to generate barcodes!")
        exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Unique barcode system implemented successfully!")
    print("\n📋 Next steps:")
    print("1. Update your models with new columns")
    print("2. Modify stock-in process to generate unique barcodes")
    print("3. Update POS to scan individual item barcodes")
    print("=" * 60)