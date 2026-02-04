# test_sri_lanka_time.py
"""
Test Sri Lanka timezone implementation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.utils.timezone_helper import get_sri_lanka_time, utc_to_sri_lanka
from datetime import datetime
import pytz

def test_timezone():
    app = create_app()
    
    with app.app_context():
        print("Testing Sri Lanka Timezone Implementation")
        print("=" * 50)
        
        # Current time in Sri Lanka
        sl_time = get_sri_lanka_time()
        print(f"Current Sri Lanka Time: {sl_time}")
        print(f"Current Sri Lanka Date: {sl_time.date()}")
        print(f"Timezone: {sl_time.tzinfo}")
        
        # Test conversion
        utc_time = datetime.utcnow()
        print(f"\nUTC Time: {utc_time}")
        
        sl_converted = utc_to_sri_lanka(utc_time)
        print(f"Converted to Sri Lanka: {sl_converted}")
        
        # Check time difference
        diff = sl_converted - utc_time
        print(f"Time Difference: {diff}")
        
        # Test business hours
        from app.utils.timezone_helper import is_business_hours_sri_lanka
        print(f"\nIs Business Hours: {is_business_hours_sri_lanka()}")
        
        # Test working days
        from app.utils.timezone_helper import is_working_day_sri_lanka
        print(f"Is Working Day: {is_working_day_sri_lanka()}")
        
        print("\nTest completed successfully!")

if __name__ == '__main__':
    test_timezone()