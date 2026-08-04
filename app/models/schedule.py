from datetime import datetime, date
from app.extensions import db


class StaffSchedule(db.Model):
    __tablename__ = 'staff_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('staff_id', 'day_of_week', name='unique_staff_day'),
    )
    
    @property
    def day_name(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[self.day_of_week]
    
    def __repr__(self):
        return f'<StaffSchedule {self.day_name} {self.start_time}-{self.end_time}>'


class BlockedTime(db.Model):
    __tablename__ = 'blocked_times'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(200))
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_type = db.Column(db.String(20))  # weekly, monthly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BlockedTime {self.reason}>'


class StaffLeave(db.Model):
    __tablename__ = 'staff_leave'
    
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    leave_type = db.Column(db.String(50), nullable=False, default='Leave')  # Leave, Training, PTO, Sick, Other
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default='Approved')  # Pending, Approved, Denied
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    staff = db.relationship('Staff', backref=db.backref('leaves', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref('created_leaves', lazy='dynamic'))
    
    @property
    def is_active_today(self):
        today = date.today()
        return self.start_date <= today <= self.end_date and self.status == 'Approved'
    
    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1
    
    def covers_date(self, check_date):
        return self.start_date <= check_date <= self.end_date and self.status == 'Approved'
    
    def __repr__(self):
        return f'<StaffLeave {self.leave_type} {self.start_date} to {self.end_date}>'


class Holiday(db.Model):
    __tablename__ = 'holidays'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)
    description = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Holiday {self.name}>'
