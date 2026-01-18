#!/usr/bin/env python3
"""
One-click MySQL migration script
Run this file and everything will be set up automatically
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a shell command"""
    print(f"\n📝 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} successful")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🔧 Mobile Shop ERP - Auto MySQL Migration")
    print("="*50)
    
    # Step 1: Install required packages
    print("\n1️⃣ Installing required packages...")
    packages = ['pymysql', 'sqlalchemy']
    
    for package in packages:
        run_command(f"pip install {package}", f"Install {package}")
    
    # Step 2: Check if setup_mysql.py exists
    if not os.path.exists('setup_mysql.py'):
        print("\n❌ Error: setup_mysql.py not found!")
        print("Please make sure you're in the project root directory")
        return False
    
    # Step 3: Run the migration
    print("\n2️⃣ Running MySQL migration...")
    try:
        # Run the setup_mysql.py script
        import setup_mysql
        if hasattr(setup_mysql, 'main'):
            success = setup_mysql.main()
            if success:
                print("\n✅ All done! Your application is ready for MySQL.")
                return True
            else:
                print("\n❌ Migration failed. Please check the error messages above.")
                return False
        else:
            print("\n❌ setup_mysql.py doesn't have a main() function")
            return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def check_xampp():
    """Check if XAMPP is installed"""
    print("\n🔍 Checking for XAMPP...")
    
    # Common XAMPP installation paths
    xampp_paths = [
        r"C:\xampp",
        r"D:\xampp",
        r"C:\Program Files\xampp",
        "/Applications/XAMPP",
        "/opt/lampp"
    ]
    
    for path in xampp_paths:
        if os.path.exists(path):
            print(f"✅ XAMPP found at: {path}")
            return True
    
    print("⚠️ XAMPP not found in common locations")
    print("Please ensure XAMPP is installed and MySQL service is running")
    return True  # Continue anyway, user might have MySQL elsewhere

if __name__ == '__main__':
    print("📱 This script will migrate your app from SQLite to MySQL")
    print("Requirements:")
    print("  • XAMPP installed with MySQL running")
    print("  • Python 3.6+ installed")
    print("  • Internet connection (for package downloads)")
    
    response = input("\nDo you want to continue? (yes/no): ").lower()
    
    if response in ['yes', 'y', '']:
        # Check XAMPP
        check_xampp()
        
        # Run migration
        if main():
            print("\n" + "="*50)
            print("🎉 Setup Complete!")
            print("\nNext Steps:")
            print("1. Start XAMPP Control Panel")
            print("2. Start Apache and MySQL services")
            print("3. Run: python run.py")
            print("4. Open: http://localhost:5000")
            print("\nLogin with: admin / admin123")
            print("="*50)
        else:
            print("\n❌ Setup failed. Please check the errors above.")
    else:
        print("Setup cancelled.")