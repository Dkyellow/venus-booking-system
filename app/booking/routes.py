from flask import render_template, redirect, url_for, flash, request, jsonify
from datetime import datetime, date, timedelta
from app.booking import booking_bp
from app.booking.forms import PublicBookingForm, ManageBookingForm
from app.models.service import Service, ServiceCategory
from app.models.staff import Staff
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus, AppointmentHistory
from app.extensions import db
from app.services.scheduling_engine import SchedulingEngine
from app.services.notification_service import NotificationService
from app.services.google_calendar_service import GoogleCalendarService


@booking_bp.route('/')
def book():
    services = Service.query.filter_by(is_active=True, is_online_bookable=True).order_by(Service.sort_order, Service.name).all()
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.sort_order).all()
    practitioners = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    form = PublicBookingForm()
    return render_template('booking/book.html', form=form, services=services, categories=categories, practitioners=practitioners)


@booking_bp.route('/confirmation/<reference>')
def confirmation(reference):
    appointment = Appointment.query.filter_by(reference=reference).first_or_404()
    add_to_cal_url = GoogleCalendarService.generate_add_to_calendar_url(appointment)
    ics_content = GoogleCalendarService.get_ics_content(appointment)
    return render_template('booking/confirmation.html', appointment=appointment, add_to_cal_url=add_to_cal_url, ics_content=ics_content)


@booking_bp.route('/manage', methods=['GET', 'POST'])
def manage():
    form = ManageBookingForm()
    appointment = None
    
    if form.validate_on_submit():
        appointment = Appointment.query.filter_by(
            reference=form.reference.data.upper()
        ).first()
        
        if not appointment:
            flash('Booking not found. Please check your reference number.', 'danger')
        elif appointment.patient.email.lower() != form.email.data.lower():
            flash('Email does not match our records.', 'danger')
            appointment = None
        else:
            return redirect(url_for('booking.manage_detail', reference=appointment.reference))
    
    return render_template('booking/manage.html', form=form, appointment=appointment)


@booking_bp.route('/manage/<reference>')
def manage_detail(reference):
    appointment = Appointment.query.filter_by(reference=reference).first_or_404()
    add_to_cal_url = GoogleCalendarService.generate_add_to_calendar_url(appointment)
    return render_template('booking/manage_detail.html', appointment=appointment, add_to_cal_url=add_to_cal_url)


@booking_bp.route('/manage/<reference>/cancel', methods=['POST'])
def cancel_appointment(reference):
    appointment = Appointment.query.filter_by(reference=reference).first_or_404()
    
    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        flash('This appointment cannot be cancelled.', 'danger')
        return redirect(url_for('booking.manage_detail', reference=reference))
    
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.utcnow()
    appointment.cancellation_reason = request.form.get('reason', 'Cancelled by patient')
    
    history = AppointmentHistory(
        appointment_id=appointment.id,
        action='cancelled',
        old_value=appointment.status.value,
        new_value='Cancelled',
        notes=request.form.get('reason', ''),
    )
    db.session.add(history)
    db.session.commit()
    
    NotificationService.notify_booking_cancelled(appointment, request.form.get('reason'))
    
    flash('Your appointment has been cancelled.', 'info')
    return redirect(url_for('booking.manage', reference=reference))


@booking_bp.route('/manage/<reference>/reschedule', methods=['POST'])
def reschedule_appointment(reference):
    appointment = Appointment.query.filter_by(reference=reference).first_or_404()
    
    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        flash('This appointment cannot be rescheduled.', 'danger')
        return redirect(url_for('booking.manage_detail', reference=reference))
    
    new_date = request.form.get('date')
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')
    
    if not new_date or not new_start or not new_end:
        flash('Please provide date, start time, and end time.', 'danger')
        return redirect(url_for('booking.manage_detail', reference=reference))
    
    old_date = appointment.date
    old_time = appointment.start_time
    
    appointment.date = datetime.strptime(new_date, '%Y-%m-%d').date()
    appointment.start_time = datetime.strptime(f"{new_date} {new_start}", '%Y-%m-%d %H:%M')
    appointment.end_time = datetime.strptime(f"{new_date} {new_end}", '%Y-%m-%d %H:%M')
    appointment.status = AppointmentStatus.RESCHEDULED
    
    history = AppointmentHistory(
        appointment_id=appointment.id,
        action='reschedule_requested',
        old_value=f'{old_date.strftime("%Y-%m-%d")} {old_time.strftime("%H:%M")}',
        new_value=f'{new_date} {new_start}',
    )
    db.session.add(history)
    db.session.commit()
    
    flash('Reschedule request submitted. You will receive an email once confirmed by our team.', 'info')
    return redirect(url_for('booking.manage_detail', reference=reference))
