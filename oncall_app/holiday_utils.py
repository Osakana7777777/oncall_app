import datetime as _dt

try:
    import jpholiday
    def is_holiday(day: _dt.date) -> bool: 
        return jpholiday.is_holiday(day)
except ImportError:
    jpholiday = None
    def is_holiday(day: _dt.date) -> bool: 
        return False