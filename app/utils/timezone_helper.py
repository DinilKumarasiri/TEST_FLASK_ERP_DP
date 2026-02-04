# app/utils/timezone_helper.py
"""
Sri Lanka timezone helper functions
"""
from datetime import datetime, time as dt_time
import pytz
from flask import current_app

# Sri Lanka timezone
SRI_LANKA_TZ = pytz.timezone('Asia/Colombo')

def get_sri_lanka_time():
    """Get current time in Sri Lanka timezone"""
    return datetime.now(SRI_LANKA_TZ)

def get_sri_lanka_date():
    """Get current date in Sri Lanka timezone"""
    return get_sri_lanka_time().date()

def utc_to_sri_lanka(utc_dt):
    """Convert UTC datetime to Sri Lanka time"""
    if utc_dt is None:
        return None
    
    if utc_dt.tzinfo is None:
        # Assume UTC if no timezone info
        utc_dt = pytz.utc.localize(utc_dt)
    
    return utc_dt.astimezone(SRI_LANKA_TZ)

def sri_lanka_to_utc(sl_dt):
    """Convert Sri Lanka datetime to UTC"""
    if sl_dt is None:
        return None
    
    if sl_dt.tzinfo is None:
        # Localize to Sri Lanka timezone
        sl_dt = SRI_LANKA_TZ.localize(sl_dt)
    
    return sl_dt.astimezone(pytz.utc)

def format_sri_lanka_time(dt, format_str='%Y-%m-%d %H:%M:%S'):
    """Format datetime in Sri Lanka timezone"""
    if dt is None:
        return ''
    
    sl_time = utc_to_sri_lanka(dt) if dt.tzinfo else dt
    return sl_time.strftime(format_str)

def format_sri_lanka_date(dt, format_str='%Y-%m-%d'):
    """Format date in Sri Lanka timezone"""
    if dt is None:
        return ''
    
    sl_time = utc_to_sri_lanka(dt) if hasattr(dt, 'tzinfo') else dt
    return sl_time.strftime(format_str)

def is_business_hours_sri_lanka(check_time=None):
    """Check if current time is within Sri Lanka business hours"""
    if check_time is None:
        check_time = get_sri_lanka_time()
    
    # Get business hours from config
    from flask import current_app
    try:
        open_time_str = current_app.config.get('BUSINESS_OPEN_TIME', '08:30')
        close_time_str = current_app.config.get('BUSINESS_CLOSE_TIME', '17:30')
        
        open_time = dt_time(int(open_time_str.split(':')[0]), int(open_time_str.split(':')[1]))
        close_time = dt_time(int(close_time_str.split(':')[0]), int(close_time_str.split(':')[1]))
        
        current_time = check_time.time()
        
        # Check if within business hours
        return open_time <= current_time <= close_time
        
    except:
        # Default business hours 8:30 AM to 5:30 PM
        open_time = dt_time(8, 30)
        close_time = dt_time(17, 30)
        current_time = check_time.time()
        return open_time <= current_time <= close_time

def is_working_day_sri_lanka(check_date=None):
    """Check if date is a working day in Sri Lanka"""
    if check_date is None:
        check_date = get_sri_lanka_date()
    
    # Get working days from config
    from flask import current_app
    try:
        working_days = current_app.config.get('BUSINESS_DAYS', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'])
        day_name = check_date.strftime('%A')
        return day_name in working_days
    except:
        # Default: Monday to Saturday are working days
        day_name = check_date.strftime('%A')
        return day_name not in ['Sunday']

def get_sri_lanka_week_start(date_obj=None):
    """Get start of week (Monday) in Sri Lanka"""
    if date_obj is None:
        date_obj = get_sri_lanka_date()
    
    # Monday is start of week
    return date_obj - timedelta(days=date_obj.weekday())

def get_sri_lanka_month_start(date_obj=None):
    """Get start of month in Sri Lanka"""
    if date_obj is None:
        date_obj = get_sri_lanka_date()
    
    return date_obj.replace(day=1)

def sri_lanka_time_ago(value):
    """Format datetime as time ago in Sri Lanka context"""
    from app.utils.timezone_helper import get_sri_lanka_time
    
    if not value:
        return ''
    
    now = get_sri_lanka_time()
    
    if hasattr(value, 'date') and not hasattr(value, 'hour'):
        value = datetime.combine(value, dt_time.min)
        value = SRI_LANKA_TZ.localize(value)
    
    if hasattr(value, 'tzinfo') and value.tzinfo is None:
        value = SRI_LANKA_TZ.localize(value)
    
    diff = now - value
    
    # Sri Lanka specific time phrases
    if diff.days > 365:
        years = diff.days // 365
        return f'වසර {years}කට පෙර' if years == 1 else f'වසර {years}කට පෙර'
    elif diff.days > 30:
        months = diff.days // 30
        return f'මාස {months}කට පෙර' if months == 1 else f'මාස {months}කට පෙර'
    elif diff.days > 7:
        weeks = diff.days // 7
        return f'සති {weeks}කට පෙර' if weeks == 1 else f'සති {weeks}කට පෙර'
    elif diff.days > 0:
        return f'දින {diff.days}කට පෙර' if diff.days == 1 else f'දින {diff.days}කට පෙර'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'පැය {hours}කට පෙර' if hours == 1 else f'පැය {hours}කට පෙර'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'මිනිත්තු {minutes}කට පෙර' if minutes == 1 else f'මිනිත්තු {minutes}කට පෙර'
    elif diff.seconds > 0:
        return f'තත්පර {diff.seconds}කට පෙර' if diff.seconds == 1 else f'තත්පර {diff.seconds}කට පෙර'
    else:
        return 'දැන්'