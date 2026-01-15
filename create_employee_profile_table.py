# create_employee_profile_table.py
from app import create_app, db
from app.models import User, EmployeeProfile

app = create_app()

with app.app_context():
    # Check if table exists
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    
    if 'employee_profiles' not in inspector.get_table_names():
        print("Creating employee_profiles table...")
        EmployeeProfile.__table__.create(db.engine)
        print("Table created successfully!")
    else:
        print("employee_profiles table already exists.")