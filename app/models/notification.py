from datetime import datetime
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    type = db.Column(db.String(50), nullable=False)  # email, whatsapp, sms, system
    category = db.Column(db.String(50), nullable=False)  # confirmation, reminder, rescheduled, cancelled
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    
    sent_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')
    patient = db.relationship('Patient', backref='notifications')
    appointment = db.relationship('Appointment', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.type} - {self.category}>'


class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    template = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    error_message = db.Column(db.Text)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointment = db.relationship('Appointment', backref='email_logs')
    
    def __repr__(self):
        return f'<EmailLog {self.recipient} - {self.subject}>'


class WhatsAppLog(db.Model):
    __tablename__ = 'whatsapp_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    template = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    appointment = db.relationship('Appointment', backref='whatsapp_logs')
    
    def __repr__(self):
        return f'<WhatsAppLog {self.recipient}>'
