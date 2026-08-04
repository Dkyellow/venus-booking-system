from datetime import datetime
from app.extensions import db


class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    room_type = db.Column(db.String(50), nullable=False, default='Consultation')  # Consultation, Examination, Procedure, Laboratory, Imaging
    capacity = db.Column(db.Integer, default=1)
    floor = db.Column(db.String(20))
    equipment = db.Column(db.Text)  # Comma-separated list of equipment
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Room {self.name}>'


class AppointmentRoom(db.Model):
    __tablename__ = 'appointment_rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointment = db.relationship('Appointment', backref=db.backref('room_assignments', lazy='dynamic'))
    room = db.relationship('Room', backref=db.backref('assignments', lazy='dynamic'))
    
    def __repr__(self):
        return f'<AppointmentRoom {self.room_id} for {self.appointment_id}>'
