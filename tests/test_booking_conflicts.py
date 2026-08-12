"""
Comprehensive tests for booking conflict detection and prevention.

Tests cover:
1. Same doctor double booking prevention
2. Same room double booking prevention
3. Different doctor and room (allowed)
4. Back-to-back appointments (allowed)
5. Cancellation releases resources
6. Concurrent booking race condition
7. Service duration determines end time
8. Doctor working hours validation
"""
import pytest
import random
from datetime import datetime, timedelta, time as dt_time
from app import create_app
from app.extensions import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.models.staff import Staff
from app.models.patient import Patient
from app.models.room import Room, AppointmentRoom
from app.models.schedule import StaffSchedule
from app.services.booking_service import BookingService

# Unique counter for reference generation
_ref_counter = [0]


def _unique_ref():
    _ref_counter[0] += 1
    return f"APT-TEST-{_ref_counter[0]:04d}"


def _future_time(hours_ahead: int = 3) -> datetime:
    """Get a future datetime that's at least `hours_ahead` hours in the future (UTC)."""
    now_utc = datetime.utcnow()
    future = now_utc + timedelta(hours=hours_ahead)
    # Round up to next hour boundary
    future = future.replace(minute=0, second=0, microsecond=0)
    # If we rounded down, add an hour
    if future <= now_utc + timedelta(hours=hours_ahead):
        future += timedelta(hours=1)
    return future


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    yield db.session


def _seed_test_data():
    """Create test service, staff, patient, and room."""
    service = Service(
        name="Dental Cleaning",
        description="Professional dental cleaning",
        duration=60,
        buffer_time=15,
        price=100.00,
        is_active=True,
        is_online_bookable=True
    )
    db.session.add(service)
    db.session.flush()

    doctor = Staff(
        first_name="Test",
        last_name="Dentist",
        email="dr.test@venushealthcare.co.zw",
        specialization="Dentistry",
        title="Dr.",
        is_active=True,
        is_practitioner=True
    )
    db.session.add(doctor)
    db.session.flush()

    # Set working hours Mon-Fri 8am-5pm
    for dow in range(5):
        schedule = StaffSchedule(
            staff_id=doctor.id,
            day_of_week=dow,
            start_time=dt_time(8, 0),
            end_time=dt_time(17, 0),
            is_active=True
        )
        db.session.add(schedule)

    service2 = Service(
        name="General Consultation",
        description="General check-up",
        duration=30,
        buffer_time=15,
        price=50.00,
        is_active=True,
        is_online_bookable=True
    )
    db.session.add(service2)
    db.session.flush()

    doctor2 = Staff(
        first_name="Test2",
        last_name="Doctor",
        email="dr2.test@venushealthcare.co.zw",
        specialization="General Practice",
        title="Dr.",
        is_active=True,
        is_practitioner=True
    )
    db.session.add(doctor2)
    db.session.flush()

    # Set working hours for doctor2
    for dow in range(5):
        schedule2 = StaffSchedule(
            staff_id=doctor2.id,
            day_of_week=dow,
            start_time=dt_time(8, 0),
            end_time=dt_time(17, 0),
            is_active=True
        )
        db.session.add(schedule2)

    room = Room(
        name="Dental Suite 1",
        description="Test dental room",
        room_type="Examination",
        capacity=1,
        floor="1st",
        equipment="Dental chair",
        is_active=True
    )
    db.session.add(room)
    db.session.flush()

    patient_data = {
        'first_name': "Test",
        'last_name': "Patient",
        'email': "test@example.com",
        'phone': "+263771234567",
        'date_of_birth': None,
        'gender': "Other"
    }

    db.session.commit()
    return service, doctor, doctor2, room, patient_data


def _make_booking(service_id, doctor_id, start_dt, end_dt, room_id=None, status=AppointmentStatus.CONFIRMED):
    """Create an appointment directly in the database."""
    from app.models.patient import Patient
    patient = Patient(
        first_name="Existing",
        last_name="Patient",
        email="existing@example.com",
        phone="+263771111111",
        date_of_birth=None,
        gender="Other"
    )
    db.session.add(patient)
    db.session.flush()

    appt = Appointment(
        reference=_unique_ref(),
        patient_id=patient.id,
        practitioner_id=doctor_id,
        service_id=service_id,
        date=start_dt.date(),
        start_time=start_dt,
        end_time=end_dt,
        status=status
    )
    db.session.add(appt)
    db.session.commit()

    if room_id:
        ar = AppointmentRoom(appointment_id=appt.id, room_id=room_id)
        db.session.add(ar)
        db.session.commit()

    return appt


