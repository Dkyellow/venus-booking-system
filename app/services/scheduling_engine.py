from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
import pytz
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.staff import Staff
from app.models.service import Service
from app.models.schedule import StaffSchedule, BlockedTime, Holiday


class SchedulingEngine:
    
    def __init__(self, timezone='UTC'):
        self.timezone = pytz.timezone(timezone)
    
    def get_available_slots(
        self,
        service_id: int,
        target_date: date,
        practitioner_id: Optional[int] = None,
        duration_override: Optional[int] = None
    ) -> List[Dict]:
        service = Service.query.get(service_id)
        if not service:
            return []
        
        duration = duration_override or service.duration
        buffer_time = service.buffer_time or 15
        
        if practitioner_id:
            practitioner = Staff.query.get(practitioner_id)
            if not practitioner:
                return []
            schedules = StaffSchedule.query.filter_by(
                staff_id=practitioner_id,
                day_of_week=target_date.weekday(),
                is_active=True
            ).all()
        else:
            schedules = StaffSchedule.query.filter_by(
                day_of_week=target_date.weekday(),
                is_active=True
            ).all()
        
        if not schedules:
            return []
        
        if Holiday.query.filter_by(date=target_date).first():
            return []
        
        blocked_times = []
        if practitioner_id:
            blocked_times = BlockedTime.query.filter(
                BlockedTime.staff_id == practitioner_id,
                BlockedTime.start_time <= datetime.combine(target_date, time(23, 59, 59)),
                BlockedTime.end_time >= datetime.combine(target_date, time(0, 0, 0))
            ).all()
        
        existing_appointments = Appointment.query.filter(
            Appointment.date == target_date,
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.PENDING
            ]),
            Appointment.end_time > datetime.combine(target_date, time(0, 0, 0)),
            Appointment.start_time < datetime.combine(target_date, time(23, 59, 59))
        )
        
        if practitioner_id:
            existing_appointments = existing_appointments.filter(
                Appointment.practitioner_id == practitioner_id
            )
        
        existing_appointments = existing_appointments.all()
        
        available_slots = []
        
        for schedule in schedules:
            day_start = datetime.combine(target_date, schedule.start_time)
            day_end = datetime.combine(target_date, schedule.end_time)
            
            if target_date == date.today():
                now = datetime.now(self.timezone).replace(tzinfo=None)
                if day_start < now:
                    day_start = now + timedelta(minutes=30)
                    day_start = day_start.replace(second=0, microsecond=0)
            
            current_time = day_start
            
            while current_time + timedelta(minutes=duration) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration)
                
                if self._is_slot_available(slot_start, slot_end, existing_appointments, blocked_times):
                    available_slots.append({
                        'start_time': slot_start.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                        'display': slot_start.strftime('%I:%M %p'),
                        'datetime_start': slot_start.isoformat(),
                        'datetime_end': slot_end.isoformat(),
                    })
                
                current_time += timedelta(minutes=buffer_time)
        
        return available_slots
    
    def _is_slot_available(
        self,
        slot_start: datetime,
        slot_end: datetime,
        existing_appointments: List,
        blocked_times: List
    ) -> bool:
        for appointment in existing_appointments:
            if slot_start < appointment.end_time and slot_end > appointment.start_time:
                return False
        
        for blocked in blocked_times:
            if slot_start < blocked.end_time and slot_end > blocked.start_time:
                return False
        
        return True
    
    def get_available_dates(
        self,
        service_id: int,
        practitioner_id: Optional[int] = None,
        months_ahead: int = 2
    ) -> List[Dict]:
        service = Service.query.get(service_id)
        if not service:
            return []
        
        available_dates = []
        start_date = date.today()
        end_date = start_date + timedelta(days=service.max_advance_days or 60)
        end_date = min(end_date, start_date + timedelta(days=months_ahead * 30))
        
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                slots = self.get_available_slots(
                    service_id=service_id,
                    target_date=current_date,
                    practitioner_id=practitioner_id
                )
                if slots:
                    available_dates.append({
                        'date': current_date.isoformat(),
                        'display': current_date.strftime('%B %d, %Y'),
                        'day_name': current_date.strftime('%A'),
                        'slots_count': len(slots),
                    })
            
            current_date += timedelta(days=1)
        
        return available_dates
    
    def can_book_appointment(
        self,
        service_id: int,
        practitioner_id: Optional[int],
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[bool, str]:
        service = Service.query.get(service_id)
        if not service:
            return False, "Service not found"
        
        if not service.is_active:
            return False, "Service is not currently available"
        
        if start_time < datetime.utcnow():
            return False, "Cannot book appointments in the past"
        
        target_date = start_time.date()
        min_advance = timedelta(hours=service.min_advance_hours or 2)
        if start_time < datetime.utcnow() + min_advance:
            return False, f"Appointments must be booked at least {service.min_advance_hours} hours in advance"
        
        if Holiday.query.filter_by(date=target_date).first():
            return False, "Cannot book on holidays"
        
        if practitioner_id:
            blocked = BlockedTime.query.filter(
                BlockedTime.staff_id == practitioner_id,
                BlockedTime.start_time < end_time,
                BlockedTime.end_time > start_time
            ).first()
            if blocked:
                return False, "Time slot is blocked"
        
        conflict = Appointment.query.filter(
            Appointment.date == target_date,
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.PENDING
            ]),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time
        )
        
        if practitioner_id:
            conflict = conflict.filter(Appointment.practitioner_id == practitioner_id)
        
        if conflict.first():
            return False, "Time slot is already booked"
        
        return True, "Available"
    
    def create_booking_reference(self) -> str:
        import secrets
        date_str = datetime.utcnow().strftime('%Y%m%d')
        random_part = secrets.token_hex(3).upper()
        return f"APT-{date_str}-{random_part}"
    
    def get_practitioner_schedule_summary(self, practitioner_id: int, target_date: date) -> Dict:
        schedules = StaffSchedule.query.filter_by(
            staff_id=practitioner_id,
            day_of_week=target_date.weekday(),
            is_active=True
        ).all()
        
        if not schedules:
            return {'is_working': False, 'day_name': target_date.strftime('%A')}
        
        blocked_times = BlockedTime.query.filter(
            BlockedTime.staff_id == practitioner_id,
            BlockedTime.start_time <= datetime.combine(target_date, time(23, 59)),
            BlockedTime.end_time >= datetime.combine(target_date, time(0, 0))
        ).all()
        
        return {
            'is_working': True,
            'day_name': target_date.strftime('%A'),
            'schedules': [{
                'start': s.start_time.strftime('%I:%M %p'),
                'end': s.end_time.strftime('%I:%M %p'),
            } for s in schedules],
            'blocked_count': len(blocked_times),
        }
