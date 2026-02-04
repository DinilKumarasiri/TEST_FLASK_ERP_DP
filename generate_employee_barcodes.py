# generate_barcodes_simple.py
"""
Simple script to generate barcodes for employees without app context issues
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
from datetime import datetime
import time
import random
import string

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
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    return pymysql.connect(**db_config)

def generate_barcode(employee_code=None, user_id=None):
    """Generate a unique barcode for an employee"""
    timestamp = int(time.time() * 1000) % 1000000
    
    # Use employee code or user ID as base
    if employee_code and employee_code != 'None':
        # Clean the employee code
        base = ''.join(c for c in str(employee_code) if c.isalnum())[:6].upper()
        if len(base) < 4:
            base = base.ljust(4, 'X')
    else:
        base = f"EMP{user_id:04d}"[:6]
    
    random_part = ''.join(random.choices(string.digits, k=4))
    barcode = f"{base}{timestamp:06d}{random_part}"
    
    # Ensure proper length (12-13 digits)
    if len(barcode) < 12:
        barcode = barcode.ljust(12, '0')
    elif len(barcode) > 13:
        barcode = barcode[:13]
    
    # Add check digit (EAN-13 style)
    if len(barcode) == 12:
        try:
            digits = [int(d) for d in barcode[:12]]
            odd_sum = sum(digits[i] * 3 for i in range(0, 12, 2))
            even_sum = sum(digits[i] for i in range(1, 12, 2))
            total = odd_sum + even_sum
            check_digit = (10 - (total % 10)) % 10
            barcode = barcode + str(check_digit)
        except:
            # If check digit calculation fails, add a random digit
            barcode = barcode + str(random.randint(0, 9))
    
    return barcode

def generate_missing_barcodes_simple():
    """Generate barcodes for employees without them - simple version"""
    print("Generating barcodes for employees...")
    
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, check if barcode columns exist
        print("\n1. Checking database structure...")
        
        # Check for barcode columns
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'employee_profiles' 
            AND COLUMN_NAME IN ('employee_barcode', 'barcode_image', 'barcode_generated_at', 'barcode_scans_count')
        """)
        
        existing_columns = [row['COLUMN_NAME'] for row in cursor.fetchall()]
        required_columns = ['employee_barcode', 'barcode_image', 'barcode_generated_at', 'barcode_scans_count']
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"  Warning: Missing columns: {', '.join(missing_columns)}")
            print("  Please run the migration script first: python migration/add_employee_barcode_simple.py")
            return False
        
        print("  All required columns exist ✓")
        
        # Get all employee profiles without barcodes
        print("\n2. Finding employees without barcodes...")
        
        cursor.execute("""
            SELECT ep.id, ep.user_id, ep.employee_code, u.username, 
                   ep.full_name, ep.employee_barcode
            FROM employee_profiles ep
            JOIN users u ON ep.user_id = u.id
            WHERE ep.employee_barcode IS NULL OR ep.employee_barcode = '' OR ep.employee_barcode = 'None'
            ORDER BY u.username
        """)
        
        employees = cursor.fetchall()
        
        if not employees:
            print("  No employees found without barcodes!")
            return True
        
        print(f"  Found {len(employees)} employees without barcodes")
        
        # Get existing barcodes to avoid duplicates
        cursor.execute("SELECT employee_barcode FROM employee_profiles WHERE employee_barcode IS NOT NULL AND employee_barcode != '' AND employee_barcode != 'None'")
        existing_barcodes = {row['employee_barcode'] for row in cursor.fetchall()}
        
        print("\n3. Generating barcodes...")
        
        generated_count = 0
        failed_count = 0
        
        for emp in employees:
            emp_id = emp['id']
            user_id = emp['user_id']
            emp_code = emp['employee_code']
            username = emp['username']
            full_name = emp['full_name']
            current_barcode = emp['employee_barcode']
            
            try:
                # Generate unique barcode
                max_attempts = 10
                barcode = None
                
                for attempt in range(max_attempts):
                    barcode = generate_barcode(emp_code, user_id)
                    
                    # Check if barcode is unique
                    if barcode not in existing_barcodes:
                        existing_barcodes.add(barcode)
                        break
                    
                    # Wait a bit and try again
                    time.sleep(0.001)
                    
                    if attempt == max_attempts - 1:
                        # Last resort: use timestamp with random suffix
                        barcode = f"U{int(time.time() * 1000000)}{user_id}"
                        if len(barcode) > 13:
                            barcode = barcode[:13]
                
                # Create barcode image URL
                barcode_image_url = f"https://barcode.tec-it.com/barcode.ashx?data={barcode}&code=Code128&dpi=96&dataseparator="
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Update employee profile
                update_sql = """
                    UPDATE employee_profiles 
                    SET employee_barcode = %s, 
                        barcode_image = %s,
                        barcode_generated_at = %s,
                        barcode_scans_count = 0
                    WHERE id = %s
                """
                
                cursor.execute(update_sql, (barcode, barcode_image_url, current_time, emp_id))
                
                generated_count += 1
                
                # Print progress
                if generated_count <= 10 or generated_count % 10 == 0:
                    display_name = full_name if full_name and full_name != 'None' else username
                    print(f"  [{generated_count}] {display_name}: {barcode}")
                
                # Small delay to ensure unique timestamps
                time.sleep(0.001)
                
            except Exception as e:
                failed_count += 1
                print(f"  Error for {username}: {str(e)}")
                continue
        
        conn.commit()
        
        print(f"\n4. Summary:")
        print(f"   Successfully generated: {generated_count} barcodes")
        print(f"   Failed: {failed_count}")
        
        if generated_count > 0:
            # Verify the update
            cursor.execute("SELECT COUNT(*) as count FROM employee_profiles WHERE employee_barcode IS NOT NULL AND employee_barcode != '' AND employee_barcode != 'None'")
            total_with_barcodes = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as total FROM employee_profiles")
            total_employees = cursor.fetchone()['total']
            
            print(f"\n5. Verification:")
            print(f"   Total employees: {total_employees}")
            print(f"   With barcodes: {total_with_barcodes}")
            print(f"   Without barcodes: {total_employees - total_with_barcodes}")
        
        return True
        
    except Exception as e:
        print(f"\nError during barcode generation: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("Employee Barcode Generator")
    print("=" * 60)
    
    success = generate_missing_barcodes_simple()
    
    print("\n" + "=" * 60)
    if success:
        print("Barcode generation completed successfully!")
    else:
        print("Barcode generation failed!")
    print("=" * 60)
    
    sys.exit(0 if success else 1)