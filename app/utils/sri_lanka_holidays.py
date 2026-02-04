# app/utils/sri_lanka_holidays.py
"""
Sri Lanka public holidays helper
"""
from datetime import date, datetime, timedelta
import pytz

SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

def get_sri_lanka_holidays(year=None):
    """Get list of Sri Lanka public holidays for a given year"""
    if year is None:
        year = datetime.now(SRI_LANKA_TZ).year
    
    holidays = []
    
    # Fixed date holidays
    holidays.append(date(year, 1, 1))    # New Year's Day
    holidays.append(date(year, 1, 14))   # Tamil Thai Pongal Day
    holidays.append(date(year, 2, 4))    # National Day
    holidays.append(date(year, 4, 13))   # Sinhala and Tamil New Year Eve
    holidays.append(date(year, 4, 14))   # Sinhala and Tamil New Year
    holidays.append(date(year, 5, 1))    # May Day
    holidays.append(date(year, 12, 25))  # Christmas Day
    
    # Variable date holidays (Buddhist)
    # These need calculation - simplified for now
    # Add actual calculation for Vesak, Poson, etc.
    
    return holidays

def is_sri_lanka_holiday(check_date=None):
    """Check if a date is a public holiday in Sri Lanka"""
    if check_date is None:
        check_date = datetime.now(SRI_LANKA_TZ).date()
    
    holidays = get_sri_lanka_holidays(check_date.year)
    return check_date in holidays

def is_sri_lanka_working_day(check_date=None):
    """Check if a date is a working day in Sri Lanka (not Sunday or holiday)"""
    if check_date is None:
        check_date = datetime.now(SRI_LANKA_TZ).date()
    
    # Sunday is not a working day
    if check_date.weekday() == 6:  # Sunday
        return False
    
    # Check if it's a holiday
    if is_sri_lanka_holiday(check_date):
        return False
    
    return True