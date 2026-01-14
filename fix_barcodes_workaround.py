#!/usr/bin/env python
"""
Complete barcode generator with automatic column creation
"""
import sys
import os
import sqlite3
import re

def check_and_create_columns(db_path):
    """Check if barcode columns exist, create them if not"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(products)")
        columns = [col[1] for col in cursor.fetchall()]
        
        changes_made = False
        
        # Add barcode column if needed
        if 'barcode' not in columns:
            print("  Creating 'barcode' column...")
            cursor.execute("ALTER TABLE products ADD COLUMN barcode VARCHAR(100)")
            changes_made = True
        
        # Add barcode_image column if needed
        if 'barcode_image' not in columns:
            print("  Creating 'barcode_image' column...")
            cursor.execute("ALTER TABLE products ADD COLUMN barcode_image VARCHAR(200)")
            changes_made = True
        
        if changes_made:
            conn.commit()
            print("  ✅ Database columns updated")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking/creating columns: {e}")
        return False

def generate_barcodes_complete():
    """Complete barcode generator with column creation"""
    
    # Database path
    db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    try:
        print("🔍 Checking database structure...")
        
        # Ensure columns exist
        if not check_and_create_columns(db_path):
            return False
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n🔍 Finding products without barcodes...")
        
        # Get products without barcodes (handle NULL or empty string)
        cursor.execute("""
            SELECT id, name, sku FROM products 
            WHERE (barcode IS NULL OR barcode = '' OR barcode = 'None') 
            AND is_active = 1
        """)
        
        products = cursor.fetchall()
        
        if not products:
            print("✅ All products already have barcodes!")
            
            # Show barcode statistics
            cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM products 
                WHERE (barcode IS NOT NULL AND barcode != '' AND barcode != 'None') 
                AND is_active = 1
            """)
            with_barcodes = cursor.fetchone()[0]
            
            print(f"\n📊 Statistics:")
            print(f"  Total active products: {total}")
            print(f"  Products with barcodes: {with_barcodes}")
            print(f"  Coverage: {(with_barcodes/total*100):.1f}%")
            
            conn.close()
            return True
        
        print(f"Found {len(products)} products without barcodes")
        print("-" * 50)
        
        updated_count = 0
        
        for idx, (product_id, product_name, sku) in enumerate(products, 1):
            try:
                print(f"\n[{idx}/{len(products)}] Processing: {product_name}")
                print(f"  SKU: {sku}")
                print(f"  ID: {product_id}")
                
                # Generate barcode from SKU or ID
                if sku:
                    # Clean SKU to create barcode (remove special characters)
                    barcode = re.sub(r'[^A-Za-z0-9]', '', sku)
                    if len(barcode) < 8:
                        barcode = barcode.zfill(12)
                    barcode_number = barcode[:12]
                    print(f"  Generated from SKU: {barcode_number}")
                else:
                    # Use product ID padded to 12 digits
                    barcode_number = str(product_id).zfill(12)
                    print(f"  Generated from ID: {barcode_number}")
                
                # Generate online barcode URL
                barcode_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode_number}&code=Code128&dpi=96"
                
                # Update product directly with SQL
                cursor.execute("""
                    UPDATE products 
                    SET barcode = ?, barcode_image = ?
                    WHERE id = ?
                """, (barcode_number, barcode_url, product_id))
                
                updated_count += 1
                print(f"  ✅ Barcode assigned: {barcode_number}")
                
            except Exception as e:
                print(f"  ❌ Error with {product_name}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        
        print("\n" + "=" * 50)
        print(f"✅ SUCCESS: Generated barcodes for {updated_count} products")
        print("=" * 50)
        
        # Show updated statistics
        print("\n📊 Updated Statistics:")
        cursor.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE (barcode IS NOT NULL AND barcode != '' AND barcode != 'None') 
            AND is_active = 1
        """)
        with_barcodes = cursor.fetchone()[0]
        
        print(f"  Total active products: {total}")
        print(f"  Products with barcodes: {with_barcodes}")
        print(f"  Coverage: {(with_barcodes/total*100):.1f}%")
        
        # Show sample of updated products
        print("\n📝 Sample of updated products:")
        cursor.execute("""
            SELECT name, barcode FROM products 
            WHERE barcode IS NOT NULL AND barcode != ''
            LIMIT 5
        """)
        sample = cursor.fetchall()
        for name, bcode in sample:
            print(f"  {name}: {bcode}")
        
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def backup_database():
    """Create a backup of the database before making changes"""
    import shutil
    import datetime
    
    db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"
    backup_dir = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\backups"
    
    if not os.path.exists(db_path):
        return False
    
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Create backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"mobile_shop_backup_{timestamp}.db")
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"📦 Database backed up to: {backup_path}")
        return True
    except Exception as e:
        print(f"⚠️  Could not create backup: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Complete Barcode Generation System")
    print("=" * 60)
    
    # Create backup first
    print("\n💾 Creating database backup...")
    backup_database()
    
    # Generate barcodes
    success = generate_barcodes_complete()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Barcode generation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your Flask application")
        print("2. Check products in /inventory/products")
        print("3. Use barcode scanning in POS")
        print("4. Print barcode labels if needed")
        print("=" * 60)
    else:
        print("\n❌ Barcode generation failed!")
        print("=" * 60)