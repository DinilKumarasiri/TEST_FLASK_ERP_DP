# migration/add_employee_barcode_simple.py
"""
Simplified migration script to add barcode support to employees
Run with: python migration/add_employee_barcode_simple.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from datetime import datetime
import time

def get_db_connection():
    """Get database connection from environment variables"""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    db_config = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'user': os.environ.get('DB_USER', 'root'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'mobile_shop'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'charset': 'utf8mb4'
    }
    
    return pymysql.connect(**db_config)

def add_employee_barcode_columns_simple():
    """Add barcode columns to employee tables - Simplified version"""
    print("Starting migration: Adding barcode support for employees...")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n1. Adding barcode columns to employee_profiles table...")
        
        # Check if columns already exist
        cursor.execute("SHOW COLUMNS FROM employee_profiles LIKE 'employee_barcode'")
        if cursor.fetchone():
            print("  - Column 'employee_barcode' already exists")
        else:
            cursor.execute("ALTER TABLE employee_profiles ADD COLUMN employee_barcode VARCHAR(100) UNIQUE NULL")
            print("  - Added column: employee_barcode")
        
        cursor.execute("SHOW COLUMNS FROM employee_profiles LIKE 'barcode_image'")
        if cursor.fetchone():
            print("  - Column 'barcode_image' already exists")
        else:
            cursor.execute("ALTER TABLE employee_profiles ADD COLUMN barcode_image VARCHAR(200) NULL")
            print("  - Added column: barcode_image")
        
        cursor.execute("SHOW COLUMNS FROM employee_profiles LIKE 'barcode_generated_at'")
        if cursor.fetchone():
            print("  - Column 'barcode_generated_at' already exists")
        else:
            cursor.execute("ALTER TABLE employee_profiles ADD COLUMN barcode_generated_at DATETIME NULL")
            print("  - Added column: barcode_generated_at")
        
        cursor.execute("SHOW COLUMNS FROM employee_profiles LIKE 'barcode_scans_count'")
        if cursor.fetchone():
            print("  - Column 'barcode_scans_count' already exists")
        else:
            cursor.execute("ALTER TABLE employee_profiles ADD COLUMN barcode_scans_count INTEGER DEFAULT 0")
            print("  - Added column: barcode_scans_count")
        
        print("\n2. Creating attendance_logs table...")
        
        # Check if table exists
        cursor.execute("SHOW TABLES LIKE 'attendance_logs'")
        if cursor.fetchone():
            print("  - Table 'attendance_logs' already exists")
        else:
            create_table_sql = """
            CREATE TABLE attendance_logs (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                employee_id INTEGER NOT NULL,
                scan_type VARCHAR(20) NOT NULL,
                scan_time DATETIME NOT NULL,
                barcode_used VARCHAR(100) NOT NULL,
                location VARCHAR(100),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
            cursor.execute(create_table_sql)
            
            # Add indexes
            cursor.execute("CREATE INDEX idx_attendance_logs_employee_date ON attendance_logs (employee_id, DATE(scan_time))")
            cursor.execute("CREATE INDEX idx_attendance_logs_scan_time ON attendance_logs (scan_time)")
            
            print("  - Created table: attendance_logs")
            print("  - Added indexes")
        
        print("\n3. Generating barcodes for existing employees...")
        
        # Get all employee profiles
        cursor.execute("""
            SELECT ep.id, ep.user_id, ep.employee_code, u.username 
            FROM employee_profiles ep
            JOIN users u ON ep.user_id = u.id
            WHERE (ep.employee_barcode IS NULL OR ep.employee_barcode = '')
        """)
        
        employees = cursor.fetchall()
        print(f"  - Found {len(employees)} employees without barcodes")
        
        barcodes_generated = 0
        for emp_id, user_id, employee_code, username in employees:
            try:
                # Generate unique barcode
                timestamp = int(time.time() * 1000) % 1000000
                
                # Use employee code or user ID as base
                if employee_code:
                    base = ''.join(c for c in str(employee_code) if c.isalnum())[:6].upper()
                else:
                    base = f"EMP{user_id:04d}"[:6]
                
                random_part = str(timestamp % 10000).zfill(4)
                barcode = f"{base}{timestamp:06d}{random_part}"
                
                # Ensure proper length
                if len(barcode) < 12:
                    barcode = barcode.ljust(12, '0')
                elif len(barcode) > 13:
                    barcode = barcode[:13]
                
                # Add check digit
                if len(barcode) == 12:
                    digits = [int(d) for d in barcode[:12]]
                    odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
                    even_sum = sum(digits[i] for i in range(1, 12, 2))
                    total = odd_sum + even_sum
                    check_digit = (10 - (total % 10)) % 10
                    barcode = barcode + str(check_digit)
                
                # Update employee profile
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                update_sql = """
                    UPDATE employee_profiles 
                    SET employee_barcode = %s, 
                        barcode_generated_at = %s,
                        barcode_image = %s
                    WHERE id = %s
                """
                barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode}&code=Code128&dpi=96"
                
                cursor.execute(update_sql, (barcode, current_time, barcode_image_url, emp_id))
                barcodes_generated += 1
                
                if barcodes_generated <= 5:  # Only print first 5 for brevity
                    print(f"    Generated barcode for {username}: {barcode}")
                
            except Exception as e:
                print(f"    Error generating barcode for employee {emp_id}: {e}")
                continue
        
        conn.commit()
        
        print(f"\nMigration completed successfully!")
        print(f"- Added barcode columns to employee_profiles table")
        print(f"- Created attendance_logs table")
        print(f"- Generated barcodes for {barcodes_generated} employees")
        
        return True
        
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    success = add_employee_barcode_columns_simple()
    sys.exit(0 if success else 1)