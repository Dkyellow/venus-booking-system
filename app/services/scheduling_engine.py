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
        
        # Check holiday
        if Holiday.query.filter_by(date=target_date).first():
            return []
        
        # Batch-load all data for this date
        day_start_dt = datetime.combine(target_date, time(0, 0))
        day_end_dt = datetime.combine(target_date, time(23, 59, 59))
        
        # Load staff schedules for this day of week
        day_of_week = target_date.weekday()
        
        # Load leave records
        if practitioner_id:
            leave_records = StaffLeave.query.filter(
                StaffLeave.staff_id == practitioner_id,
                StaffLeave.start_date <= target_date,
                StaffLeave.end_date >= target_date,
                StaffLeave.status == 'Approved'
            ).all()
            on_leave_ids = {lr.staff_id for lr in leave_records}
            if practitioner_id in on_leave_ids:
                return []
        else:
            leave_records = StaffLeave.query.filter(
                StaffLeave.start_date <= target_date,
                StaffLeave.end_date >= target_date,
                StaffLeave.status == 'Approved'
            ).all()
            on_leave_ids = {lr.staff_id for lr in leave_records}
        
        # Load schedules for this day
        all_schedules = StaffSchedule.query.filter(
            StaffSchedule.day_of_week == day_of_week,
            StaffSchedule.is_active == True
        ).all()
        
        # Filter to available staff
        if practitioner_id:
            schedules = [s for s in all_schedules if s.staff_id == practitioner_id and s.staff_id not in on_leave_ids]
        else:
            available_staff_ids = {s.id for s in Staff.query.filter_by(is_active=True, is_practitioner=True).all()}
            schedules = [s for s in all_schedules if s.staff_id in available_staff_ids and s.staff_id not in on_leave_ids]
        
        if not schedules:
            return []
        
        # Load blocked times
        blocked_times = BlockedTime.query.filter(
            BlockedTime.start_time <= day_end_dt,
            BlockedTime.end_time >= day_start_dt
        ).all()
        if practitioner_id:
            blocked_times = [b for b in blocked_times if b.staff_id == practitioner_id]
        
        # Load existing appointments
        existing_appointments = Appointment.query.filter(
            Appointment.date == target_date,
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.PENDING
            ]),
            Appointment.end_time > day_start_dt,
            Appointment.start_time < day_end_dt
        ).all()
        if practitioner_id:
            existing_appointments = [a for a in existing_appointments if a.practitioner_id == practitioner_id]
        
        # Pre-index
        blocked_by_staff = {}
        for b in blocked_times:
            blocked_by_staff.setdefault(b.staff_id, []).append(b)
        
        appts_by_staff = {}
        for a in existing_appointments:
            appts_by_staff.setdefault(a.practitioner_id, []).append(a)
        
        # Generate slots
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
            staff_blocked = blocked_by_staff.get(staff_id, [])
            staff_appts = appts_by_staff.get(staff_id, [])
            
            while current_time + timedelta(minutes=total_slot) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration)
                
                start_key = slot_start.strftime('%H:%M')
                if start_key in processed_starts:
                    current_time += timedelta(minutes=buffer_time)
                    continue
                
                # Check blocked
                blocked = any(slot_start < b.end_time and slot_end > b.start_time for b in staff_blocked)
                if blocked:
                    current_time += timedelta(minutes=buffer_time)
                    continue
                
                # Check appointments
                conflict = any(slot_start < a.end_time and slot_end > a.start_time for a in staff_appts)
                if conflict:
                    current_time += timedelta(minutes=buffer_time)
                    continue
                
                # Check room if needed
                if service.requires_room:
                    room_ok, _, _ = self.check_room_availability(
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
        
        start_date = date.today()
        end_date = start_date + timedelta(days=min(service.max_advance_days or 60, months_ahead * 30))
        
        duration = service.duration
        buffer_time = service.buffer_time or 15
        total_slot = duration + buffer_time
        
        # Batch-load all data for the date range
        day_start_dt = datetime.combine(start_date, time(0, 0))
        day_end_dt = datetime.combine(end_date, time(23, 59, 59))
        
        # Holidays
        holiday_dates = {h.date for h in Holiday.query.filter(
            Holiday.date >= start_date, Holiday.date <= end_date
        ).all()}
        
        # Staff schedules (all active)
        all_schedules = StaffSchedule.query.filter(
            StaffSchedule.is_active == True,
            StaffSchedule.day_of_week >= 0
        ).all()
        
        # Leave records
        if practitioner_id:
            leave_records = StaffLeave.query.filter(
                StaffLeave.staff_id == practitioner_id,
                StaffLeave.start_date <= end_date,
                StaffLeave.end_date >= start_date,
                StaffLeave.status == 'Approved'
            ).all()
        else:
            leave_records = StaffLeave.query.filter(
                StaffLeave.start_date <= end_date,
                StaffLeave.end_date >= start_date,
                StaffLeave.status == 'Approved'
            ).all()
        
        # Blocked times
        if practitioner_id:
            blocked_times = BlockedTime.query.filter(
                BlockedTime.staff_id == practitioner_id,
                BlockedTime.start_time <= day_end_dt,
                BlockedTime.end_time >= day_start_dt
            ).all()
        else:
            blocked_times = []
        
        # Active practitioners
        if practitioner_id:
            active_staff = {practitioner_id}
        else:
            active_staff = {s.id for s in Staff.query.filter_by(is_active=True, is_practitioner=True).all()}
        
        # Existing appointments
        existing_appointments = Appointment.query.filter(
            Appointment.date >= start_date,
            Appointment.date <= end_date,
            Appointment.status.in_([
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_PROGRESS,
                AppointmentStatus.PENDING
            ])
        )
        if practitioner_id:
            existing_appointments = existing_appointments.filter(
                Appointment.practitioner_id == practitioner_id
            )
        existing_appointments = existing_appointments.all()
        
        # Pre-index data
        schedules_by_staff_day = {}
        for s in all_schedules:
            schedules_by_staff_day.setdefault(s.staff_id, {})[s.day_of_week] = s
        
        leave_by_staff = {}
        for lr in leave_records:
            leave_by_staff.setdefault(lr.staff_id, []).append(lr)
        
        appointments_by_date = {}
        for appt in existing_appointments:
            appointments_by_date.setdefault(appt.date, []).append(appt)
        
        # Check each date
        available_dates = []
        current_date = start_date
        while current_date <= end_date:
            if current_date not in holiday_dates:
                has_slots = self._check_date_has_slots(
                    current_date, service, duration, buffer_time, total_slot,
                    active_staff, schedules_by_staff_day, leave_by_staff,
                    blocked_times, appointments_by_date, practitioner_id
                )
                if has_slots:
                    available_dates.append({
                        'date': current_date.isoformat(),
                        'display': current_date.strftime('%B %d, %Y'),
                        'day_name': current_date.strftime('%A'),
                        'slots_count': has_slots,
                    })
            
            current_date += timedelta(days=1)
        
        return available_dates
    
    def _check_date_has_slots(
        self, target_date, service, duration, buffer_time, total_slot,
        active_staff, schedules_by_staff_day, leave_by_staff,
        blocked_times, appointments_by_date, practitioner_id
    ):
        day_of_week = target_date.weekday()
        day_appointments = appointments_by_date.get(target_date, [])
        day_blocked = [b for b in blocked_times 
                       if b.start_time.date() <= target_date and b.end_time.date() >= target_date]
        slot_count = 0
        
        # Determine which staff to check
        if practitioner_id:
            staff_to_check = [practitioner_id]
        else:
            staff_to_check = list(active_staff)
        
        for staff_id in staff_to_check:
            # Check leave
            on_leave = False
            for lr in leave_by_staff.get(staff_id, []):
                if lr.start_date <= target_date <= lr.end_date:
                    on_leave = True
                    break
            if on_leave:
                continue
            
            # Check schedule
            staff_scheds = schedules_by_staff_day.get(staff_id, {})
            if day_of_week not in staff_scheds:
                continue
            sched = staff_scheds[day_of_week]
            
            staff_appts = [a for a in day_appointments 
                          if a.practitioner_id == staff_id]
            staff_blocked = [b for b in day_blocked if b.staff_id == staff_id]
            
            # Generate slots
            day_start = datetime.combine(target_date, sched.start_time)
            day_end = datetime.combine(target_date, sched.end_time)
            
            if target_date == date.today():
                now = datetime.now(self.timezone).replace(tzinfo=None)
                if day_start < now:
                    day_start = now + timedelta(minutes=30)
                    day_start = day_start.replace(second=0, microsecond=0)
            
            current_time = day_start
            while current_time + timedelta(minutes=total_slot) <= day_end:
                slot_start = current_time
                slot_end = current_time + timedelta(minutes=duration)
                
                # Check blocked
                blocked = False
                for b in staff_blocked:
                    if slot_start < b.end_time and slot_end > b.start_time:
                        blocked = True
                        break
                
                if not blocked:
                    # Check appointments
                    conflict = False
                    for appt in staff_appts:
                        if slot_start < appt.end_time and slot_end > appt.start_time:
                            conflict = True
                            break
                    
                    if not conflict:
                        # Check room if needed
                        if service.requires_room:
                            room_ok, _, _ = self.check_room_availability(
                                target_date, slot_start, slot_end, service.required_room_type
                            )
                            if room_ok:
                                slot_count += 1
                        else:
                            slot_count += 1
                
                current_time += timedelta(minutes=buffer_time)
        
        return slot_count
    
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
