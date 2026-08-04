import os
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = os.getenv('DATABASE_URL')

def migrate():
    if not DATABASE_URL:
        print("No DATABASE_URL found, skipping migration.")
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
    
    migrations = [
        ("services", "requires_room", "BOOLEAN DEFAULT FALSE"),
        ("services", "required_room_type", "VARCHAR(50)"),
        ("services", "min_duration", "INTEGER"),
        ("services", "max_duration", "INTEGER"),
    ]
    
    for table, column, coltype in migrations:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
            print(f"[MIGRATE] Added {table}.{column}")
        except psycopg2.errors.DuplicateColumn:
            print(f"[MIGRATE] {table}.{column} already exists, skipping.")
        except Exception as e:
            print(f"[MIGRATE] Error adding {table}.{column}: {e}")
    
    new_tables = [
        """CREATE TABLE IF NOT EXISTS staff_leave (
            id SERIAL PRIMARY KEY,
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            leave_type VARCHAR(50) NOT NULL DEFAULT 'Leave',
            reason TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'Approved',
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS rooms (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            room_type VARCHAR(50) NOT NULL DEFAULT 'Consultation',
            capacity INTEGER DEFAULT 1,
            floor VARCHAR(20),
            equipment TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS appointment_rooms (
            id SERIAL PRIMARY KEY,
            appointment_id INTEGER NOT NULL REFERENCES appointments(id),
            room_id INTEGER NOT NULL REFERENCES rooms(id),
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    
    for sql in new_tables:
        try:
            cur.execute(sql)
            print(f"[MIGRATE] Table created or already exists.")
        except Exception as e:
            print(f"[MIGRATE] Table creation: {e}")
    
    rooms_data = [
        ('Consultation Room 1', 'Standard consultation room', 'Consultation', 1, '1st', 'Blood pressure monitor, Thermometer'),
        ('Consultation Room 2', 'General consultation room', 'Consultation', 1, '1st', 'Stethoscope, Otoscope'),
        ('Dental Suite 1', 'Fully equipped dental room', 'Examination', 1, '1st', 'Dental chair, X-Ray'),
        ('Dental Suite 2', 'Secondary dental room', 'Procedure', 1, '1st', 'Dental chair, Compressor'),
        ('Physiotherapy Room', 'Physical therapy space', 'Procedure', 2, '2nd', 'Treatment table, Exercise equipment'),
        ('Ultrasound Room', 'Diagnostic imaging suite', 'Imaging', 1, '2nd', 'Ultrasound machine'),
        ('Laboratory', 'Sample collection and testing', 'Laboratory', 2, '1st', 'Centrifuge, Microscope'),
        ('Examination Room 1', 'Multi-purpose exam room', 'Examination', 1, '1st', 'Exam table, Basic diagnostics'),
        ('Vaccination Room', 'Dedicated immunization room', 'Consultation', 1, '1st', 'Vaccine storage, Emergency kit'),
        ('ENT Suite', 'Specialist ENT room', 'Examination', 1, '2nd', 'Otoscope, Nasoscope, Audiometer'),
    ]
    
    for name, desc, rtype, cap, floor, equip in rooms_data:
        try:
            cur.execute(
                "INSERT INTO rooms (name, description, room_type, capacity, floor, equipment) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING",
                (name, desc, rtype, cap, floor, equip)
            )
        except Exception as e:
            print(f"[MIGRATE] Room insert error: {e}")
    
    print("[MIGRATE] Done!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    migrate()
