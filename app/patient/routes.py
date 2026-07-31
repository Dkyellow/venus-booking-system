from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date, timedelta
from app.patient import patient_bp
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus
from app.models.service import Service
from app.extensions import db
from app.utils.decorators import patient_required


@patient_bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    today = date.today()
    
    upcoming = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date >= today,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING, AppointmentStatus.CHECKED_IN])
    ).order_by(Appointment.date, Appointment.start_time).limit(10).all()
    
    past = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.date < today
    ).order_by(Appointment.date.desc(), Appointment.start_time.desc()).limit(10).all()
    
    total_appointments = Appointment.query.filter_by(patient_id=patient.id).count()
    completed = Appointment.query.filter_by(patient_id=patient.id, status=AppointmentStatus.COMPLETED).count()
    cancelled = Appointment.query.filter_by(patient_id=patient.id, status=AppointmentStatus.CANCELLED).count()
    
    return render_template('patient/dashboard.html',
                          patient=patient,
                          upcoming=upcoming,
                          past=past,
                          total_appointments=total_appointments,
                          completed=completed,
                          cancelled=cancelled)


@patient_bp.route('/appointments')
@login_required
@patient_required
def appointments():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    
    query = Appointment.query.filter_by(patient_id=patient.id)
    
    if status_filter:
        query = query.filter(Appointment.status == AppointmentStatus(status_filter))
    
    pagination = query.order_by(Appointment.date.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('patient/appointments.html',
                          appointments=pagination.items,
                          pagination=pagination,
                          selected_status=status_filter)


@patient_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    patient = Patient.query.filter_by(user_id=current_user.id).first()
    if not patient:
        flash('Patient profile not found.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        patient.first_name = request.form.get('first_name', patient.first_name)
        patient.last_name = request.form.get('last_name', patient.last_name)
        patient.phone = request.form.get('phone', patient.phone)
        patient.address = request.form.get('address', patient.address)
        patient.emergency_contact_name = request.form.get('emergency_contact_name', '')
        patient.emergency_contact_phone = request.form.get('emergency_contact_phone', '')
        
        current_user.first_name = patient.first_name
        current_user.last_name = patient.last_name
        current_user.phone = patient.phone
        
        dob = request.form.get('date_of_birth')
        if dob:
            from datetime import datetime
            patient.date_of_birth = datetime.strptime(dob, '%Y-%m-%d').date()
        
        gender = request.form.get('gender')
        if gender:
            patient.gender = gender
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient.profile'))
    
    return render_template('patient/profile.html', patient=patient)
