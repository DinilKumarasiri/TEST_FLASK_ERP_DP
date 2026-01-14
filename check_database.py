#!/usr/bin/env python
"""
Check database schema
"""
import sqlite3
import os

db_path = r"D:\AleneSoft\02. Projects\01. AleneSoft Product\01. AlenePro\01. AlenePro Product\Dinil app\TEST_FLASK_ERP_DP-main\TEST_FLASK_ERP_DP\mobile_shop.db"

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 Database Schema Check")
print("=" * 60)

# Check products table structure
print("\n🔍 Checking 'products' table structure:")
cursor.execute("PRAGMA table_info(products)")
columns = cursor.fetchall()

print("Columns in 'products' table:")
for col in columns:
    print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULLABLE'}")

# Check if barcode columns exist
barcode_exists = any(col[1] == 'barcode' for col in columns)
barcode_image_exists = any(col[1] == 'barcode_image' for col in columns)

print(f"\n📋 Barcode columns check:")
print(f"  'barcode' column exists: {barcode_exists}")
print(f"  'barcode_image' column exists: {barcode_image_exists}")

# Show sample data
print("\n📝 Sample products (first 5):")
cursor.execute("SELECT id, name, sku FROM products LIMIT 5")
products = cursor.fetchall()
for prod in products:
    print(f"  ID: {prod[0]}, Name: {prod[1]}, SKU: {prod[2]}")

conn.close()