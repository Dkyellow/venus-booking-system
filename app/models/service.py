from datetime import datetime
from app.extensions import db


class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#6366F1')
    icon = db.Column(db.String(50), default='fa-medical')
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    services = db.relationship('Service', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<ServiceCategory {self.name}>'


class Service(db.Model):
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer, nullable=False, default=30)
    buffer_time = db.Column(db.Integer, default=15)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=True)
    price = db.Column(db.Numeric(10, 2), default=0)
    color = db.Column(db.String(7), default='#4F46E5')
    icon = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    is_online_bookable = db.Column(db.Boolean, default=True)
    max_advance_days = db.Column(db.Integer, default=60)
    min_advance_hours = db.Column(db.Integer, default=2)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Service {self.name}>'
