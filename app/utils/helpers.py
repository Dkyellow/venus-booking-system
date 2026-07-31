import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
import pytz


def generate_booking_reference():
    date_str = datetime.utcnow().strftime('%Y%m%d')
    random_part = secrets.token_hex(3).upper()
    return f"APT-{date_str}-{random_part}"


def generate_unique_id(prefix='ID', length=8):
    return f"{prefix}-{uuid.uuid4().hex[:length].upper()}"


def format_datetime(dt, fmt='%Y-%m-%d %H:%M'):
    if dt is None:
        return ''
    return dt.strftime(fmt)


def format_date(dt, fmt='%Y-%m-%d'):
    if dt is None:
        return ''
    return dt.strftime(fmt)


def format_time(dt, fmt='%I:%M %p'):
    if dt is None:
        return ''
    return dt.strftime(fmt)


def format_currency(amount):
    if amount is None:
        return '$0.00'
    return f"${amount:,.2f}"


def get_local_time(timezone_str='UTC'):
    tz = pytz.timezone(timezone_str)
    return datetime.now(tz)


def time_ago(dt):
    now = datetime.utcnow()
    diff = now - dt
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "just now"


def mask_email(email):
    if not email or '@' not in email:
        return email
    local, domain = email.split('@')
    if len(local) <= 2:
        masked = local[0] + '*' * (len(local) - 1)
    else:
        masked = local[:2] + '*' * (len(local) - 2)
    return f"{masked}@{domain}"


def mask_phone(phone):
    if not phone or len(phone) < 4:
        return phone
    return '*' * (len(phone) - 4) + phone[-4:]


def paginate_query(query, page, per_page=20):
    return query.paginate(page=page, per_page=per_page, error_out=False)


def get_pagination_range(page, total_pages, window=5):
    if total_pages <= window:
        return list(range(1, total_pages + 1))
    
    start = max(1, page - window // 2)
    end = min(total_pages, start + window - 1)
    
    if end - start < window - 1:
        start = max(1, end - window + 1)
    
    return list(range(start, end + 1))