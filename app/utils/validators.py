import re
from email_validator import validate_email, EmailNotValidError


def validate_email_address(email):
    try:
        valid = validate_email(email)
        return True, valid.email
    except EmailNotValidError as e:
        return False, str(e)


def validate_phone(phone):
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    if not cleaned.isdigit():
        return False, 'Phone number must contain only digits'
    if len(cleaned) < 7 or len(cleaned) > 15:
        return False, 'Phone number must be between 7 and 15 digits'
    return True, cleaned


def validate_name(name):
    if not name or len(name.strip()) < 2:
        return False, 'Name must be at least 2 characters'
    if len(name.strip()) > 100:
        return False, 'Name must not exceed 100 characters'
    if not re.match(r'^[a-zA-Z\s\-\'.]+$', name.strip()):
        return False, 'Name contains invalid characters'
    return True, name.strip()


def sanitize_input(text):
    if not text:
        return text
    import bleach
    return bleach.clean(text.strip(), tags=[], attributes={})


def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', password):
        errors.append('Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        errors.append('Password must contain at least one lowercase letter')
    if not re.search(r'\d', password):
        errors.append('Password must contain at least one digit')
    return len(errors) == 0, errors