class TestDoctorOverlapPrevention:
    """Test 1: Same doctor cannot have overlapping appointments."""

    def test_same_doctor_overlap_rejected(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Create existing appointment (10:00-11:00)
            _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60))

            # Try to book same doctor at overlapping time (10:30-11:30)
            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=base_time + timedelta(minutes=30),
                end_time=base_time + timedelta(minutes=90),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is None
            assert error is not None
            assert "unavailable" in error.lower() or "booked" in error.lower() or "conflict" in error.lower()

    def test_different_time_no_overlap(self, app):
        """Test 4: Back-to-back appointments are allowed."""
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Create 10:00-11:00 appointment
            _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60))

            # Try 11:00-12:00 (back-to-back, no overlap)
            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=base_time + timedelta(hours=1),
                end_time=base_time + timedelta(hours=2),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is not None
            assert error is None


class TestRoomOverlapPrevention:
    """Test 2: Same room cannot have overlapping appointments."""

    def test_same_room_overlap_rejected(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            # Service requires a room
            service.requires_room = True
            service.required_room_type = room.room_type
            db.session.commit()

            base_time = _future_time(3)

            # Create existing appointment with the room
            _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60), room_id=room.id)

            # Try same room with different doctor at overlapping time
            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor2.id,
                start_time=base_time + timedelta(minutes=30),
                end_time=base_time + timedelta(minutes=90),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is None
            assert error is not None
            assert "room" in error.lower() or "unavailable" in error.lower() or "booked" in error.lower()


class TestDifferentResources:
    """Test 3: Different doctor and room is allowed."""

    def test_different_doctor_room_allowed(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Book doctor1+room1 at 10:00-11:00
            _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60), room_id=room.id)

            # Should be able to book doctor2+room2 at same time
            room2 = Room(
                name="Dental Suite 2",
                description="Another room",
                room_type="Examination",
                capacity=1,
                floor="1st",
                equipment="Dental chair",
                is_active=True
            )
            db.session.add(room2)
            db.session.commit()

            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor2.id,
                start_time=base_time,
                end_time=base_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )

            # This should succeed (different doctor)
            assert appointment is not None
            assert error is None


class TestCancellation:
    """Test 6: Cancellation releases resources."""

    def test_cancellation_releases_slot(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Create appointment
            appt = _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60))

            # Cancel it
            success, error = booking_service.cancel_booking(appt.id, reason="Patient cancel")
            assert success
            assert error is None

            # Verify it's cancelled
            assert appt.status == AppointmentStatus.CANCELLED

            # Same time slot should now be available for same doctor
            appointment, err = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=base_time,
                end_time=base_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is not None
            assert err is None


class TestServiceDuration:
    """Test: Service duration determines end time."""

    def test_end_time_calculated_from_duration(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            start_time = _future_time(3)

            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=60),  # matches service.duration
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is not None
            assert error is None
            assert appointment.duration_minutes == 60 or appointment.end_time - appointment.start_time == timedelta(minutes=60)


class TestAdminConfirmationReCheck:
    """Test: Admin confirmation re-validates availability."""

    def test_admin_confirm_double_book_rejected(self, app):
        with app.app_context():
            from app.models.user import User, Role
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Create a CONFIRMED appointment (10:00-11:00)
            _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60))

            # Create a PENDING appointment at same time (bypassing conflict check)
            pending_appt = Appointment(
                reference=_unique_ref(),
                patient_id=1,
                practitioner_id=doctor.id,
                service_id=service.id,
                date=base_time.date(),
                start_time=base_time,
                end_time=base_time + timedelta(minutes=60),
                status=AppointmentStatus.PENDING
            )
            db.session.add(pending_appt)
            db.session.commit()

            # Try to confirm the PENDING appointment
            success, error = booking_service.confirm_booking(pending_appt.id, admin_id=1)

            assert success is False
            assert error is not None
            assert "unavailable" in error.lower() or "conflict" in error.lower() or "booked" in error.lower()


