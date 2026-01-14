# add_barcode_columns.py
import sqlite3
import os
import sys

def add_columns_to_stock_items():
    """Add item_barcode and is_serialized columns to stock_items table"""
    
    # Find the database file
    db_paths = [
        'instance/database.db',
        'mobile_shop.db',
        'app/instance/database.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            print(f"Found database at: {path}")
            break
    
    if not db_path:
        print("ERROR: Could not find database file!")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Connected to database successfully!")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(stock_items)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Existing columns in stock_items: {columns}")
        
        # Add item_barcode column if it doesn't exist
        if 'item_barcode' not in columns:
            print("Adding item_barcode column...")
            cursor.execute("ALTER TABLE stock_items ADD COLUMN item_barcode TEXT")
            print("✓ Added item_barcode column")
        
        # Add is_serialized column if it doesn't exist
        if 'is_serialized' not in columns:
            print("Adding is_serialized column...")
            cursor.execute("ALTER TABLE stock_items ADD COLUMN is_serialized BOOLEAN DEFAULT 0")
            print("✓ Added is_serialized column")
        
        # Create unique index on item_barcode
        print("Creating unique index on item_barcode...")
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_stock_item_barcode 
            ON stock_items(item_barcode) 
            WHERE item_barcode IS NOT NULL
        """)
        print("✓ Created unique index")
        
        # Commit changes
        conn.commit()
        print("\n✅ Database update completed successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(stock_items)")
        new_columns = cursor.fetchall()
        print("\nUpdated table structure:")
        print("=" * 60)
        for col in new_columns:
            print(f"{col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else 'NULL':10}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def generate_barcodes_for_existing_items():
    """Generate barcodes for existing stock items that don't have them"""
    
    db_paths = [
        'instance/database.db',
        'mobile_shop.db',
        'app/instance/database.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("ERROR: Could not find database file!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all stock items without barcodes
        cursor.execute("""
            SELECT si.id, p.sku, p.name 
            FROM stock_items si
            LEFT JOIN products p ON si.product_id = p.id
            WHERE si.item_barcode IS NULL OR si.item_barcode = ''
            ORDER BY si.id
        """)
        
        items = cursor.fetchall()
        print(f"\nFound {len(items)} items without barcodes")
        
        if items:
            print("\nGenerating barcodes...")
            count = 0
            
            for item_id, sku, product_name in items:
                # Generate unique barcode
                if sku:
                    # Clean SKU for barcode
                    clean_sku = ''.join(c for c in sku if c.isalnum())[:6]
                    barcode = f"{clean_sku}{item_id:06d}"
                else:
                    barcode = f"IT{item_id:08d}"
                
                # Ensure 12-13 characters
                if len(barcode) < 12:
                    barcode = barcode.zfill(12)
                elif len(barcode) > 13:
                    barcode = barcode[:13]
                
                # Update the item
                cursor.execute("""
                    UPDATE stock_items 
                    SET item_barcode = ?, is_serialized = 1 
                    WHERE id = ?
                """, (barcode, item_id))
                
                count += 1
                if count % 10 == 0:
                    print(f"  Processed {count} items...")
            
            conn.commit()
            print(f"\n✅ Generated barcodes for {count} items")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("STOCK ITEMS BARCODE MIGRATION")
    print("=" * 60)
    
    # Step 1: Add columns
    print("\nStep 1: Adding columns to stock_items table...")
    add_columns_to_stock_items()
    
    # Step 2: Generate barcodes for existing items
    print("\n" + "=" * 60)
    print("Step 2: Generating barcodes for existing items...")
    generate_barcodes_for_existing_items()
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE!")
    print("=" * 60)