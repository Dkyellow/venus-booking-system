"""
Migration: Add exclusion constraints for booking overlap prevention
Date: 2025-01-20

This migration adds PostgreSQL exclusion constraints to prevent double-booking
of doctors and rooms, as well as adding indexes for performance and the
confirmed_at column.
"""
import os
from urllib.parse import urlparse
from sqlalchemy import text

DATABASE_URL = os.getenv('DATABASE_URL')


def migrate_postgres():
    """Apply PostgreSQL-specific migrations."""
    if not DATABASE_URL or 'postgresql' not in DATABASE_URL:
        print("Not a PostgreSQL database - skipping PG-specific migrations")
        return

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed - skipping PG migrations")
        return

    url = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Enable btree_gist extension for exclusion constraints
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        print("[MIGRATE] Enabled btree_gist extension")
    except Exception as e:
        print(f"[WARN] Could not enable btree_gist: {e}")

    # Add confirmed_at column if not exists
    try:
        cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP WITH TIME ZONE")
        print("[MIGRATE] Added confirmed_at column")
    except Exception as e:
        print(f"[MIGRATE] confirmed_at column error: {e}")

    # Add indexes for performance
    indexes = [
        ("idx_appointments_doctor_start", "CREATE INDEX IF NOT EXISTS idx_appointments_doctor_start ON appointments(practitioner_id, start_time, end_time)"),
        ("idx_appointments_room_start", "CREATE INDEX IF NOT EXISTS idx_appointments_room_start ON appointments(start_time, end_time)"),
        ("idx_appointments_status_date", "CREATE INDEX IF NOT EXISTS idx_appointments_status_date ON appointments(status, date)"),
        ("idx_appointments_patient_id", "CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id)"),
        ("idx_appointment_rooms_appointment_id", "CREATE INDEX IF NOT EXISTS idx_appointment_rooms_appointment_id ON appointment_rooms(appointment_id)"),
        ("idx_appointment_rooms_room_id", "CREATE INDEX IF NOT EXISTS idx_appointment_rooms_room_id ON appointment_rooms(room_id)"),
    ]
    for idx_name, sql in indexes:
        try:
            cur.execute(sql)
            print(f"[MIGRATE] Created index: {idx_name}")
        except Exception as e:
            print(f"[MIGRATE] Index {idx_name} error: {e}")

    # Add exclusion constraint for doctor overlap (on confirmed/active appointments only)
    try:
        cur.execute("""
            ALTER TABLE appointments
            ADD CONSTRAINT no_doctor_booking_overlap
            EXCLUDE USING GIST (
                practitioner_id WITH =,
                tstzrange(start_time, end_time, '[)') WITH &&
            )
            WHERE (status = 'Confirmed' OR status = 'Checked In' OR status = 'In Progress')
        """)
        print("[MIGRATE] Added doctor overlap exclusion constraint")
    except psycopg2.errors.UndefinedObject as e:
        print(f"[WARN] Could not add doctor exclusion constraint: {e}")
    except psycopg2.errors.DuplicateObject:
        print("[MIGRATE] Doctor overlap constraint already exists, skipping")
    except Exception as e:
        print(f"[WARN] Doctor exclusion constraint error: {e}")

    # Add exclusion constraint for room overlap (on confirmed/active appointments only)
    try:
        cur.execute("""
            ALTER TABLE appointment_rooms
            ADD CONSTRAINT no_room_booking_overlap
            EXCLUDE USING GIST (
                room_id WITH =,
                tstzrange(
                    (SELECT start_time FROM appointments WHERE appointments.id = appointment_rooms.appointment_id),
                    (SELECT end_time FROM appointments WHERE appointments.id = appointment_rooms.appointment_id),
                    '[)'
                ) WITH &&
            )
            WHERE (
                (SELECT status FROM appointments WHERE appointments.id = appointment_rooms.appointment_id) = 'Confirmed'
                OR (SELECT status FROM appointments WHERE appointments.id = appointment_rooms.appointment_id) = 'Checked In'
                OR (SELECT status FROM appointments WHERE appointments.id = appointment_rooms.appointment_id) = 'In Progress'
            )
        """)
        print("[MIGRATE] Added room overlap exclusion constraint")
    except psycopg2.errors.UndefinedObject as e:
        print(f"[WARN] Could not add room exclusion constraint: {e}")
    except psycopg2.errors.DuplicateObject:
        print("[MIGRATE] Room overlap constraint already exists, skipping")
    except Exception as e:
        print(f"[WARN] Room exclusion constraint error: {e}")

    cur.close()
    conn.close()
    print("[MIGRATE] PostgreSQL migration complete!")


def migrate_sqalchemy():
    """Apply SQLAlchemy-managed migrations (for SQLite dev / test)."""
    from app import create_app
    from app.extensions import db
    from sqlalchemy import inspect

    app = create_app(os.getenv('FLASK_ENV', 'development'))

    with app.app_context():
        # Add confirmed_at column if it doesn't exist
        inspector = inspect(db.engine)

        if 'appointments' in [t['name'] for t in inspector.get_tables()]:
            columns = [c['name'] for c in inspector.get_columns('appointments')]
            if 'confirmed_at' not in columns:
                db.session.execute(text("ALTER TABLE appointments ADD COLUMN confirmed_at TIMESTAMP WITH TIME ZONE"))
                print("[MIGRATE] Added confirmed_at column to appointments")

        # Update any appointments missing confirmed_at
        from app.models.appointment import Appointment, AppointmentStatus
        pending_update = Appointment.query.filter(
            Appointment.status == AppointmentStatus.CONFIRMED,
            Appointment.confirmed_at.is_(None)
        ).update({'confirmed_at': Appointment.created_at}, synchronize_session='fetch')

        if pending_update:
            print(f"[MIGRATE] Updated {pending_update} appointments with confirmed_at")

        db.session.commit()
        print("[MIGRATE] SQLAlchemy migration complete!")


if __name__ == '__main__':
    migrate_postgres()
    migrate_sqalchemy()
