from datetime import datetime
from app.extensions import db


class ClinicSettings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    clinic_name = db.Column(db.String(200), default='Venus Medical Clinic')
    clinic_email = db.Column(db.String(120))
    clinic_phone = db.Column(db.String(20))
    clinic_address = db.Column(db.Text)
    clinic_website = db.Column(db.String(200))
    clinic_logo_url = db.Column(db.String(500))
    
    working_hours_start = db.Column(db.Time, default=datetime.strptime('08:00', '%H:%M').time())
    working_hours_end = db.Column(db.Time, default=datetime.strptime('18:00', '%H:%M').time())
    timezone = db.Column(db.String(50), default='UTC')
    
    default_appointment_duration = db.Column(db.Integer, default=30)
    default_buffer_time = db.Column(db.Integer, default=15)
    max_advance_booking_days = db.Column(db.Integer, default=60)
    min_advance_booking_hours = db.Column(db.Integer, default=2)
    allow_same_day_booking = db.Column(db.Boolean, default=True)
    
    enable_email_notifications = db.Column(db.Boolean, default=True)
    enable_whatsapp_notifications = db.Column(db.Boolean, default=False)
    enable_google_calendar_sync = db.Column(db.Boolean, default=False)
    
    reminder_48h_enabled = db.Column(db.Boolean, default=True)
    reminder_24h_enabled = db.Column(db.Boolean, default=True)
    reminder_2h_enabled = db.Column(db.Boolean, default=True)
    
    smtp_server = db.Column(db.String(200))
    smtp_port = db.Column(db.Integer, default=587)
    smtp_username = db.Column(db.String(120))
    smtp_password = db.Column(db.String(200))
    smtp_use_tls = db.Column(db.Boolean, default=True)
    
    whatsapp_api_url = db.Column(db.String(500))
    whatsapp_api_token = db.Column(db.String(500))
    whatsapp_phone_number_id = db.Column(db.String(100))
    
    brand_primary_color = db.Column(db.String(7), default='#4F46E5')
    brand_secondary_color = db.Column(db.String(7), default='#7C3AED')
    brand_accent_color = db.Column(db.String(7), default='#06B6D4')
    
    google_calendar_client_id = db.Column(db.String(200))
    google_calendar_client_secret = db.Column(db.String(200))
    
    currency = db.Column(db.String(10), default='USD')
    tax_rate = db.Column(db.Numeric(5, 2), default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ClinicSettings {self.clinic_name}>'
