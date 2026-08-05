import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date, time, timedelta
from app import create_app
from app.extensions import db
from app.models.user import User, Role
from app.models.patient import Patient
from app.models.staff import Staff
from app.models.service import Service, ServiceCategory
from app.models.appointment import Appointment, AppointmentStatus, AppointmentHistory
from app.models.schedule import StaffSchedule
from app.models.room import Room
from app.models.settings import ClinicSettings


def seed_database():
    app = create_app('development')
    with app.app_context():
        db.create_all()

        print("Seeding roles...")
        roles = {}
        for name, desc in [('Administrator', 'Full system access'), ('Receptionist', 'Booking management'), ('Patient', 'Patient portal access')]:
            role = Role.query.filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.session.add(role)
            roles[name] = role
        db.session.flush()

        print("Seeding admin user...")
        admin = User.query.filter_by(email='admin@venushealthcare.co.zw').first()
        if not admin:
            admin = User(email='admin@venushealthcare.co.zw', first_name='Admin', last_name='User', phone='+263777289797', role_id=roles['Administrator'].id)
            admin.set_password('admin123')
            db.session.add(admin)

        print("Seeding receptionist...")
        receptionist = User.query.filter_by(email='reception@venushealthcare.co.zw').first()
        if not receptionist:
            receptionist = User(email='reception@venushealthcare.co.zw', first_name='Sarah', last_name='Johnson', phone='+263774890158', role_id=roles['Receptionist'].id)
            receptionist.set_password('reception123')
            db.session.add(receptionist)

        print("Seeding services...")
        service_data = [
            ('General Consultation', 'Comprehensive medical consultations for adults and children. Our experienced general practitioners provide thorough health assessments, diagnoses, and treatment plans.', 30, 15, '#69A83F', 'fa-stethoscope', 50.00),
            ('Dental Checkup', 'Professional dental examination, cleaning, and oral health assessment. Includes X-rays if needed and personalised dental care advice.', 45, 15, '#10B981', 'fa-tooth', 75.00),
            ('Dental Fillings', 'Tooth-coloured composite fillings to restore decayed or damaged teeth. Painless procedure with modern materials.', 45, 15, '#10B981', 'fa-tooth', 80.00),
            ('Dental Cleaning', 'Professional teeth cleaning and polishing to remove plaque and tartar. Prevents gum disease and maintains oral health.', 30, 15, '#10B981', 'fa-tooth', 60.00),
            ('Orthodontics', 'Braces and clear aligners to straighten teeth and correct bite issues. Comprehensive orthodontic treatment for all ages.', 60, 15, '#10B981', 'fa-teeth', 150.00),
            ('Dental Implants', 'Permanent tooth replacement using titanium implants. Natural-looking and long-lasting solution for missing teeth.', 90, 30, '#10B981', 'fa-tooth', 500.00),
            ('Teeth Whitening', 'Professional teeth whitening for a brighter, whiter smile. Safe and effective in-office treatment.', 60, 15, '#10B981', 'fa-sun', 120.00),
            ('Dental Crowns & Bridges', 'Custom-made crowns and bridges to restore damaged or missing teeth. Natural appearance and comfortable fit.', 60, 30, '#10B981', 'fa-tooth', 200.00),
            ('Veneers', 'Thin porcelain shells bonded to teeth to improve appearance. Transform your smile with minimal preparation.', 60, 30, '#10B981', 'fa-tooth', 250.00),
            ('Paediatric Dentistry', 'Gentle dental care for children in a comfortable, friendly environment. Preventive treatments and education.', 30, 15, '#10B981', 'fa-baby', 50.00),
            ('Dental Extractions', 'Safe and painless tooth extraction when necessary. Includes surgical and wisdom tooth removal.', 45, 15, '#10B981', 'fa-tooth', 100.00),
            ('Dental X-Rays', 'Digital dental X-rays for accurate diagnosis. Low radiation exposure with instant results.', 15, 10, '#10B981', 'fa-x-ray', 40.00),
            ('Dental Emergencies', 'Same-day emergency dental care for toothaches, broken teeth, and dental trauma.', 30, 15, '#10B981', 'fa-exclamation-triangle', 75.00),
            ('Smile Makeover', 'Complete smile transformation combining multiple dental treatments. Custom treatment plan for your dream smile.', 90, 30, '#10B981', 'fa-smile', 800.00),
            ('Clear Aligners', 'Invisible aligners for discreet teeth straightening. Removable and comfortable for adults and teens.', 60, 15, '#10B981', 'fa-teeth-open', 200.00),
            ('General Practice', 'Comprehensive primary healthcare for individuals and families. Routine check-ups, chronic disease management, and preventive care.', 30, 15, '#69A83F', 'fa-stethoscope', 50.00),
            ('Family Medicine', 'Holistic healthcare for the whole family. From children to elderly, we provide continuity of care across generations.', 30, 15, '#69A83F', 'fa-users', 50.00),
            ('Chronic Disease Management', 'Ongoing monitoring and management of chronic conditions including diabetes, hypertension, asthma, and heart disease.', 30, 15, '#69A83F', 'fa-heartbeat', 60.00),
            ('Travel Clinic', 'Travel health consultations, vaccinations, and medications for international travel. Personalised travel health advice.', 30, 15, '#69A83F', 'fa-plane', 75.00),
            ('Laboratory Testing', 'On-site laboratory for blood work, urine tests, and other diagnostic testing. Fast and accurate results.', 15, 10, '#14B8A6', 'fa-flask', 45.00),
            ('ECG', 'Electrocardiogram testing for heart health assessment. Quick, non-invasive cardiac screening.', 15, 10, '#14B8A6', 'fa-heartbeat', 40.00),
            ('Specialist Consultations', 'Access to specialist doctors in psychiatry, dermatology, and other medical specialties. Referral-based and self-referral appointments.', 45, 15, '#8B5CF6', 'fa-user-md', 100.00),
            ('Vaccination Clinic', 'Comprehensive vaccination services including childhood immunisations, travel vaccines, and COVID-19 vaccinations. All standard vaccines available.', 20, 10, '#EF4444', 'fa-syringe', 35.00),
            ('Dermatology', 'Skin care consultations, diagnosis, and treatment of skin conditions. Acne, eczema, psoriasis, and skin cancer screening.', 30, 15, '#F59E0B', 'fa-hand-holding-medical', 80.00),
            ('Paediatrics', 'Specialised healthcare for infants, children, and adolescents. Developmental assessments, immunisations, and paediatric consultations.', 30, 15, '#EC4899', 'fa-baby', 60.00),
            ('Mental Health Services', 'Comprehensive psychiatric and psychological care including individual therapy, group therapy, CBT, family therapy, and psychiatric evaluations.', 60, 15, '#8B5CF6', 'fa-brain', 100.00),
            ('Psychiatric Evaluations', 'Comprehensive psychiatric assessments for diagnosis and treatment planning. Includes medication management and follow-up.', 60, 15, '#8B5CF6', 'fa-brain', 120.00),
            ('Clinical Psychology', 'Individual therapy sessions with qualified clinical psychologists. Evidence-based treatment for anxiety, depression, and trauma.', 50, 15, '#8B5CF6', 'fa-comments', 80.00),
            ('Educational Assessments', 'Comprehensive educational and learning assessments for children and adults. ADHD assessments and learning disability evaluations.', 90, 30, '#8B5CF6', 'fa-graduation-cap', 150.00),
            ('Physiotherapy', 'Physical therapy and rehabilitation sessions. Treatment for musculoskeletal conditions, sports injuries, and post-surgical recovery.', 60, 15, '#F59E0B', 'fa-bone', 80.00),
            ('Diagnostic Imaging', 'Digital X-rays, ultrasound, and other diagnostic imaging services. State-of-the-art equipment for accurate diagnosis.', 30, 15, '#06B6D4', 'fa-x-ray', 120.00),
            ('Preventative Health Screenings', 'Comprehensive health screenings and wellness checks. Early detection of health issues for better outcomes.', 30, 15, '#69A83F', 'fa-shield-alt', 70.00),
            ('Smile Design', 'Digital smile design using advanced technology. Visualise your new smile before treatment begins.', 45, 15, '#10B981', 'fa-magic', 100.00),
            ('Pharmacy', 'On-site pharmacy for convenient prescription filling and over-the-counter medications. Quality pharmaceutical services.', 15, 5, '#14B8A6', 'fa-prescription-bottle-alt', 0.00),
        ]

        services = {}
        for name, desc, duration, buffer, color, icon, price in service_data:
            svc = Service.query.filter_by(name=name).first()
            if not svc:
                svc = Service(name=name, description=desc, duration=duration, buffer_time=buffer, color=color, icon=icon, price=price, is_active=True, is_online_bookable=True)
                db.session.add(svc)
            services[name] = svc
        db.session.flush()

        print("Seeding practitioners...")
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

        staff_list = {}
        for first, last, email, spec, title, color, svc_names in practitioners_data:
            s = Staff.query.filter_by(email=email).first()
            if not s:
                s = Staff(first_name=first, last_name=last, email=email, specialization=spec, title=title, color=color, is_active=True, is_practitioner=True)
                db.session.add(s)
                db.session.flush()
                for sn in svc_names:
                    if sn in services:
                        s.services.append(services[sn])
                for day in range(7):
                    sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(8, 0), end_time=time(17, 0), is_active=True)
                    db.session.add(sched)
            staff_list[email] = s
        db.session.flush()

        print("Seeding rooms...")
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

        rooms = {}
        for name, desc, rtype, cap, floor, equip in rooms_data:
            room = Room.query.filter_by(name=name).first()
            if not room:
                room = Room(name=name, description=desc, room_type=rtype, capacity=cap, floor=floor, equipment=equip)
                db.session.add(room)
            rooms[name] = room
        db.session.flush()

        print("Seeding clinic settings...")
        settings = ClinicSettings.query.first()
        if not settings:
            settings = ClinicSettings(
                clinic_name='Venus Medical & Dental Centre',
                clinic_email='medical@venushealthcare.co.zw',
                clinic_phone='+263 (0242) 339 769',
                clinic_address='4 Cuba Ave, Mount Pleasant, Harare, Zimbabwe',
                clinic_website='https://venushealthcare.co.zw'
            )
            db.session.add(settings)

        db.session.commit()
        print("\n=== Seed Complete ===")
        print("Admin: admin@venushealthcare.co.zw / admin123")
        print("Receptionist: reception@venushealthcare.co.zw / reception123")
        print(f"Services: {len(services)}")
        print(f"Practitioners: {len(staff_list)}")
        print(f"Rooms: {len(rooms)}")


if __name__ == '__main__':
    seed_database()
