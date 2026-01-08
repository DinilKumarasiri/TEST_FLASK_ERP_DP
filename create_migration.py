# create_migration.py
from app import create_app, db
from modules.models import StockItem

app = create_app()

with app.app_context():
    # Add created_by column to stock_items table
    from sqlalchemy import text
    
    try:
        # Check if column exists
        result = db.session.execute(text("PRAGMA table_info(stock_items)"))
        columns = [row[1] for row in result]
        
        if 'created_by' not in columns:
            print("Adding created_by column to stock_items table...")
            db.session.execute(text("ALTER TABLE stock_items ADD COLUMN created_by INTEGER"))
            db.session.execute(text("ALTER TABLE stock_items ADD COLUMN imei VARCHAR(50)"))
            db.session.commit()
            print("Migration successful!")
        else:
            print("created_by column already exists")
    except Exception as e:
        print(f"Error during migration: {e}")
        db.session.rollback()