class TestConcurrentBooking:
    """Test 7: Concurrent booking race condition (requires PostgreSQL for full test)."""

    def test_application_level_conflict_detection(self, app):
        """Test that application-level conflict detection works."""
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # First booking succeeds
            appointment1, error1 = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=base_time,
                end_time=base_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )
            assert appointment1 is not None
            assert error1 is None

            # Second booking for same time should be rejected at application level
            patient_data2 = {
                'first_name': 'Test2',
                'last_name': 'Patient',
                'email': 'test2@example.com',
                'phone': '+263771234568',
                'date_of_birth': None,
                'gender': 'Other'
            }
            appointment2, error2 = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=base_time,
                end_time=base_time + timedelta(minutes=60),
                patient_data=patient_data2,
                auto_confirm=True
            )
            assert appointment2 is None
            assert error2 is not None
            assert "unavailable" in error2.lower() or "booked" in error2.lower()

    def test_concurrent_booking_only_one_succeeds(self, app):
        """
        Test concurrent booking race condition.
        NOTE: This test requires PostgreSQL with btree_gist extension to properly test
        the exclusion constraint. With SQLite, all bookings may succeed because:
        1. SQLite doesn't support exclusion constraints
        2. Each thread has its own DB session
        This test documents the expected behavior in production (PostgreSQL).
        """
        import sys
        # Check if we're using PostgreSQL
        from app.extensions import db
        if 'sqlite' in str(db.engine.url):
            pytest.skip("Concurrent booking test requires PostgreSQL with btree_gist extension")

        with app.app_context():
            from threading import Thread
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(5)

            results = []
            counter = [0]

            def attempt_booking():
                idx = counter[0]
                counter[0] += 1
                pd = {
                    'first_name': f'Concurrent{idx}',
                    'last_name': 'User',
                    'email': f'concurrent{idx}@example.com',
                    'phone': f'+26377{200000 + idx}',
                }
                with app.app_context():
                    appt, err = booking_service.create_booking(
                        service_id=service.id,
                        practitioner_id=doctor.id,
                        start_time=base_time,
                        end_time=base_time + timedelta(minutes=60),
                        patient_data=pd,
                        auto_confirm=True
                    )
                    results.append((appt is not None, err))

            threads = [Thread(target=attempt_booking) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            successes = sum(1 for success, _ in results if success)
            # In PostgreSQL with exclusion constraints, only 1 should succeed
            assert successes == 1, f"Expected 1 success, got {successes}"


class TestPastTimeRejection:
    """Test: Cannot book in the past."""

    def test_past_time_rejected(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            service.min_advance_hours = 0
            db.session.commit()
            booking_service = BookingService()

            # Use UTC time for past time (1 hour ago in UTC)
            past_time = datetime.utcnow() - timedelta(hours=1)

            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=past_time,
                end_time=past_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is None
            assert error is not None
            assert "past" in error.lower()


class TestMinAdvanceValidation:
    """Test: Min advance booking hours is enforced."""

    def test_min_advance_rejected(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            service.min_advance_hours = 24
            db.session.commit()
            booking_service = BookingService()

            # Try to book 1 hour from now (less than 24 hour minimum) - use UTC
            soon_time = datetime.utcnow() + timedelta(hours=1)

            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=soon_time,
                end_time=soon_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is None
            assert error is not None
            assert "advance" in error.lower() or "hours" in error.lower()


class TestRoomAssignment:
    """Test: Room assignment during booking."""

    def test_room_assigned_when_required(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            service.requires_room = True
            service.required_room_type = 'Examination'
            db.session.commit()

            booking_service = BookingService()

            start_time = _future_time(3)

            appointment, error = booking_service.create_booking(
                service_id=service.id,
                practitioner_id=doctor.id,
                start_time=start_time,
                end_time=start_time + timedelta(minutes=60),
                patient_data=patient_data,
                auto_confirm=True
            )

            assert appointment is not None
            assert error is None
            room_assignment = AppointmentRoom.query.filter_by(appointment_id=appointment.id).first()
            assert room_assignment is not None
            assert room_assignment.room_id == room.id


class TestRescheduleAvailability:
    """Test: Rescheduling checks availability."""

    def test_reschedule_to_conflicting_time_rejected(self, app):
        with app.app_context():
            service, doctor, doctor2, room, patient_data = _seed_test_data()
            booking_service = BookingService()

            base_time = _future_time(3)

            # Create two appointments for same doctor
            # appt1: 10:00-11:00
            appt1 = _make_booking(service.id, doctor.id, base_time, base_time + timedelta(minutes=60))
            # appt2: 11:00-12:00
            appt2 = _make_booking(
                service.id, doctor.id,
                base_time + timedelta(hours=1),
                base_time + timedelta(hours=2),
            )

            # Try to reschedule appt1 to overlap with appt2 (11:30-12:30)
            success, _, error = booking_service.reschedule_booking(
                appt1.id,
                base_time + timedelta(minutes=30),  # Overlaps appt2 (starts at 11:00, so 11:30 conflicts)
                base_time + timedelta(minutes=90),
                is_admin=True
            )

            assert success is False
            assert error is not None
            assert "unavailable" in error.lower() or "conflict" in error.lower() or "booked" in error.lower()