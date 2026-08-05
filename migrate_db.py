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
        ('Consultation Room 1', 'Standard consultation room for general practice', 'Consultation', 1, '1st', 'Blood pressure monitor, Thermometer'),
        ('Consultation Room 2', 'General consultation room', 'Consultation', 1, '1st', 'Stethoscope, Otoscope'),
        ('Dental Suite 1', 'Fully equipped dental examination room with CEREC technology', 'Examination', 1, '1st', 'Dental chair, CEREC, Panorex, Digital Intraoral Camera'),
        ('Dental Suite 2', 'Secondary dental room for procedures', 'Procedure', 1, '1st', 'Dental chair, Compressor'),
        ('Dental Suite 3', 'Specialist dental room for orthodontics and implants', 'Procedure', 1, '1st', 'Dental chair, Implant surgical kit, Orthodontic instruments'),
        ('Physiotherapy Room', 'Physical therapy and rehabilitation space', 'Procedure', 2, '2nd', 'Treatment table, Exercise equipment, Ultrasound therapy'),
        ('Mental Health Suite', 'Private consultation room for psychiatric and psychological services', 'Consultation', 1, '2nd', 'Comfortable seating, Sound insulation, Therapy materials'),
        ('Paediatric Room', 'Child-friendly examination and treatment room', 'Examination', 1, '1st', 'Child-sized equipment, Colourful decor, Toys'),
        ('Dermatology Room', 'Specialist dermatology examination room', 'Examination', 1, '2nd', 'Dermatoscope, Exam table, Good lighting'),
        ('Laboratory', 'On-site laboratory for blood work and diagnostic testing', 'Laboratory', 2, '1st', 'Centrifuge, Microscope, Sample storage, Blood collection equipment'),
        ('Vaccination Room', 'Dedicated immunisation room with vaccine storage', 'Consultation', 1, '1st', 'Vaccine refrigerator, Syringes, Emergency kit'),
        ('Pharmacy', 'On-site pharmacy for prescription and OTC medications', 'Pharmacy', 2, '1st', 'Medication storage, Dispensing counter'),
        ('Diagnostic Imaging Room', 'Digital X-ray and ultrasound imaging suite', 'Imaging', 1, '2nd', 'Digital X-ray machine, Ultrasound machine'),
        ('ECG Room', 'Electrocardiogram testing room', 'Examination', 1, '1st', 'ECG machine, Monitoring equipment'),
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

# Also run via Flask app context for ORM-based migrations
import os
from app import create_app
from app.extensions import db

def migrate_schedules():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        from app.models.staff import Staff
        from app.models.schedule import StaffSchedule
        from datetime import time
        
        all_staff = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
        for s in all_staff:
            existing_days = {sched.day_of_week for sched in StaffSchedule.query.filter_by(staff_id=s.id, is_active=True).all()}
            for day in range(7):
                if day not in existing_days:
                    sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0), is_active=True)
                    db.session.add(sched)
                    print(f"[MIGRATE] Added day {day} schedule for {s.first_name} {s.last_name}")
        db.session.commit()
        print("[MIGRATE] Weekend schedules migration complete.")
