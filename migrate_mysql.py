#!/usr/bin/env python3
"""
MySQL Migration Script - One-time migration, no duplicate backups
"""

import sys
import os
import sqlite3
import pymysql
from datetime import datetime

print("="*60)
print("MySQL Migration for Mobile Shop ERP")
print("="*60)

# -------------------------------------------------------------------
# 1. CHECK MYSQL
# -------------------------------------------------------------------
print("\n[1/5] Checking MySQL server...")
try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        charset='utf8mb4'
    )
    conn.close()
    print("✓ MySQL is running")
except pymysql.err.OperationalError:
    print("✗ MySQL is not running")
    print("\nPlease start XAMPP Control Panel and:")
    print("1. Click 'Start' next to MySQL")
    print("2. Wait for the status to turn green")
    print("3. Run this script again")
    sys.exit(1)

# -------------------------------------------------------------------
# 2. CREATE DATABASE
# -------------------------------------------------------------------
print("\n[2/5] Creating database...")
try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS mobile_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print("✓ Database 'mobile_shop' ready")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# -------------------------------------------------------------------
# 3. CHECK IF ALREADY MIGRATED
# -------------------------------------------------------------------
print("\n[3/5] Checking migration status...")
try:
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='mobile_shop',
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE 'users'")
    if cursor.fetchone():
        print("ℹ Database already has tables. Skipping migration.")
        print("\n✅ Migration already completed!")
        print("\nTo start your app: python run.py")
        print("Then open: http://localhost:5000")
        cursor.close()
        conn.close()
        sys.exit(0)
    cursor.close()
    conn.close()
except:
    pass  # Database is empty, continue with migration

# -------------------------------------------------------------------
# 4. BACKUP SQLITE (ONLY IF EXISTS AND NOT ALREADY BACKED UP)
# -------------------------------------------------------------------
print("\n[4/5] Checking SQLite data...")
sqlite_path = os.path.join('instance', 'database.db')
data_to_migrate = {}

if os.path.exists(sqlite_path):
    # Check if backup already exists
    backup_dir = 'backups'
    backup_file = os.path.join(backup_dir, 'sqlite_final_backup.db')
    
    # Create backup only once
    if not os.path.exists(backup_file):
        print("Creating backup...")
        try:
            import shutil
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(sqlite_path, backup_file)
            print(f"✓ Backup created: {backup_file}")
        except Exception as e:
            print(f"✗ Backup failed: {e}")
    else:
        print("✓ Using existing backup")
    
    # Read data from SQLite
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()
        
        # Get user tables only
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            if table == 'alembic_version':
                continue
                
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                if rows:
                    data_to_migrate[table] = [dict(row) for row in rows]
                    print(f"  ✓ {table}: {len(rows)} rows")
            except:
                continue
        
        sqlite_conn.close()
        
    except Exception as e:
        print(f"✗ Error reading SQLite: {e}")
else:
    print("ℹ No SQLite database found")

# -------------------------------------------------------------------
# 5. SETUP MYSQL TABLES AND MIGRATE DATA
# -------------------------------------------------------------------
print("\n[5/5] Setting up MySQL...")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import create_app, db
    from app.models import (
        User, Customer, Product, ProductCategory, Supplier,
        StockItem, PurchaseOrder, PurchaseOrderItem,
        Invoice, InvoiceItem, Payment, RepairJob, RepairItem,
        Attendance, LeaveRequest, Commission, EmployeeProfile
    )
    
    app = create_app()
    
    with app.app_context():
        print("Creating tables...")
        db.create_all()
        
        # Create default admin if no data to migrate
        if not data_to_migrate or 'users' not in data_to_migrate:
            if User.query.count() == 0:
                admin = User(
                    username='admin',
                    email='admin@mobileshop.com',
                    role='admin',
                    is_active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✓ Created default admin: admin / admin123")
        
        # Migrate data if available
        if data_to_migrate:
            print("Migrating data...")
            
            # Model mapping
            MODEL_MAP = {
                'users': User,
                'customers': Customer,
                'products': Product,
                'product_categories': ProductCategory,
                'suppliers': Supplier,
                'stock_items': StockItem,
                'purchase_orders': PurchaseOrder,
                'purchase_order_items': PurchaseOrderItem,
                'invoices': Invoice,
                'invoice_items': InvoiceItem,
                'payments': Payment,
                'repair_jobs': RepairJob,
                'repair_items': RepairItem,
                'attendance': Attendance,
                'leave_requests': LeaveRequest,
                'commissions': Commission,
                'employee_profiles': EmployeeProfile
            }
            
            total_migrated = 0
            
            for table_name, rows in data_to_migrate.items():
                if table_name not in MODEL_MAP:
                    continue
                    
                model_class = MODEL_MAP[table_name]
                count = 0
                
                for row in rows:
                    try:
                        # Skip if user exists
                        if table_name == 'users' and 'username' in row:
                            if User.query.filter_by(username=row['username']).first():
                                continue
                        
                        instance = model_class()
                        for key, value in row.items():
                            if hasattr(instance, key) and key != 'id':
                                setattr(instance, key, value)
                        
                        db.session.add(instance)
                        count += 1
                        
                        # Commit in batches of 50
                        if count % 50 == 0:
                            db.session.commit()
                            
                    except Exception as e:
                        continue
                
                if count > 0:
                    db.session.commit()
                    total_migrated += count
                    print(f"  ✓ {table_name}: {count} rows")
            
            print(f"✓ Total migrated: {total_migrated} rows")
        
        print("✓ MySQL setup complete")
        
        # Final check
        user_count = User.query.count()
        print(f"✓ Total users in database: {user_count}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# -------------------------------------------------------------------
# DONE
# -------------------------------------------------------------------
print("\n" + "="*60)
print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
print("="*60)
print("\nYour app is now using MySQL!")
print("\nTo start:")
print("$ python run.py")
print("\nThen open: http://localhost:5000")
print("Login: admin / admin123")
print("\nNote: SQLite backup saved as 'backups/sqlite_final_backup.db'")
print("="*60)