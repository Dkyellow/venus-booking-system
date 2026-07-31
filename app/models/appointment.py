import enum
from datetime import datetime
from app.extensions import db


class AppointmentStatus(enum.Enum):
    PENDING = 'Pending'
    CONFIRMED = 'Confirmed'
    CHECKED_IN = 'Checked In'
    IN_PROGRESS = 'In Progress'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'
    NO_SHOW = 'No Show'
    RESCHEDULED = 'Rescheduled'


class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    practitioner_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.CONFIRMED, nullable=False)
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    internal_notes = db.Column(db.Text)
    
    google_calendar_event_id = db.Column(db.String(200))
    reminder_sent_48h = db.Column(db.Boolean, default=False)
    reminder_sent_24h = db.Column(db.Boolean, default=False)
    reminder_sent_2h = db.Column(db.Boolean, default=False)
    
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)
    completed_at = db.Column(db.DateTime)
    checked_in_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    service = db.relationship('Service', backref='appointments')
    history = db.relationship('AppointmentHistory', backref='appointment', lazy='dynamic',
                              order_by='AppointmentHistory.created_at.desc()')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    @property
    def status_color(self):
        colors = {
            AppointmentStatus.PENDING: 'warning',
            AppointmentStatus.CONFIRMED: 'primary',
            AppointmentStatus.CHECKED_IN: 'info',
            AppointmentStatus.IN_PROGRESS: 'info',
            AppointmentStatus.COMPLETED: 'success',
            AppointmentStatus.CANCELLED: 'danger',
            AppointmentStatus.NO_SHOW: 'secondary',
            AppointmentStatus.RESCHEDULED: 'warning',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def duration_minutes(self):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0
    
    @property
    def is_past(self):
        return self.end_time < datetime.utcnow()
    
    @property
    def is_today(self):
        return self.date == datetime.utcnow().date()
    
    def __repr__(self):
        return f'<Appointment {self.reference}>'


class AppointmentHistory(db.Model):
    __tablename__ = 'appointment_history'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    notes = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[changed_by])
    
    def __repr__(self):
        return f'<AppointmentHistory {self.action}>'
