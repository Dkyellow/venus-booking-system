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
            
            # Enable btree_gist extension for exclusion constraints
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
                print("[MIGRATE] Enabled btree_gist extension")
            except Exception as e:
                print(f"[WARN] Could not enable btree_gist: {e}")
            
            for table, column, coltype in [
                ("services", "requires_room", "BOOLEAN DEFAULT FALSE"),
                ("services", "required_room_type", "VARCHAR(50)"),
                ("services", "min_duration", "INTEGER"),
                ("services", "max_duration", "INTEGER"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {coltype}")
                    print(f"[MIGRATE] Added {table}.{column}")
                except:
                    pass
            
            # Add confirmed_at column
            try:
                cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMP WITH TIME ZONE")
                print("[MIGRATE] Added confirmed_at column")
            except Exception as e:
                print(f"[WARN] confirmed_at column error: {e}")
            
            # Add exclusion constraints for overlap prevention
            try:
                cur.execute("""
                    ALTER TABLE appointments
                    ADD CONSTRAINT no_doctor_booking_overlap
                    EXCLUDE USING GIST (
                        practitioner_id WITH =,
                        tstzrange(start_time, end_time, '[)') WITH &&
                    )
                    WHERE (coalesce(status::text, '') IN ('Confirmed', 'Checked In', 'In Progress'))
                """)
                print("[MIGRATE] Added doctor overlap exclusion constraint")
            except psycopg2.errors.DuplicateObject:
                print("[MIGRATE] Doctor overlap constraint already exists, skipping")
            except Exception as e:
                print(f"[WARN] Doctor exclusion constraint error: {e}")
            
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
                        (SELECT coalesce(status::text, '') FROM appointments WHERE appointments.id = appointment_rooms.appointment_id) IN ('Confirmed', 'Checked In', 'In Progress')
                    )
                """)
                print("[MIGRATE] Added room overlap exclusion constraint")
            except psycopg2.errors.DuplicateObject:
                print("[MIGRATE] Room overlap constraint already exists, skipping")
            except Exception as e:
                print(f"[WARN] Room exclusion constraint error: {e}")
            
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
            ]
            for name, desc, rtype, cap, floor, equip in rooms_data:
                try:
                    cur.execute("INSERT INTO rooms (name, description, room_type, capacity, floor, equipment) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (name) DO NOTHING", (name, desc, rtype, cap, floor, equip))
                except:
                    pass
            
            # Add indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_appointments_doctor_start ON appointments(practitioner_id, start_time, end_time)",
                "CREATE INDEX IF NOT EXISTS idx_appointments_status_date ON appointments(status, date)",
                "CREATE INDEX IF NOT EXISTS idx_appointments_patient_id ON appointments(patient_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_rooms_appointment_id ON appointment_rooms(appointment_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointment_rooms_room_id ON appointment_rooms(room_id)",
            ]
            for idx_sql in indexes:
                try:
                    cur.execute(f"DROP INDEX IF EXISTS {idx_sql.split('CREATE INDEX IF NOT EXISTS')[1].split(' ON')[0].strip()}")
                    cur.execute(idx_sql.replace("IF NOT EXISTS", ""))
                    print(f"[MIGRATE] Created index from: {idx_sql[:80]}")
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
                sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0), is_active=True)
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
            ('General Consultation', 'Comprehensive medical consultations for adults and children.', 30, 15, '#69A83F', 'fa-stethoscope', 50.00),
            ('Dental Checkup', 'Professional dental examination, cleaning, and oral health assessment.', 45, 15, '#10B981', 'fa-tooth', 75.00),
            ('Dental Fillings', 'Tooth-coloured composite fillings to restore decayed or damaged teeth.', 45, 15, '#10B981', 'fa-tooth', 80.00),
            ('Dental Cleaning', 'Professional teeth cleaning and polishing to prevent gum disease.', 30, 15, '#10B981', 'fa-tooth', 60.00),
            ('Orthodontics', 'Braces and clear aligners to straighten teeth and correct bite issues.', 60, 15, '#10B981', 'fa-teeth', 150.00),
            ('Dental Implants', 'Permanent tooth replacement using titanium implants.', 90, 30, '#10B981', 'fa-tooth', 500.00),
            ('Teeth Whitening', 'Professional teeth whitening for a brighter, whiter smile.', 60, 15, '#10B981', 'fa-sun', 120.00),
            ('Dental Crowns & Bridges', 'Custom-made crowns and bridges to restore damaged or missing teeth.', 60, 30, '#10B981', 'fa-tooth', 200.00),
            ('Veneers', 'Thin porcelain shells bonded to teeth to improve appearance.', 60, 30, '#10B981', 'fa-tooth', 250.00),
            ('Paediatric Dentistry', 'Gentle dental care for children in a friendly environment.', 30, 15, '#10B981', 'fa-baby', 50.00),
            ('Dental Extractions', 'Safe and painless tooth extraction when necessary.', 45, 15, '#10B981', 'fa-tooth', 100.00),
            ('Dental X-Rays', 'Digital dental X-rays for accurate diagnosis.', 15, 10, '#10B981', 'fa-x-ray', 40.00),
            ('Dental Emergencies', 'Same-day emergency dental care for toothaches and trauma.', 30, 15, '#10B981', 'fa-exclamation-triangle', 75.00),
            ('Smile Makeover', 'Complete smile transformation combining multiple treatments.', 90, 30, '#10B981', 'fa-smile', 800.00),
            ('Clear Aligners', 'Invisible aligners for discreet teeth straightening.', 60, 15, '#10B981', 'fa-teeth-open', 200.00),
            ('General Practice', 'Comprehensive primary healthcare for individuals and families.', 30, 15, '#69A83F', 'fa-stethoscope', 50.00),
            ('Family Medicine', 'Holistic healthcare for the whole family.', 30, 15, '#69A83F', 'fa-users', 50.00),
            ('Chronic Disease Management', 'Ongoing management of diabetes, hypertension, asthma, and heart disease.', 30, 15, '#69A83F', 'fa-heartbeat', 60.00),
            ('Travel Clinic', 'Travel health consultations, vaccinations, and medications.', 30, 15, '#69A83F', 'fa-plane', 75.00),
            ('Laboratory Testing', 'On-site laboratory for blood work and diagnostic testing.', 15, 10, '#14B8A6', 'fa-flask', 45.00),
            ('ECG', 'Electrocardiogram testing for heart health assessment.', 15, 10, '#14B8A6', 'fa-heartbeat', 40.00),
            ('Specialist Consultations', 'Access to specialist doctors in psychiatry, dermatology, and other specialties.', 45, 15, '#8B5CF6', 'fa-user-md', 100.00),
            ('Vaccination Clinic', 'Comprehensive vaccination services including childhood immunisations and travel vaccines.', 20, 10, '#EF4444', 'fa-syringe', 35.00),
            ('Dermatology', 'Skin care consultations, diagnosis, and treatment of skin conditions.', 30, 15, '#F59E0B', 'fa-hand-holding-medical', 80.00),
            ('Paediatrics', 'Specialised healthcare for infants, children, and adolescents.', 30, 15, '#EC4899', 'fa-baby', 60.00),
            ('Mental Health Services', 'Comprehensive psychiatric and psychological care.', 60, 15, '#8B5CF6', 'fa-brain', 100.00),
            ('Psychiatric Evaluations', 'Comprehensive psychiatric assessments for diagnosis and treatment planning.', 60, 15, '#8B5CF6', 'fa-brain', 120.00),
            ('Clinical Psychology', 'Individual therapy with qualified clinical psychologists.', 50, 15, '#8B5CF6', 'fa-comments', 80.00),
            ('Educational Assessments', 'Comprehensive educational and learning assessments for children and adults.', 90, 30, '#8B5CF6', 'fa-graduation-cap', 150.00),
            ('Physiotherapy', 'Physical therapy and rehabilitation sessions.', 60, 15, '#F59E0B', 'fa-bone', 80.00),
            ('Diagnostic Imaging', 'Digital X-rays, ultrasound, and other diagnostic imaging services.', 30, 15, '#06B6D4', 'fa-x-ray', 120.00),
            ('Preventative Health Screenings', 'Comprehensive health screenings and wellness checks.', 30, 15, '#69A83F', 'fa-shield-alt', 70.00),
            ('Smile Design', 'Digital smile design using advanced technology.', 45, 15, '#10B981', 'fa-magic', 100.00),
            ('Pharmacy', 'On-site pharmacy for prescription filling and OTC medications.', 15, 5, '#14B8A6', 'fa-prescription-bottle-alt', 0.00),
        ]
        
        services = {}
        for name, desc, duration, buffer, color, icon, price in service_data:
            svc = Service(name=name, description=desc, duration=duration, buffer_time=buffer, color=color, icon=icon, price=price, is_active=True, is_online_bookable=True)
            db.session.add(svc)
            services[name] = svc
        db.session.flush()
        
        practitioners_data = [
            ('Knowledge', 'Tsungu', 'knowledge.tsungu@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#69A83F', ['General Consultation', 'Dental Checkup', 'Dental Fillings', 'Dental Cleaning', 'Orthodontics', 'Dental Implants', 'Teeth Whitening', 'Dental Crowns & Bridges', 'Veneers', 'Paediatric Dentistry', 'Dental Extractions', 'Dental X-Rays', 'Dental Emergencies', 'Smile Makeover', 'Clear Aligners', 'Smile Design']),
            ('Rukudzo', 'Mwamuka', 'rukudzo.mwamuka@venushealthcare.co.zw', 'Psychiatry', 'Dr.', '#8B5CF6', ['Mental Health Services', 'Psychiatric Evaluations', 'Clinical Psychology']),
            ('James', 'Wilson', 'james.wilson@venushealthcare.co.zw', 'General Practice', 'Dr.', '#69A83F', ['General Consultation', 'Family Medicine', 'Chronic Disease Management', 'Travel Clinic', 'Preventative Health Screenings']),
            ('Emily', 'Chen', 'emily.chen@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#10B981', ['Dental Checkup', 'Dental Fillings', 'Dental Cleaning', 'Dental Emergencies']),
            ('Sarah', 'Davis', 'sarah.davis@venushealthcare.co.zw', 'Paediatrics', 'Dr.', '#EC4899', ['Paediatrics', 'Vaccination Clinic']),
            ('Michael', 'Brown', 'michael.brown@venushealthcare.co.zw', 'Physiotherapy', 'Dr.', '#F59E0B', ['Physiotherapy']),
            ('Lisa', 'Anderson', 'lisa.anderson@venushealthcare.co.zw', 'Dermatology', 'Dr.', '#F59E0B', ['Dermatology', 'General Consultation']),
            ('David', 'Kim', 'david.kim@venushealthcare.co.zw', 'Clinical Psychology', 'Dr.', '#8B5CF6', ['Clinical Psychology', 'Educational Assessments', 'Mental Health Services']),
            ('Amy', 'Taylor', 'amy.taylor@venushealthcare.co.zw', 'Nursing', 'Nurse', '#14B8A6', ['Vaccination Clinic', 'Laboratory Testing', 'ECG']),
            ('Grace', 'Moyo', 'grace.moyo@venushealthcare.co.zw', 'Diagnostic Imaging', 'Dr.', '#06B6D4', ['Diagnostic Imaging', 'Laboratory Testing']),
        ]
        
        for first, last, email, spec, title, color, svc_names in practitioners_data:
            s = Staff(first_name=first, last_name=last, email=email, specialization=spec, title=title, color=color, is_active=True, is_practitioner=True)
            db.session.add(s)
            db.session.flush()
            for sn in svc_names:
                if sn in services:
                    s.services.append(services[sn])
            for day in range(7):
                sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0), is_active=True)
                db.session.add(sched)
        
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
            room = Room(name=name, description=desc, room_type=rtype, capacity=cap, floor=floor, equipment=equip)
            db.session.add(room)
        
        settings = ClinicSettings(
            clinic_name='Venus Medical & Dental Centre',
            clinic_email='medical@venushealthcare.co.zw',
            clinic_phone='+263 (0242) 339 769',
            clinic_address='4 Cuba Ave, Mount Pleasant, Harare, Zimbabwe',
            clinic_website='https://venushealthcare.co.zw'
        )
        db.session.add(settings)
        
        db.session.commit()
        print("[SEED] Done!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
