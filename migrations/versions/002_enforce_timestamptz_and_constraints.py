"""
Migration: Ensure timezone-aware timestamps and add exclusion constraints
Date: 2026-08-12

This migration ensures appointment timestamps are stored as TIMESTAMP WITH TIME ZONE
and enforces exclusion constraints to prevent overlapping confirmed bookings.
"""
import os
from urllib.parse import urlparse

DATABASE_URL = os.getenv('DATABASE_URL')


def migrate_postgres():
    if not DATABASE_URL or 'postgres' not in DATABASE_URL:
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

    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        print("[MIGRATE] Enabled btree_gist extension")
    except Exception as e:
        print(f"[WARN] Could not enable btree_gist: {e}")

    # Alter appointments timestamp columns to timestamptz
    try:
        cur.execute("ALTER TABLE appointments ALTER COLUMN start_time TYPE TIMESTAMP WITH TIME ZONE USING start_time AT TIME ZONE 'UTC'")
        cur.execute("ALTER TABLE appointments ALTER COLUMN end_time TYPE TIMESTAMP WITH TIME ZONE USING end_time AT TIME ZONE 'UTC'")
        cur.execute("ALTER TABLE appointments ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
        cur.execute("ALTER TABLE appointments ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")
        cur.execute("ALTER TABLE appointments ALTER COLUMN cancelled_at TYPE TIMESTAMP WITH TIME ZONE USING cancelled_at AT TIME ZONE 'UTC'")
        cur.execute("ALTER TABLE appointments ALTER COLUMN confirmed_at TYPE TIMESTAMP WITH TIME ZONE USING confirmed_at AT TIME ZONE 'UTC'")
        print("[MIGRATE] Converted appointment timestamp columns to timestamptz where applicable")
    except Exception as e:
        print(f"[MIGRATE] Appointment timestamp conversion warning: {e}")

    # Alter appointment_rooms assigned_at
    try:
        cur.execute("ALTER TABLE appointment_rooms ALTER COLUMN assigned_at TYPE TIMESTAMP WITH TIME ZONE USING assigned_at AT TIME ZONE 'UTC'")
        print("[MIGRATE] Converted appointment_rooms.assigned_at to timestamptz")
    except Exception as e:
        print(f"[MIGRATE] appointment_rooms assigned_at conversion warning: {e}")

    # Create indexes
    indexes = [
        ("idx_appointments_practitioner_time", "CREATE INDEX IF NOT EXISTS idx_appointments_practitioner_time ON appointments(practitioner_id, start_time, end_time)"),
        ("idx_appointments_status_date", "CREATE INDEX IF NOT EXISTS idx_appointments_status_date ON appointments(status, date)"),
        ("idx_appointment_rooms_room_id", "CREATE INDEX IF NOT EXISTS idx_appointment_rooms_room_id ON appointment_rooms(room_id)")
    ]
    for name, sql in indexes:
        try:
            cur.execute(sql)
            print(f"[MIGRATE] Created index: {name}")
        except Exception as e:
            print(f"[MIGRATE] Index {name} error: {e}")

    # Add exclusion constraint for practitioner overlap
    try:
        cur.execute("""
            ALTER TABLE appointments
            ADD CONSTRAINT IF NOT EXISTS no_doctor_booking_overlap
            EXCLUDE USING GIST (
                practitioner_id WITH =,
                tstzrange(start_time, end_time, '[)') WITH &&
            )
            WHERE (status = 'Confirmed' OR status = 'Checked In' OR status = 'In Progress')
        """)
        print("[MIGRATE] Added/ensured doctor overlap exclusion constraint")
    except Exception as e:
        print(f"[MIGRATE] Doctor exclusion constraint error: {e}")

    # Add exclusion constraint for room overlap on appointment_rooms
    try:
        cur.execute("""
            ALTER TABLE appointment_rooms
            ADD CONSTRAINT IF NOT EXISTS no_room_booking_overlap
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
        print("[MIGRATE] Added/ensured room overlap exclusion constraint")
    except Exception as e:
        print(f"[MIGRATE] Room exclusion constraint error: {e}")

    cur.close()
    conn.close()
    print("[MIGRATE] PostgreSQL timezone + constraints migration complete!")


def migrate_sqalchemy():
    # Fallback for non-Postgres environments - ensure confirmed_at exists
    from app import create_app
    from app.extensions import db
    from sqlalchemy import inspect, text

    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        inspector = inspect(db.engine)
        if 'appointments' in [t['name'] for t in inspector.get_tables()]:
            columns = [c['name'] for c in inspector.get_columns('appointments')]
            if 'confirmed_at' not in columns:
                try:
                    db.session.execute(text("ALTER TABLE appointments ADD COLUMN confirmed_at TIMESTAMP WITH TIME ZONE"))
                    print("[MIGRATE] Added confirmed_at column")
                    db.session.commit()
                except Exception as e:
                    print(f"[MIGRATE] Could not add confirmed_at: {e}")


if __name__ == '__main__':
    migrate_postgres()
    migrate_sqalchemy()
