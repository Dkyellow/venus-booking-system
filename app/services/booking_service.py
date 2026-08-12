from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
from sqlalchemy import exc as sqlalchemy_exc
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus, AppointmentHistory
from app.models.patient import Patient
from app.models.service import Service
from app.models.room import Room, AppointmentRoom
from app.services.scheduling_engine import SchedulingEngine
import logging

logger = logging.getLogger(__name__)


class BookingService:
    """
    Transaction-safe booking service.
    All booking operations are wrapped in database transactions.
    PostgreSQL exclusion constraints provide the final safeguard against double-booking.
    """

    def __init__(self):
        self.engine = SchedulingEngine()

    def create_booking(
        self,
        service_id: int,
        practitioner_id: Optional[int],
        start_time: datetime,
        end_time: datetime,
        patient_data: Dict[str, Any],
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
        auto_confirm: bool = False
    ) -> Tuple[Optional[Appointment], Optional[str]]:
        """
        Create a booking inside a single database transaction.

        Performs all validation and inserts within one transaction block.
        If the insertion violates the PostgreSQL exclusion constraint,
        the transaction is rolled back and a conflict is reported.

        Returns: (appointment, error_message)
            - (Appointment, None) on success
            - (None, error_string) on failure
        """
        try:
            service = Service.query.get(service_id)
            if not service:
                return None, "Service not found"

            if not service.is_active:
                return None, "Service is not currently available"

            if start_time >= end_time:
                return None, "Start time must be before end time"

            # Calculate end_time from service duration if not provided
            # (but if end_time is provided and valid, use it)
            if end_time is None:
                end_time = start_time + timedelta(minutes=service.duration)

            # Validate against past times
            now = datetime.utcnow()
            if start_time < now:
                return None, "Cannot book appointments in the past"

            # Min advance booking
            min_advance = timedelta(hours=service.min_advance_hours or 2)
            if start_time < now + min_advance:
                hours = service.min_advance_hours or 2
                return None, f"Appointments must be booked at least {hours} hours in advance"

            # Check holiday
            from app.models.schedule import Holiday
            target_date = start_time.date()
            if Holiday.query.filter_by(date=target_date).first():
                return None, "Cannot book appointments on holidays"

            # Check practitioner availability
            if practitioner_id:
                available, reason = self.engine.is_practitioner_available_at_time(
                    practitioner_id, target_date, start_time, end_time
                )
                if not available:
                    return None, reason

            # Check for existing conflicts (application-level, before hitting DB)
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
                return None, "The selected doctor is unavailable during this time"

            # Check room availability if service requires a room
            room = None
            if service.requires_room:
                room_ok, room, room_reason = self.engine.check_room_availability(
                    target_date, start_time, end_time, service.required_room_type
                )
                if not room_ok:
                    return None, room_reason

            # Find or create patient
            patient = Patient.query.filter(
                (Patient.email == patient_data['email'].lower()) |
                (Patient.phone == patient_data['phone'])
            ).first()

            if not patient:
                patient = Patient(
                    first_name=patient_data['first_name'],
                    last_name=patient_data['last_name'],
                    email=patient_data['email'].lower(),
                    phone=patient_data['phone'],
                    date_of_birth=patient_data.get('date_of_birth'),
                    gender=patient_data.get('gender')
                )
                db.session.add(patient)
                db.session.flush()

            reference = self.engine.create_booking_reference()

            appointment = Appointment(
                reference=reference,
                patient_id=patient.id,
                practitioner_id=practitioner_id,
                service_id=service_id,
                date=start_time.date(),
                start_time=start_time,
                end_time=end_time,
                status=AppointmentStatus.CONFIRMED if auto_confirm else AppointmentStatus.PENDING,
                reason=reason,
                notes=notes,
                created_by=created_by
            )
            db.session.add(appointment)

            # Assign room within the same transaction
            if room:
                assignment = AppointmentRoom(
                    appointment_id=appointment.id,
                    room_id=room.id
                )
                db.session.add(assignment)

            history = AppointmentHistory(
                appointment_id=appointment.id,
                action='created' if not auto_confirm else 'confirmed',
                new_value=f"Appointment created{' and confirmed' if auto_confirm else ''}"
            )
            db.session.add(history)

            db.session.commit()

            logger.info(f"Booking created: {reference} (appointment_id={appointment.id})")
            return appointment, None

        except sqlalchemy_exc.IntegrityError as e:
            db.session.rollback()
            if 'no_doctor_booking_overlap' in str(e.orig) or 'no_room_booking_overlap' in str(e.orig):
                logger.warning(f"Booking conflict detected (DB constraint): {e.orig}")
                return None, "The selected doctor or room is no longer available. Please select another time."
            elif 'appointments_reference_key' in str(e.orig):
                logger.error(f"Reference collision: {e.orig}")
                return None, "A booking reference collision occurred. Please try again."
            else:
                logger.error(f"IntegrityError during booking creation: {e.orig}")
                return None, "An error occurred while creating your booking. Please try again."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error during booking creation: {e}", exc_info=True)
            return None, f"An unexpected error occurred: {str(e)}"

    def confirm_booking(self, appointment_id: int, admin_id: int) -> Tuple[bool, Optional[str]]:
        """
        Confirm a pending booking.
        Re-validates availability before committing.
        """
        try:
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return False, "Appointment not found"

            if appointment.status != AppointmentStatus.PENDING:
                return False, f"Cannot confirm appointment with status: {appointment.status.value}"

            service = appointment.service
            start_time = appointment.start_time
            end_time = appointment.end_time
            target_date = start_time.date()

            # Re-check practitioner availability
            if appointment.practitioner_id:
                available, reason = self.engine.is_practitioner_available_at_time(
                    appointment.practitioner_id, target_date, start_time, end_time
                )
                if not available:
                    # Check if it's a self-conflict (this appointment's own time)
                    return False, f"Doctor is not available: {reason}"

            # Re-check for conflicts (exclude current appointment)
            conflict = Appointment.query.filter(
                Appointment.id != appointment.id,
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

            if appointment.practitioner_id:
                conflict = conflict.filter(Appointment.practitioner_id == appointment.practitioner_id)

            existing = conflict.first()
            if existing:
                return False, "A conflicting appointment exists. Please check the schedule and retry."

            # Re-check room if needed
            if service.requires_room:
                room = (
                    db.session.query(Room)
                    .join(AppointmentRoom)
                    .filter(AppointmentRoom.appointment_id == appointment.id)
                    .first()
                )
                if room:
                    room_conflict = Appointment.query.filter(
                        Appointment.id != appointment.id,
                        Appointment.date == target_date,
                        Appointment.status.in_([
                            AppointmentStatus.CONFIRMED,
                            AppointmentStatus.CHECKED_IN,
                            AppointmentStatus.IN_PROGRESS,
                            AppointmentStatus.PENDING
                        ]),
                        Appointment.start_time < end_time,
                        Appointment.end_time > start_time
                    ).join(AppointmentRoom, AppointmentRoom.appointment_id == Appointment.id
                    ).filter(AppointmentRoom.room_id == room.id).first()

                    if room_conflict:
                        return False, "Room is no longer available for this time slot."

            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_at = datetime.utcnow()

            history = AppointmentHistory(
                appointment_id=appointment.id,
                action='status_changed',
                old_value=AppointmentStatus.PENDING.value,
                new_value=AppointmentStatus.CONFIRMED.value,
                changed_by=admin_id
            )
            db.session.add(history)
            db.session.commit()

            logger.info(f"Booking confirmed: appointment_id={appointment_id}")
            return True, None

        except sqlalchemy_exc.IntegrityError as e:
            db.session.rollback()
            if 'no_doctor_booking_overlap' in str(e.orig) or 'no_room_booking_overlap' in str(e.orig):
                return False, "The selected doctor or room is no longer available."
            logger.error(f"IntegrityError during confirmation: {e.orig}")
            return False, "A database conflict occurred. Please try again."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error confirming booking: {e}", exc_info=True)
            return False, str(e)

    def cancel_booking(self, appointment_id: int, reason: str = None,
                       cancelled_by: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Cancel an appointment."""
        try:
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return False, "Appointment not found"

            if appointment.status in [
                AppointmentStatus.CANCELLED,
                AppointmentStatus.COMPLETED,
                AppointmentStatus.NO_SHOW
            ]:
                return False, "This appointment cannot be cancelled"

            old_status = appointment.status
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = datetime.utcnow()
            appointment.cancellation_reason = reason

            history = AppointmentHistory(
                appointment_id=appointment.id,
                action='cancelled',
                old_value=old_status.value,
                new_value=AppointmentStatus.CANCELLED.value,
                notes=reason,
                changed_by=cancelled_by
            )
            db.session.add(history)
            db.session.commit()

            logger.info(f"Booking cancelled: appointment_id={appointment_id}")
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cancelling booking: {e}", exc_info=True)
            return False, str(e)

    def reschedule_booking(
        self,
        appointment_id: int,
        new_start: datetime,
        new_end: datetime,
        admin_id: Optional[int] = None,
        is_admin: bool = False
    ) -> Tuple[bool, Optional[Appointment], Optional[str]]:
        """
        Reschedule an appointment with full availability checking.
        """
        try:
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return False, None, "Appointment not found"

            old_status = appointment.status
            old_start = appointment.start_time
            old_end = appointment.end_time

            service = appointment.service
            target_date = new_start.date()

            # Check past time
            if new_start < datetime.utcnow():
                return False, None, "Cannot reschedule to a past time"

            # Check holiday
            from app.models.schedule import Holiday
            if Holiday.query.filter_by(date=target_date).first():
                return False, None, "Cannot reschedule on holidays"

            # Check practitioner availability
            if appointment.practitioner_id:
                available, reason = self.engine.is_practitioner_available_at_time(
                    appointment.practitioner_id, target_date, new_start, new_end
                )
                if not available:
                    return False, None, f"Doctor is not available: {reason}"

            # Check for conflicts (excluding current appointment)
            conflict = Appointment.query.filter(
                Appointment.id != appointment.id,
                Appointment.date == target_date,
                Appointment.status.in_([
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.CHECKED_IN,
                    AppointmentStatus.IN_PROGRESS,
                    AppointmentStatus.PENDING
                ]),
                Appointment.start_time < new_end,
                Appointment.end_time > new_start
            )

            if appointment.practitioner_id:
                conflict = conflict.filter(Appointment.practitioner_id == appointment.practitioner_id)

            if conflict.first():
                return False, None, "The selected doctor is unavailable during this time"

            # Check room availability if service requires a room
            if service.requires_room:
                room = (
                    db.session.query(Room)
                    .join(AppointmentRoom)
                    .filter(AppointmentRoom.appointment_id == appointment.id)
                    .first()
                )
                if room:
                    room_conflict = Appointment.query.filter(
                        Appointment.id != appointment.id,
                        Appointment.date == target_date,
                        Appointment.status.in_([
                            AppointmentStatus.CONFIRMED,
                            AppointmentStatus.CHECKED_IN,
                            AppointmentStatus.IN_PROGRESS,
                            AppointmentStatus.PENDING
                        ]),
                        Appointment.start_time < new_end,
                        Appointment.end_time > new_start
                    ).join(AppointmentRoom, AppointmentRoom.appointment_id == Appointment.id
                    ).filter(AppointmentRoom.room_id == room.id).first()

                    if room_conflict:
                        return False, None, "Room is unavailable during this time"

            # All checks passed, apply changes
            appointment.start_time = new_start
            appointment.end_time = new_end
            appointment.date = new_start.date()

            if is_admin:
                appointment.status = AppointmentStatus.CONFIRMED
                appointment.confirmed_at = datetime.utcnow()
                action = 'rescheduled_and_confirmed'
                new_status_val = AppointmentStatus.CONFIRMED.value
            else:
                appointment.status = AppointmentStatus.RESCHEDULED
                action = 'reschedule_requested'
                new_status_val = AppointmentStatus.RESCHEDULED.value

            history = AppointmentHistory(
                appointment_id=appointment.id,
                action=action,
                old_value=f"{old_status.value} at {old_start.strftime('%Y-%m-%d %H:%M')}",
                new_value=f"{new_status_val} at {new_start.strftime('%Y-%m-%d %H:%M')}",
                changed_by=admin_id
            )
            db.session.add(history)
            db.session.commit()

            logger.info(f"Booking rescheduled: appointment_id={appointment_id}")
            return True, appointment, None

        except sqlalchemy_exc.IntegrityError as e:
            db.session.rollback()
            if 'no_doctor_booking_overlap' in str(e.orig) or 'no_room_booking_overlap' in str(e.orig):
                return False, None, "The selected doctor or room is no longer available. Please select another time."
            logger.error(f"IntegrityError during reschedule: {e.orig}")
            return False, None, "A database conflict occurred. Please try again."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error rescheduling booking: {e}", exc_info=True)
            return False, None, str(e)

    def find_conflicting_appointment(
        self,
        practitioner_id: Optional[int],
        start_time: datetime,
        end_time: datetime,
        exclude_id: Optional[int] = None
    ) -> Optional[Appointment]:
        """Check if any existing confirmed/pending appointment conflicts."""
        target_date = start_time.date()
        query = Appointment.query.filter(
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
            query = query.filter(Appointment.practitioner_id == practitioner_id)

        if exclude_id:
            query = query.filter(Appointment.id != exclude_id)

        return query.first()

    def approve_reschedule(self, appointment_id: int, admin_id: int) -> Tuple[bool, Optional[str]]:
        """Approve a reschedule request (change status from RESCHEDULED to CONFIRMED)."""
        try:
            appointment = Appointment.query.get(appointment_id)
            if not appointment:
                return False, "Appointment not found"

            if appointment.status != AppointmentStatus.RESCHEDULED:
                return False, f"Cannot approve reschedule for status: {appointment.status.value}"

            # Re-validate availability since the time may have been changed
            service = appointment.service
            start_time = appointment.start_time
            end_time = appointment.end_time
            target_date = start_time.date()

            if appointment.practitioner_id:
                available, reason = self.engine.is_practitioner_available_at_time(
                    appointment.practitioner_id, target_date, start_time, end_time
                )
                if not available:
                    return False, f"Doctor is not available: {reason}"

            conflict = Appointment.query.filter(
                Appointment.id != appointment.id,
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

            if appointment.practitioner_id:
                conflict = conflict.filter(Appointment.practitioner_id == appointment.practitioner_id)

            if conflict.first():
                return False, "A conflicting appointment exists. Cannot approve reschedule."

            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_at = datetime.utcnow()

            history = AppointmentHistory(
                appointment_id=appointment.id,
                action='reschedule_approved',
                old_value=AppointmentStatus.RESCHEDULED.value,
                new_value=AppointmentStatus.CONFIRMED.value,
                changed_by=admin_id
            )
            db.session.add(history)
            db.session.commit()

            logger.info(f"Reschedule approved: appointment_id={appointment_id}")
            return True, None

        except sqlalchemy_exc.IntegrityError as e:
            db.session.rollback()
            if 'no_doctor_booking_overlap' in str(e.orig) or 'no_room_booking_overlap' in str(e.orig):
                return False, "A conflicting appointment was created. Cannot approve reschedule."
            return False, "A database conflict occurred."
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving reschedule: {e}", exc_info=True)
            return False, str(e)
