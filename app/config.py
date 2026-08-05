import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///venus_booking.db')
    
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'Venus Medical & Dental Centre <medical@venushealthcare.co.zw>')
    
    GOOGLE_CALENDAR_CLIENT_ID = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
    GOOGLE_CALENDAR_REDIRECT_URI = os.getenv('GOOGLE_CALENDAR_REDIRECT_URI', 'http://localhost:5000/api/google-calendar/callback')
    
    WHATSAPP_API_URL = os.getenv('WHATSAPP_API_URL')
    WHATSAPP_API_TOKEN = os.getenv('WHATSAPP_API_TOKEN')
    
    CLINIC_NAME = os.getenv('CLINIC_NAME', 'Venus Medical & Dental Centre')
    CLINIC_PHONE = os.getenv('CLINIC_PHONE', '+263 (0242) 339 769')
    CLINIC_EMAIL = os.getenv('CLINIC_EMAIL', 'medical@venushealthcare.co.zw')
    CLINIC_ADDRESS = os.getenv('CLINIC_ADDRESS', '4 Cuba Ave, Mount Pleasant, Harare, Zimbabwe')
    CLINIC_WEBSITE = os.getenv('CLINIC_WEBSITE', 'https://venushealthcare.co.zw')
    
    APPOINTMENT_BUFFER_MINUTES = int(os.getenv('APPOINTMENT_BUFFER_MINUTES', 15))
    MAX_APPOINTMENTS_PER_SLOT = int(os.getenv('MAX_APPOINTMENTS_PER_SLOT', 1))
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    
    REMINDER_HOURS_BEFORE = [48, 24, 2]
    
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    WTF_CSRF_ENABLED = True
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///venus_booking.db')


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}