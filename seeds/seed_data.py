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
        
        # Create categories first
        categories_data = [
            ('General Practitioner', 'General practice, family medicine, family planning & more', '#69A83F', 'fa-stethoscope', 1),
            ('Dental', 'General dentistry, orthodontics, Restorative & Aesthetic dentistry', '#10B981', 'fa-tooth', 2),
            ('Mental Health Specialist Clinics', 'Psychiatrist, Clinical Neuropsychologist, Educational Psychologist', '#8B5CF6', 'fa-brain', 3),
            ('Dermatology', 'Specialist adult and Paediatric Dermatology managing a range of skin conditions', '#F59E0B', 'fa-hand-holding-medical', 4),
            ('Physiotherapy', 'Physical therapy and rehabilitation for musculoskeletal conditions', '#F59E0B', 'fa-bone', 5),
            ('Paediatrics', 'Specialised paediatrician consultation', '#EC4899', 'fa-baby', 6),
            ('Vaccinations & Health Screenings', 'Vaccines & screenings for travel or individual needs, as well as baby clinic immunizations and weighing', '#EF4444', 'fa-syringe', 7),
            ('Ultrasound', 'Diagnostic ultrasound imaging', '#06B6D4', 'fa-x-ray', 8),
            ('Diagnostic Services', 'On-site laboratory services for testing and diagnoses', '#14B8A6', 'fa-flask', 9),
            ('Pharmacy', 'Fully stocked pharmacy for your prescriptions and health needs', '#14B8A6', 'fa-prescription-bottle-alt', 10),
        ]
        
        categories = {}
        for name, desc, color, icon, sort_order in categories_data:
            cat = ServiceCategory.query.filter_by(name=name).first()
            if not cat:
                cat = ServiceCategory(name=name, description=desc, color=color, icon=icon, is_active=True, sort_order=sort_order)
                db.session.add(cat)
            categories[name] = cat
        db.session.flush()
        
        service_data = [
            # General Practitioner category
            ('General Consultation', 'Comprehensive medical consultations for adults and children. Our experienced general practitioners provide thorough health assessments, diagnoses, and treatment plans.', 30, 15, '#69A83F', 'fa-stethoscope', 50.00, 'General Practitioner', True),
            ('Family Medicine', 'Holistic healthcare for the whole family. From children to elderly, we provide continuity of care across generations.', 30, 15, '#69A83F', 'fa-users', 50.00, 'General Practitioner', True),
            ('Chronic Disease Management', 'Ongoing monitoring and management of chronic conditions including diabetes, hypertension, asthma, and heart disease.', 30, 15, '#69A83F', 'fa-heartbeat', 60.00, 'General Practitioner', True),
            ('Travel Clinic', 'Travel health consultations, vaccinations, and medications for international travel. Personalised travel health advice.', 30, 15, '#69A83F', 'fa-plane', 75.00, 'General Practitioner', True),
            
            # Dental category
            ('General Dentistry', 'Routine dental check-ups, cleanings, fillings, and preventive care. Comprehensive dental examinations for all ages.', 45, 15, '#10B981', 'fa-tooth', 75.00, 'Dental', True),
            ('Orthodontics', 'Braces and clear aligners to straighten teeth and correct bite issues. Comprehensive orthodontic treatment for all ages.', 60, 15, '#10B981', 'fa-teeth', 150.00, 'Dental', True),
            ('Restorative & Aesthetic Dentistry', 'Crowns, bridges, veneers, implants, and smile makeovers. Transform your smile with modern restorative and cosmetic treatments.', 90, 30, '#10B981', 'fa-smile', 500.00, 'Dental', True),
            ('Dental Emergencies', 'Same-day emergency dental care for toothaches, broken teeth, and dental trauma.', 30, 15, '#10B981', 'fa-exclamation-triangle', 75.00, 'Dental', True),
            
            # Mental Health Specialist Clinics category
            ('Psychiatrist', 'A medical doctor who diagnoses, treats, and manages mental health disorders, often including medication management.', 60, 15, '#8B5CF6', 'fa-brain', 120.00, 'Mental Health Specialist Clinics', True),
            ('Clinical Neuropsychologist', 'Specializes in understanding how brain function affects behavior and cognition, often assessing memory, learning, or neurological conditions.', 90, 30, '#8B5CF6', 'fa-brain', 150.00, 'Mental Health Specialist Clinics', True),
            ('Educational Psychologist', 'Helps with learning difficulties, school performance issues, and emotional challenges affecting academic success.', 90, 30, '#8B5CF6', 'fa-graduation-cap', 150.00, 'Mental Health Specialist Clinics', True),
            
            # Dermatology
            ('Dermatology', 'Skin care consultations, diagnosis, and treatment of skin conditions. Acne, eczema, psoriasis, and skin cancer screening.', 30, 15, '#F59E0B', 'fa-hand-holding-medical', 80.00, 'Dermatology', True),
            
            # Physiotherapy
            ('Physiotherapy', 'Physical therapy and rehabilitation sessions. Treatment for musculoskeletal conditions, sports injuries, and post-surgical recovery.', 60, 15, '#F59E0B', 'fa-bone', 80.00, 'Physiotherapy', True),
            
            # Paediatrics
            ('Paediatrics', 'Specialised healthcare for infants, children, and adolescents. Developmental assessments, immunisations, and paediatric consultations.', 30, 15, '#EC4899', 'fa-baby', 60.00, 'Paediatrics', True),
            
            # Vaccinations & Health Screenings
            ('Vaccination Clinic', 'Comprehensive vaccination services including childhood immunisations, travel vaccines, and COVID-19 vaccinations. All standard vaccines available.', 20, 10, '#EF4444', 'fa-syringe', 35.00, 'Vaccinations & Health Screenings', True),
            ('Preventative Health Screenings', 'Comprehensive health screenings and wellness checks. Early detection of health issues for better outcomes.', 30, 15, '#69A83F', 'fa-shield-alt', 70.00, 'Vaccinations & Health Screenings', True),
            
            # Ultrasound
            ('Ultrasound', 'Diagnostic ultrasound imaging for accurate diagnosis. State-of-the-art equipment operated by experienced sonographers.', 30, 15, '#06B6D4', 'fa-x-ray', 120.00, 'Ultrasound', True),
            
            # Diagnostic Services
            ('Laboratory Testing', 'On-site laboratory for blood work, urine tests, and other diagnostic testing. Fast and accurate results.', 15, 10, '#14B8A6', 'fa-flask', 45.00, 'Diagnostic Services', True),
            ('ECG', 'Electrocardiogram testing for heart health assessment. Quick, non-invasive cardiac screening.', 15, 10, '#14B8A6', 'fa-heartbeat', 40.00, 'Diagnostic Services', True),
            
            # Pharmacy - not bookable online
            ('Pharmacy', 'Fully stocked pharmacy for your prescriptions and health needs. Contact: +263 78 025 0400', 15, 5, '#14B8A6', 'fa-prescription-bottle-alt', 0.00, 'Pharmacy', False),
        ]

        services = {}
        for name, desc, duration, buffer, color, icon, price, cat_name, bookable in service_data:
            cat = categories.get(cat_name)
            svc = Service.query.filter_by(name=name).first()
            if not svc:
                svc = Service(
                    name=name, description=desc, duration=duration, buffer_time=buffer,
                    color=color, icon=icon, price=price, is_active=True,
                    is_online_bookable=bookable,
                    category_id=cat.id if cat else None
                )
                db.session.add(svc)
            services[name] = svc
        db.session.flush()

        print("Seeding practitioners...")
        practitioners_data = [
            ('Knowledge', 'Tsungu', 'knowledge.tsungu@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#10B981', ['General Dentistry', 'Orthodontics', 'Restorative & Aesthetic Dentistry', 'Dental Emergencies']),
            ('Rukudzo', 'Mwamuka', 'rukudzo.mwamuka@venushealthcare.co.zw', 'Psychiatry', 'Dr.', '#8B5CF6', ['Psychiatrist']),
            ('James', 'Wilson', 'james.wilson@venushealthcare.co.zw', 'General Practice', 'Dr.', '#69A83F', ['General Consultation', 'Family Medicine', 'Chronic Disease Management', 'Travel Clinic']),
            ('Emily', 'Chen', 'emily.chen@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#10B981', ['General Dentistry', 'Dental Emergencies']),
            ('Sarah', 'Davis', 'sarah.davis@venushealthcare.co.zw', 'Paediatrics', 'Dr.', '#EC4899', ['Paediatrics', 'Vaccination Clinic']),
            ('Michael', 'Brown', 'michael.brown@venushealthcare.co.zw', 'Physiotherapy', 'Dr.', '#F59E0B', ['Physiotherapy']),
            ('Lisa', 'Anderson', 'lisa.anderson@venushealthcare.co.zw', 'Dermatology', 'Dr.', '#F59E0B', ['Dermatology', 'General Consultation']),
            ('David', 'Kim', 'david.kim@venushealthcare.co.zw', 'Clinical Psychology', 'Dr.', '#8B5CF6', ['Clinical Neuropsychologist', 'Educational Psychologist']),
            ('Amy', 'Taylor', 'amy.taylor@venushealthcare.co.zw', 'Nursing', 'Nurse', '#14B8A6', ['Vaccination Clinic', 'Laboratory Testing', 'ECG', 'Preventative Health Screenings']),
            ('Grace', 'Moyo', 'grace.moyo@venushealthcare.co.zw', 'Diagnostic Imaging', 'Dr.', '#06B6D4', ['Ultrasound', 'Laboratory Testing']),
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
