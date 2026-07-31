from datetime import datetime
from app.extensions import db


staff_services = db.Table(
    'staff_services',
    db.Column('staff_id', db.Integer, db.ForeignKey('staff.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'), primary_key=True)
)


class Staff(db.Model):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20))
    specialization = db.Column(db.String(100))
    title = db.Column(db.String(50))
    bio = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    color = db.Column(db.String(7), default='#4F46E5')
    consultation_fee = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_practitioner = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='staff_profile', uselist=False)
    services = db.relationship('Service', secondary=staff_services, backref=db.backref('practitioners', lazy='dynamic'))
    schedules = db.relationship('StaffSchedule', backref='staff', lazy='dynamic', cascade='all, delete-orphan')
    blocked_times = db.relationship('BlockedTime', backref='staff', lazy='dynamic', cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='practitioner', lazy='dynamic')
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def display_name(self):
        prefix = f"{self.title} " if self.title else ""
        return f"{prefix}{self.full_name}"
    
    def __repr__(self):
        return f'<Staff {self.full_name}>'
