import os
from app import create_app
from app.extensions import db
from apscheduler.schedulers.background import BackgroundScheduler

app = create_app(os.getenv('FLASK_ENV', 'development'))

scheduler = BackgroundScheduler()
scheduler.start()
app.scheduler = scheduler

with app.app_context():
    db.create_all()
    
    import psycopg2
    from urllib.parse import urlparse
    
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        try:
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
            
            for table, column, coltype in [
                ("services", "requires_room", "BOOLEAN DEFAULT FALSE"),
                ("services", "required_room_type", "VARCHAR(50)"),
                ("services", "min_duration", "INTEGER"),
                ("services", "max_duration", "INTEGER"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
                    print(f"[MIGRATE] Added {table}.{column}")
                except:
                    pass
            
            cur.execute("""CREATE TABLE IF NOT EXISTS staff_leave (
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
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS rooms (
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
            )""")
            
            cur.execute("""CREATE TABLE IF NOT EXISTS appointment_rooms (
                id SERIAL PRIMARY KEY,
                appointment_id INTEGER NOT NULL REFERENCES appointments(id),
                room_id INTEGER NOT NULL REFERENCES rooms(id),
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            
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
                    cur.execute("INSERT INTO rooms (name, description, room_type, capacity, floor, equipment) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING", (name, desc, rtype, cap, floor, equip))
                except:
                    pass
            
            cur.close()
            conn.close()
            print("[MIGRATE] PostgreSQL migration complete.")
        except Exception as e:
            print(f"[MIGRATE] Migration error: {e}")
    
    from app.models.user import User, Role
    from app.models.staff import Staff
    from app.models.service import Service
    from app.models.schedule import StaffSchedule
    from app.models.room import Room
    from app.models.settings import ClinicSettings
    from datetime import time
    
    # Add weekend schedules for existing staff who only have Mon-Fri
    all_staff = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    for s in all_staff:
        existing_days = {sched.day_of_week for sched in StaffSchedule.query.filter_by(staff_id=s.id, is_active=True).all()}
        for day in range(7):
            if day not in existing_days:
                sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0), is_active=True)
                db.session.add(sched)
                print(f"[MIGRATE] Added day {day} schedule for {s.first_name} {s.last_name}")
    db.session.commit()
    
    if User.query.count() == 0:
        print("[SEED] Database empty, seeding...")
        
        roles = {}
        for name, desc in [('Administrator', 'Full system access'), ('Receptionist', 'Booking management'), ('Patient', 'Patient portal access')]:
            role = Role(name=name, description=desc)
            db.session.add(role)
            roles[name] = role
        db.session.flush()
        
        admin = User(email='admin@venushealthcare.co.zw', first_name='Admin', last_name='User', phone='+263777289797', role_id=roles['Administrator'].id)
        admin.set_password('admin123')
        db.session.add(admin)
        
        receptionist = User(email='reception@venushealthcare.co.zw', first_name='Sarah', last_name='Johnson', phone='+263774890158', role_id=roles['Receptionist'].id)
        receptionist.set_password('reception123')
        db.session.add(receptionist)
        
        service_data = [
            ('General Consultation', 'Comprehensive health check-up and consultation', 30, 15, '#69A83F', 'fa-stethoscope', 50.00),
            ('Dental Checkup', 'Professional dental examination and cleaning', 45, 15, '#10B981', 'fa-tooth', 75.00),
            ('Physiotherapy', 'Physical therapy and rehabilitation session', 60, 15, '#F59E0B', 'fa-bone', 80.00),
            ('Ultrasound', 'Diagnostic ultrasound imaging', 30, 15, '#06B6D4', 'fa-x-ray', 120.00),
            ('Vaccination', 'Immunization and vaccination services', 20, 10, '#EF4444', 'fa-syringe', 35.00),
            ('Eye Examination', 'Comprehensive eye health and vision testing', 30, 15, '#8B5CF6', 'fa-eye', 60.00),
            ('ENT Consultation', 'Ear, Nose, and Throat specialist consultation', 30, 15, '#EC4899', 'fa-head-side-virus', 85.00),
            ('Laboratory Tests', 'Blood work and diagnostic laboratory testing', 15, 10, '#14B8A6', 'fa-flask', 45.00),
        ]
        
        services = {}
        for name, desc, duration, buffer, color, icon, price in service_data:
            svc = Service(name=name, description=desc, duration=duration, buffer_time=buffer, color=color, icon=icon, price=price, is_active=True, is_online_bookable=True)
            db.session.add(svc)
            services[name] = svc
        db.session.flush()
        
        practitioners_data = [
            ('Dr. James', 'Wilson', 'james.wilson@venushealthcare.co.zw', 'General Practice', 'Dr.', '#69A83F', ['General Consultation', 'Vaccination']),
            ('Dr. Emily', 'Chen', 'emily.chen@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#10B981', ['Dental Checkup']),
            ('Dr. Michael', 'Brown', 'michael.brown@venushealthcare.co.zw', 'Physiotherapy', 'Dr.', '#F59E0B', ['Physiotherapy']),
            ('Dr. Sarah', 'Davis', 'sarah.davis@venushealthcare.co.zw', 'Radiology', 'Dr.', '#06B6D4', ['Ultrasound']),
            ('Dr. David', 'Kim', 'david.kim@venushealthcare.co.zw', 'Ophthalmology', 'Dr.', '#8B5CF6', ['Eye Examination']),
            ('Dr. Lisa', 'Anderson', 'lisa.anderson@venushealthcare.co.zw', 'ENT', 'Dr.', '#EC4899', ['ENT Consultation']),
            ('Nurse Amy', 'Taylor', 'amy.taylor@venushealthcare.co.zw', 'Laboratory', 'Nurse', '#14B8A6', ['Laboratory Tests', 'Vaccination']),
        ]
        
        for first, last, email, spec, title, color, svc_names in practitioners_data:
            s = Staff(first_name=first, last_name=last, email=email, specialization=spec, title=title, color=color, is_active=True, is_practitioner=True)
            db.session.add(s)
            db.session.flush()
            for sn in svc_names:
                if sn in services:
                    s.services.append(services[sn])
            for day in range(7):
                sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0), is_active=True)
                db.session.add(sched)
        
        rooms_data = [
            ('Consultation Room 1', 'Standard consultation room for general practice', 'Consultation', 1, '1st', 'Blood pressure monitor, Thermometer'),
            ('Consultation Room 2', 'General consultation room', 'Consultation', 1, '1st', 'Stethoscope, Otoscope'),
            ('Dental Suite 1', 'Fully equipped dental examination room', 'Examination', 1, '1st', 'Dental chair, X-Ray, Ultrasonic scaler'),
            ('Dental Suite 2', 'Secondary dental room for procedures', 'Procedure', 1, '1st', 'Dental chair, Compressor'),
            ('Physiotherapy Room', 'Physical therapy and rehabilitation space', 'Procedure', 2, '2nd', 'Treatment table, Exercise equipment, Ultrasound therapy'),
            ('Ultrasound Room', 'Diagnostic imaging suite', 'Imaging', 1, '2nd', 'Ultrasound machine, Exam table'),
            ('Laboratory', 'Sample collection and basic testing', 'Laboratory', 2, '1st', 'Centrifuge, Microscope, Sample storage'),
            ('Examination Room 1', 'Multi-purpose examination room', 'Examination', 1, '1st', 'Exam table, Basic diagnostics'),
            ('Vaccination Room', 'Dedicated immunization room', 'Consultation', 1, '1st', 'Vaccine storage, Syringes, Emergency kit'),
            ('ENT Suite', 'Specialist ENT examination room', 'Examination', 1, '2nd', 'Otoscope, Nasoscope, Audiometer'),
        ]
        
        for name, desc, rtype, cap, floor, equip in rooms_data:
            room = Room(name=name, description=desc, room_type=rtype, capacity=cap, floor=floor, equipment=equip)
            db.session.add(room)
        
        settings = ClinicSettings(
            clinic_name='Venus Healthcare',
            clinic_email='medical@venushealthcare.co.zw',
            clinic_phone='+263 (0242) 339 769',
            clinic_address='',
            clinic_website=''
        )
        db.session.add(settings)
        
        db.session.commit()
        print("[SEED] Done!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
