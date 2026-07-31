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
            svc = Service.query.filter_by(name=name).first()
            if not svc:
                svc = Service(name=name, description=desc, duration=duration, buffer_time=buffer, color=color, icon=icon, price=price, is_active=True, is_online_bookable=True)
                db.session.add(svc)
            services[name] = svc
        db.session.flush()

        print("Seeding practitioners...")
        practitioners_data = [
            ('Dr. James', 'Wilson', 'james.wilson@venushealthcare.co.zw', 'General Practice', 'Dr.', '#69A83F', ['General Consultation', 'Vaccination']),
            ('Dr. Emily', 'Chen', 'emily.chen@venushealthcare.co.zw', 'Dentistry', 'Dr.', '#10B981', ['Dental Checkup']),
            ('Dr. Michael', 'Brown', 'michael.brown@venushealthcare.co.zw', 'Physiotherapy', 'Dr.', '#F59E0B', ['Physiotherapy']),
            ('Dr. Sarah', 'Davis', 'sarah.davis@venushealthcare.co.zw', 'Radiology', 'Dr.', '#06B6D4', ['Ultrasound']),
            ('Dr. David', 'Kim', 'david.kim@venushealthcare.co.zw', 'Ophthalmology', 'Dr.', '#8B5CF6', ['Eye Examination']),
            ('Dr. Lisa', 'Anderson', 'lisa.anderson@venushealthcare.co.zw', 'ENT', 'Dr.', '#EC4899', ['ENT Consultation']),
            ('Nurse Amy', 'Taylor', 'amy.taylor@venushealthcare.co.zw', 'Laboratory', 'Nurse', '#14B8A6', ['Laboratory Tests', 'Vaccination']),
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
                for day in range(5):
                    sched = StaffSchedule(staff_id=s.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0), is_active=True)
                    db.session.add(sched)
            staff_list[email] = s
        db.session.flush()

        print("Seeding clinic settings...")
        settings = ClinicSettings.query.first()
        if not settings:
            settings = ClinicSettings(
                clinic_name='Venus Healthcare',
                clinic_email='medical@venushealthcare.co.zw',
                clinic_phone='+263 (0242) 339 769',
                clinic_address='',
                clinic_website=''
            )
            db.session.add(settings)

        db.session.commit()
        print("\n=== Seed Complete ===")
        print("Admin: admin@venushealthcare.co.zw / admin123")
        print("Receptionist: reception@venushealthcare.co.zw / reception123")
        print(f"Services: {len(services)}")
        print(f"Practitioners: {len(staff_list)}")


if __name__ == '__main__':
    seed_database()
