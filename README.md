# Flask ERP System

A comprehensive ERP system for mobile phone repair shops built with Flask.

## Features

- User management with role-based access control
- Inventory management
- Point of Sale (POS) system
- Repair job management
- Customer management
- Supplier management
- Employee attendance and leave management
- Commission tracking
- Sales reporting

## Quick Start

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Set up the database:

   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

3. Run the application:

   ```bash
   flask run
   ```

4. Initialize sample data (optional):
   ```bash
   python init_sample_data.py
   ```

## Default Login Credentials

- **Admin**: username: `admin`, password: `admin123`
- **Manager**: username: `manager`, password: `manager123`
- **Technician**: username: `technician1`, password: `tech123`
- **Staff**: username: `staff1`, password: `staff123`

## Optimization Notes

The application startup has been optimized by:

- Moving sample data initialization to a separate script
- Fixing SQLAlchemy relationship warnings
- Reducing database queries during startup

For development, run `python init_sample_data.py` once to populate the database with sample data.
