#!/usr/bin/env python3
"""
Local Development Migration Script (Windows/WSL)
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Get the current directory (your Flask project root)
    app_root = os.getcwd()
    migration_message = "Make purchase_price optional"
    
    print(f"🚀 Starting LOCAL database migration: {migration_message}")
    print(f"📁 Working directory: {app_root}")
    print(f"🐍 Python: {sys.executable}")
    print("-" * 50)
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Not running in a virtual environment!")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Set FLASK_APP if not already set
    if 'FLASK_APP' not in os.environ:
        # Try to find the Flask app file
        possible_apps = ['app.py', 'application.py', 'run.py', 'wsgi.py']
        for app_file in possible_apps:
            if os.path.exists(os.path.join(app_root, app_file)):
                os.environ['FLASK_APP'] = app_file
                print(f"✅ Found Flask app: {app_file}")
                break
        
        if 'FLASK_APP' not in os.environ:
            print("❌ Could not find Flask app file")
            print("Please set FLASK_APP environment variable")
            return
    
    try:
        # Step 1: Create migration
        print(f"📝 Creating migration: {migration_message}")
        cmd1 = [sys.executable, '-m', 'flask', 'db', 'migrate', '-m', migration_message]
        
        print(f"Running: {' '.join(cmd1)}")
        result1 = subprocess.run(cmd1, capture_output=True, text=True, cwd=app_root)
        
        if result1.stdout:
            print("Output:", result1.stdout)
        if result1.stderr:
            print("Errors/Warnings:", result1.stderr)
        
        if result1.returncode == 0:
            print("✅ Migration created successfully")
        else:
            print("❌ Migration creation failed")
            # Continue anyway, maybe migration already exists
        
        print("-" * 50)
        
        # Step 2: Upgrade database
        print("⬆️  Upgrading database...")
        cmd2 = [sys.executable, '-m', 'flask', 'db', 'upgrade']
        
        print(f"Running: {' '.join(cmd2)}")
        result2 = subprocess.run(cmd2, capture_output=True, text=True, cwd=app_root)
        
        if result2.stdout:
            print("Output:", result2.stdout)
        if result2.stderr:
            print("Errors/Warnings:", result2.stderr)
        
        if result2.returncode == 0:
            print("✅ Database upgraded successfully")
        else:
            print("❌ Database upgrade failed")
            return
        
        print("-" * 50)
        print("🎉 Migration completed successfully!")
        
    except FileNotFoundError as e:
        print(f"❌ Command not found: {e}")
        print("Make sure Flask-Migrate is installed: pip install flask-migrate")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()