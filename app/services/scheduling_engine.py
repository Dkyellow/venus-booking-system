from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple
import pytz
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.staff import Staff
from app.models.service import Service
from app.models.schedule import StaffSchedule, BlockedTime, Holiday, StaffLeave
from app.models.room import Room, AppointmentRoom


class SchedulingEngine:
    
    def __init__(self, timezone='UTC'):
        self.timezone = pytz.timezone(timezone)
    
    def is_practitioner_available_on_date(self, practitioner_id: int, target_date: date) -> Tuple[bool, str]:
        staff = Staff.query.get(practitioner_id)
        if not staff or not staff.is_active:
            return False, "Practitioner not found or inactive"
        
        leave = StaffLeave.query.filter(
            StaffLeave.staff_id == practitioner_id,
            StaffLeave.start_date <= target_date,
            StaffLeave.end_date >= target_date,
            StaffLeave.status == 'Approved'
        ).first()
        if leave:
            return False, f"On {leave.leave_type.lower()}: {leave.reason or leave.leave_type}"
        
        schedule = StaffSchedule.query.filter_by(
            staff_id=practitioner_id,
            day_of_week=target_date.weekday(),
            is_active=True
        ).first()
        if not schedule:
            return False, "Not scheduled to work on this day"
        
        return True, "Available"
    
    def is_practitioner_available_at_time(
        self,
        practitioner_id: int,
        target_date: date,
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[bool, str]:
        available, reason = self.is_practitioner_available_on_date(practitioner_id, target_date)
        if not available:
            return False, reason
        
        blocked = BlockedTime.query.filter(
            BlockedTime.staff_id == practitioner_id,
            BlockedTime.start_time < end_time,
            BlockedTime.end_time > start_time
        ).first()
        if blocked:
            return False, f"Time blocked: {blocked.reason or 'Unavailable'}"
        
        return True, "Available"
    
    def check_room_availability(
        self,
        target_date: date,
        start_time: datetime,
        end_time: datetime,
        required_room_type: Optional[str] = None
    ) -> Tuple[bool, Optional[Room], str]:
        query = Room.query.filter_by(is_active=True)
        if required_room_type:
            query = query.filter_by(room_type=required_room_type)
        
        rooms = query.all()
        if not rooms:
            return False, None, "No rooms available"
        
        booked_room_ids = db.session.query(AppointmentRoom.room_id).join(
            Appointment, AppointmentRoom.appointment_id == Appointment.id
        ).filter(
            Appointment.date == target_date,
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.PENDING
            ]),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time
        ).subquery()
        
        available_rooms = Room.query.filter(
            Room.id.in_([r.id for r in rooms]),
            ~Room.id.in_(db.session.query(booked_room_ids))
        ).first()
        
        if not available_rooms:
            return False, None, "All rooms of required type are booked"
        
        return True, available_rooms, "Room available"
    
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
        total_slot = duration + buffer_time
        
        if practitioner_id:
            available, reason = self.is_practitioner_available_on_date(practitioner_id, target_date)
            if not available:
                return []
            
            schedules = StaffSchedule.query.filter_by(
                staff_id=practitioner_id,
                day_of_week=target_date.weekday(),
                is_active=True
            ).all()
        else:
            if Holiday.query.filter_by(date=target_date).first():
                return []
            
            all_staff_ids = [s.id for s in Staff.query.filter_by(is_active=True, is_practitioner=True).all()]
            available_staff_ids = []
            for sid in all_staff_ids:
                avail, _ = self.is_practitioner_available_on_date(sid, target_date)
                if avail:
                    available_staff_ids.append(sid)
            
            if not available_staff_ids:
                return []
            
            schedules = StaffSchedule.query.filter(
                StaffSchedule.staff_id.in_(available_staff_ids),
                StaffSchedule.day_of_week == target_date.weekday(),
                StaffSchedule.is_active == True
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
        processed_starts = set()
        
        for schedule in schedules:
            staff_id = schedule.staff_id
            day_start = datetime.combine(target_date, schedule.start_time)
            day_end = datetime.combine(target_date, schedule.end_time)
            
            if target_date == date.today():
                now = datetime.now(self.timezone).replace(tzinfo=None)
                if day_start < now:
                    day_start = now + timedelta(minutes=30)
                    day_start = day_start.replace(second=0, microsecond=0)
            
            current_time = day_start
            
            while current_time + timedelta(minutes=total_slot) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration)
                
                start_key = slot_start.strftime('%H:%M')
                if start_key in processed_starts:
                    current_time += timedelta(minutes=buffer_time)
                    continue
                
                avail, _ = self.is_practitioner_available_at_time(
                    staff_id, target_date, slot_start, slot_end
                )
                if not avail:
                    current_time += timedelta(minutes=buffer_time)
                    continue
                
                if self._is_slot_available(slot_start, slot_end, existing_appointments, blocked_times):
                    if service.requires_room:
                        room_ok, room, _ = self.check_room_availability(
                            target_date, slot_start, slot_end, service.required_room_type
                        )
                        if not room_ok:
                            current_time += timedelta(minutes=buffer_time)
                            continue
                    
                    processed_starts.add(start_key)
                    available_slots.append({
                        'start_time': slot_start.strftime('%H:%M'),
                        'end_time': (slot_start + timedelta(minutes=duration)).strftime('%H:%M'),
                        'display': slot_start.strftime('%I:%M %p'),
                        'datetime_start': slot_start.isoformat(),
                        'datetime_end': (slot_start + timedelta(minutes=duration)).isoformat(),
                        'practitioner_id': staff_id,
                    })
                
                current_time += timedelta(minutes=buffer_time)
        
        available_slots.sort(key=lambda x: x['start_time'])
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
            avail, reason = self.is_practitioner_available_at_time(
                practitioner_id, target_date, start_time, end_time
            )
            if not avail:
                return False, reason
        
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
        
        if service.requires_room:
            room_ok, room, reason = self.check_room_availability(
                target_date, start_time, end_time, service.required_room_type
            )
            if not room_ok:
                return False, reason
        
        return True, "Available"
    
    def assign_room(
        self,
        appointment_id: int,
        target_date: date,
        start_time: datetime,
        end_time: datetime,
        required_room_type: Optional[str] = None
    ) -> Optional[Room]:
        room_ok, room, _ = self.check_room_availability(
            target_date, start_time, end_time, required_room_type
        )
        if room_ok and room:
            assignment = AppointmentRoom(
                appointment_id=appointment_id,
                room_id=room.id
            )
            db.session.add(assignment)
            db.session.commit()
            return room
        return None
    
    def create_booking_reference(self) -> str:
        import secrets
        date_str = datetime.utcnow().strftime('%Y%m%d')
        random_part = secrets.token_hex(3).upper()
        return f"APT-{date_str}-{random_part}"
    
    def get_practitioner_schedule_summary(self, practitioner_id: int, target_date: date) -> Dict:
        available, reason = self.is_practitioner_available_on_date(practitioner_id, target_date)
        
        schedules = StaffSchedule.query.filter_by(
            staff_id=practitioner_id,
            day_of_week=target_date.weekday(),
            is_active=True
        ).all()
        
        blocked_times = BlockedTime.query.filter(
            BlockedTime.staff_id == practitioner_id,
            BlockedTime.start_time <= datetime.combine(target_date, time(23, 59)),
            BlockedTime.end_time >= datetime.combine(target_date, time(0, 0))
        ).all()
        
        return {
            'is_working': available,
            'day_name': target_date.strftime('%A'),
            'unavailable_reason': reason if not available else None,
            'schedules': [{
                'start': s.start_time.strftime('%I:%M %p'),
                'end': s.end_time.strftime('%I:%M %p'),
            } for s in schedules],
            'blocked_count': len(blocked_times),
        }
