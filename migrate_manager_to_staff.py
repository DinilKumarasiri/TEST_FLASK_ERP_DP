#!/usr/bin/env python3
"""
Migration script to change manager role to staff role.
Run this before deploying the code changes.
"""
import sys
import os

# Add the app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User

def migrate_roles():
    """Migrate all manager users to staff role"""
    app = create_app()
    
    with app.app_context():
        try:
            # Find all manager users
            managers = User.query.filter_by(role='manager').all()
            print(f"Found {len(managers)} manager users to migrate")
            
            # Update each manager to staff
            for manager in managers:
                print(f"Migrating: {manager.username} (ID: {manager.id}) from manager to staff")
                manager.role = 'staff'
            
            # Commit changes
            db.session.commit()
            print("Migration completed successfully!")
            
            # Verify migration
            remaining_managers = User.query.filter_by(role='manager').count()
            new_staff = User.query.filter_by(role='staff').count()
            print(f"\nVerification:")
            print(f"  - Remaining managers: {remaining_managers}")
            print(f"  - Total staff users: {new_staff}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")
            return False

if __name__ == '__main__':
    print("=" * 60)
    print("Migration: Manager Role to Staff Role")
    print("=" * 60)
    
    confirm = input("\nThis will change all 'manager' users to 'staff' role.\nContinue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        if migrate_roles():
            print("\n✅ Migration successful! You can now deploy the code changes.")
        else:
            print("\n❌ Migration failed. Check the error message above.")
    else:
        print("\nMigration cancelled.")