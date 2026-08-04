from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from app.admin import admin_bp
from app.admin.forms import (ServiceForm, StaffForm, ScheduleForm, BlockedTimeForm,
                              HolidayForm, SettingsForm, AppointmentForm, PatientForm)
from app.models.user import User, Role
from app.models.patient import Patient
from app.models.staff import Staff
from app.models.service import Service, ServiceCategory
from app.models.appointment import Appointment, AppointmentStatus, AppointmentHistory
from app.models.schedule import StaffSchedule, BlockedTime, Holiday, StaffLeave
from app.models.room import Room, AppointmentRoom
from app.models.notification import Notification, EmailLog, WhatsAppLog
from app.models.settings import ClinicSettings
from app.models.audit import AuditLog
from app.extensions import db
from app.utils.decorators import admin_required, receptionist_or_admin
from app.services.scheduling_engine import SchedulingEngine
from app.services.notification_service import NotificationService
from app.services.google_calendar_service import GoogleCalendarService


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    today_count = Appointment.query.filter(
        Appointment.date == today,
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_PROGRESS])
    ).count()

    upcoming_count = Appointment.query.filter(
        Appointment.date > today,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING])
    ).count()

    completed_count = Appointment.query.filter(
        Appointment.date == today,
        Appointment.status == AppointmentStatus.COMPLETED
    ).count()

    cancelled_count = Appointment.query.filter(
        Appointment.date >= month_start,
        Appointment.status == AppointmentStatus.CANCELLED
    ).count()

    no_show_count = Appointment.query.filter(
        Appointment.date >= month_start,
        Appointment.status == AppointmentStatus.NO_SHOW
    ).count()

    total_patients = Patient.query.filter_by(is_active=True).count()

    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(10).all()

    recent_notifications = Notification.query.order_by(Notification.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                          today_count=today_count,
                          upcoming_count=upcoming_count,
                          completed_count=completed_count,
                          cancelled_count=cancelled_count,
                          no_show_count=no_show_count,
                          total_patients=total_patients,
                          recent_appointments=recent_appointments,
                          recent_notifications=recent_notifications,
                          today=today)


@admin_bp.route('/calendar')
@login_required
def calendar():
    return render_template('admin/calendar.html')


@admin_bp.route('/appointments')
@login_required
def appointments():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    practitioner_filter = request.args.get('practitioner', '', type=str)
    service_filter = request.args.get('service', '', type=str)
    date_filter = request.args.get('date_filter', '')
    search = request.args.get('search', '')

    query = Appointment.query

    if status_filter:
        query = query.filter(Appointment.status == AppointmentStatus(status_filter))

    if practitioner_filter:
        query = query.filter(Appointment.practitioner_id == int(practitioner_filter))

    if service_filter:
        query = query.filter(Appointment.service_id == int(service_filter))

    if date_filter == 'today':
        query = query.filter(Appointment.date == date.today())
    elif date_filter == 'tomorrow':
        query = query.filter(Appointment.date == date.today() + timedelta(days=1))
    elif date_filter == 'week':
        week_start = date.today() - timedelta(days=date.today().weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(Appointment.date >= week_start, Appointment.date <= week_end)
    elif date_filter == 'month':
        query = query.filter(Appointment.date >= date.today().replace(day=1))

    if search:
        query = query.join(Patient).outerjoin(Staff).outerjoin(Service).filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%')) |
            (Patient.email.ilike(f'%{search}%')) |
            (Patient.phone.ilike(f'%{search}%')) |
            (Appointment.reference.ilike(f'%{search}%')) |
            (Staff.first_name.ilike(f'%{search}%')) |
            (Staff.last_name.ilike(f'%{search}%')) |
            (Service.name.ilike(f'%{search}%'))
        )

    query = query.order_by(Appointment.date.desc(), Appointment.start_time.desc())
    pagination = query.paginate(page=page, per_page=20, error_out=False)

    practitioners = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    services = Service.query.filter_by(is_active=True).all()

    return render_template('admin/appointments.html',
                          appointments=pagination.items,
                          pagination=pagination,
                          practitioners=practitioners,
                          services=services,
                          selected_status=status_filter,
                          selected_practitioner=practitioner_filter,
                          selected_service=service_filter,
                          selected_date_filter=date_filter,
                          search=search)


@admin_bp.route('/appointments/new', methods=['GET', 'POST'])
@login_required
def new_appointment():
    form = AppointmentForm()
    form.patient_id.choices = [(p.id, p.full_name) for p in Patient.query.filter_by(is_active=True).all()]
    form.practitioner_id.choices = [(0, 'Any Available')] + [(s.id, s.full_name) for s in Staff.query.filter_by(is_active=True, is_practitioner=True).all()]
    form.service_id.choices = [(s.id, s.name) for s in Service.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        practitioner_id = form.practitioner_id.data if form.practitioner_id.data else None
        start_dt = datetime.strptime(f"{form.date.data} {form.start_time.data}", '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(f"{form.date.data} {form.end_time.data}", '%Y-%m-%d %H:%M')

        engine = SchedulingEngine()
        can_book, message = engine.can_book_appointment(
            form.service_id.data, practitioner_id, start_dt, end_dt
        )

        if not can_book:
            flash(message, 'danger')
            return render_template('admin/new_appointment.html', form=form)

        reference = engine.create_booking_reference()
        appointment = Appointment(
            reference=reference,
            patient_id=form.patient_id.data,
            practitioner_id=practitioner_id if practitioner_id else None,
            service_id=form.service_id.data,
            date=form.date.data,
            start_time=start_dt,
            end_time=end_dt,
            status=AppointmentStatus.CONFIRMED,
            reason=form.reason.data,
            notes=form.notes.data,
            internal_notes=form.internal_notes.data,
            created_by=current_user.id
        )
        db.session.add(appointment)
        db.session.commit()

        history = AppointmentHistory(
            appointment_id=appointment.id,
            action='created',
            new_value=f'Appointment created by {current_user.full_name}',
            changed_by=current_user.id
        )
        db.session.add(history)
        db.session.commit()

        NotificationService.notify_booking_confirmed(appointment)

        flash(f'Appointment {reference} created successfully!', 'success')
        return redirect(url_for('admin.appointment_detail', id=appointment.id))

    preselected_date = request.args.get('date', '')
    return render_template('admin/new_appointment.html', form=form, preselected_date=preselected_date)


@admin_bp.route('/appointments/<int:id>')
@login_required
def appointment_detail(id):
    appointment = Appointment.query.get_or_404(id)
    history = AppointmentHistory.query.filter_by(appointment_id=id).order_by(AppointmentHistory.created_at.desc()).all()
    return render_template('admin/appointment_detail.html', appointment=appointment, history=history)


@admin_bp.route('/appointments/<int:id>/update', methods=['POST'])
@login_required
def update_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    action = request.form.get('action')

    if action == 'status':
        new_status = request.form.get('status')
        old_status = appointment.status.value
        appointment.status = AppointmentStatus(new_status)

        if new_status == 'Completed':
            appointment.completed_at = datetime.utcnow()
        elif new_status == 'Cancelled':
            appointment.cancelled_at = datetime.utcnow()
            appointment.cancellation_reason = request.form.get('reason', '')
        elif new_status == 'Checked In':
            appointment.checked_in_at = datetime.utcnow()

        history = AppointmentHistory(
            appointment_id=appointment.id,
            action='status_changed',
            old_value=old_status,
            new_value=new_status,
            changed_by=current_user.id
        )
        db.session.add(history)
        db.session.commit()

        if new_status == 'Cancelled':
            NotificationService.notify_booking_cancelled(appointment, appointment.cancellation_reason)
        elif new_status == 'Confirmed':
            NotificationService.notify_booking_confirmed(appointment)

        flash(f'Appointment status updated to {new_status}', 'success')

    elif action == 'notes':
        appointment.notes = request.form.get('notes', '')
        appointment.internal_notes = request.form.get('internal_notes', '')
        db.session.commit()
        flash('Notes updated successfully', 'success')

    return redirect(url_for('admin.appointment_detail', id=id))


@admin_bp.route('/appointments/<int:id>/reschedule', methods=['POST'])
@login_required
def reschedule_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    new_date = request.form.get('date')
    new_start = request.form.get('start_time')
    new_end = request.form.get('end_time')

    old_date = appointment.date
    old_time = appointment.start_time

    appointment.date = datetime.strptime(new_date, '%Y-%m-%d').date()
    appointment.start_time = datetime.strptime(f"{new_date} {new_start}", '%Y-%m-%d %H:%M')
    appointment.end_time = datetime.strptime(f"{new_date} {new_end}", '%Y-%m-%d %H:%M')
    appointment.status = AppointmentStatus.RESCHEDULED

    history = AppointmentHistory(
        appointment_id=appointment.id,
        action='rescheduled',
        old_value=f'{old_date} {old_time}',
        new_value=f'{new_date} {new_start}',
        changed_by=current_user.id
    )
    db.session.add(history)
    db.session.commit()

    NotificationService.notify_booking_rescheduled(appointment, old_date, old_time)

    flash('Appointment rescheduled successfully', 'success')
    return redirect(url_for('admin.appointment_detail', id=id))


@admin_bp.route('/services')
@login_required
def services():
    services_list = Service.query.order_by(Service.sort_order, Service.name).all()
    categories = ServiceCategory.query.order_by(ServiceCategory.sort_order).all()
    return render_template('admin/services.html', services=services_list, categories=categories)


@admin_bp.route('/services/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_service():
    form = ServiceForm()
    form.category_id.choices = [(0, 'None')] + [(c.id, c.name) for c in ServiceCategory.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        service = Service(
            name=form.name.data,
            description=form.description.data,
            duration=form.duration.data,
            buffer_time=form.buffer_time.data or 15,
            category_id=form.category_id.data if form.category_id.data else None,
            price=form.price.data or 0,
            color=form.color.data or '#4F46E5',
            is_active=form.is_active.data,
            is_online_bookable=form.is_online_bookable.data,
            max_advance_days=form.max_advance_days.data or 60,
            min_advance_hours=form.min_advance_hours.data or 2,
            sort_order=form.sort_order.data or 0
        )
        db.session.add(service)
        db.session.commit()
        flash('Service created successfully!', 'success')
        return redirect(url_for('admin.services'))

    return render_template('admin/service_form.html', form=form, title='New Service')


@admin_bp.route('/services/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    form = ServiceForm(obj=service)
    form.category_id.choices = [(0, 'None')] + [(c.id, c.name) for c in ServiceCategory.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        form.populate_obj(service)
        service.category_id = form.category_id.data if form.category_id.data else None
        db.session.commit()
        flash('Service updated successfully!', 'success')
        return redirect(url_for('admin.services'))

    return render_template('admin/service_form.html', form=form, title='Edit Service', service=service)


@admin_bp.route('/services/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    service.is_active = False
    db.session.commit()
    flash('Service deactivated successfully.', 'success')
    return redirect(url_for('admin.services'))


@admin_bp.route('/practitioners')
@login_required
def practitioners():
    staff_list = Staff.query.order_by(Staff.last_name).all()
    return render_template('admin/practitioners.html', staff=staff_list)


@admin_bp.route('/practitioners/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_practitioner():
    form = StaffForm()
    if form.validate_on_submit():
        practitioner = Staff(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            phone=form.phone.data,
            specialization=form.specialization.data,
            title=form.title.data,
            bio=form.bio.data,
            color=form.color.data or '#4F46E5',
            consultation_fee=form.consultation_fee.data or 0,
            is_active=form.is_active.data,
            is_practitioner=form.is_practitioner.data
        )
        db.session.add(practitioner)
        db.session.commit()

        default_schedule = [
            StaffSchedule(staff_id=practitioner.id, day_of_week=i,
                         start_time=datetime.strptime('09:00', '%H:%M').time(),
                         end_time=datetime.strptime('17:00', '%H:%M').time())
            for i in range(5)
        ]
        db.session.add_all(default_schedule)
        db.session.commit()

        flash('Practitioner created successfully!', 'success')
        return redirect(url_for('admin.practitioners'))

    return render_template('admin/practitioner_form.html', form=form, title='New Practitioner')


@admin_bp.route('/practitioners/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_practitioner(id):
    practitioner = Staff.query.get_or_404(id)
    form = StaffForm(obj=practitioner)

    if form.validate_on_submit():
        form.populate_obj(practitioner)
        db.session.commit()
        flash('Practitioner updated successfully!', 'success')
        return redirect(url_for('admin.practitioners'))

    return render_template('admin/practitioner_form.html', form=form, title='Edit Practitioner', practitioner=practitioner)


@admin_bp.route('/practitioners/<int:id>/schedules', methods=['GET', 'POST'])
@login_required
@admin_required
def practitioner_schedules(id):
    practitioner = Staff.query.get_or_404(id)
    schedules = StaffSchedule.query.filter_by(staff_id=id).order_by(StaffSchedule.day_of_week).all()

    if request.method == 'POST':
        StaffSchedule.query.filter_by(staff_id=id).delete()

        for day in range(7):
            start = request.form.get(f'start_{day}')
            end = request.form.get(f'end_{day}')
            if start and end:
                schedule = StaffSchedule(
                    staff_id=id,
                    day_of_week=day,
                    start_time=datetime.strptime(start, '%H:%M').time(),
                    end_time=datetime.strptime(end, '%H:%M').time(),
                    is_active=True
                )
                db.session.add(schedule)

        db.session.commit()
        flash('Schedule updated successfully!', 'success')
        return redirect(url_for('admin.practitioner_schedules', id=id))

    schedule_map = {s.day_of_week: s for s in schedules}
    return render_template('admin/practitioner_schedules.html',
                          practitioner=practitioner, schedule_map=schedule_map)


@admin_bp.route('/patients')
@login_required
def patients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = Patient.query
    if search:
        query = query.filter(
            (Patient.first_name.ilike(f'%{search}%')) |
            (Patient.last_name.ilike(f'%{search}%')) |
            (Patient.email.ilike(f'%{search}%')) |
            (Patient.phone.ilike(f'%{search}%'))
        )

    pagination = query.order_by(Patient.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/patients.html', patients=pagination.items, pagination=pagination, search=search)


@admin_bp.route('/patients/<int:id>')
@login_required
def patient_detail(id):
    patient = Patient.query.get_or_404(id)
    appointments = Appointment.query.filter_by(patient_id=id).order_by(Appointment.date.desc()).limit(20).all()
    return render_template('admin/patient_detail.html', patient=patient, appointments=appointments)


@admin_bp.route('/reports')
@login_required
def reports():
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    daily_data = []
    for i in range(30):
        d = today - timedelta(days=i)
        count = Appointment.query.filter(Appointment.date == d).count()
        daily_data.append({'date': d.strftime('%b %d'), 'count': count})
    daily_data.reverse()

    monthly_data = []
    for m in range(1, 13):
        count = Appointment.query.filter(
            extract('month', Appointment.date) == m,
            extract('year', Appointment.date) == today.year
        ).count()
        monthly_data.append({'month': datetime(2024, m, 1).strftime('%b'), 'count': count})

    service_stats = db.session.query(
        Service.name, func.count(Appointment.id)
    ).join(Appointment).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(10).all()

    practitioner_stats = db.session.query(
        Staff.first_name, Staff.last_name, func.count(Appointment.id)
    ).join(Appointment).group_by(Staff.id).order_by(func.count(Appointment.id).desc()).limit(10).all()

    total_appointments = Appointment.query.filter(Appointment.date >= month_start).count()
    cancelled = Appointment.query.filter(
        Appointment.date >= month_start,
        Appointment.status == AppointmentStatus.CANCELLED
    ).count()
    cancellation_rate = (cancelled / total_appointments * 100) if total_appointments > 0 else 0

    status_stats = db.session.query(
        Appointment.status, func.count(Appointment.id)
    ).filter(Appointment.date >= month_start).group_by(Appointment.status).all()

    return render_template('admin/reports.html',
                          daily_data=daily_data,
                          monthly_data=monthly_data,
                          service_stats=service_stats,
                          practitioner_stats=practitioner_stats,
                          cancellation_rate=round(cancellation_rate, 1),
                          status_stats=status_stats,
                          total_appointments=total_appointments,
                          month_start=month_start,
                          today=today)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    clinic_settings = ClinicSettings.query.first()
    if not clinic_settings:
        clinic_settings = ClinicSettings()
        db.session.add(clinic_settings)
        db.session.commit()

    form = SettingsForm(obj=clinic_settings)

    if form.validate_on_submit():
        form.populate_obj(clinic_settings)
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    return render_template('admin/settings.html', form=form, clinic_settings=clinic_settings)


@admin_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    type_filter = request.args.get('type', '')

    query = Notification.query
    if type_filter:
        query = query.filter_by(type=type_filter)

    pagination = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/notifications.html', notifications=pagination.items, pagination=pagination, selected_type=type_filter)


@admin_bp.route('/leave')
@login_required
def leave_management():
    practitioners = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    
    status_filter = request.args.get('status', '')
    practitioner_filter = request.args.get('practitioner', '')
    
    query = StaffLeave.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if practitioner_filter:
        query = query.filter_by(staff_id=int(practitioner_filter))
    
    leaves = query.order_by(StaffLeave.created_at.desc()).all()
    
    return render_template('admin/leave.html',
                          leaves=leaves,
                          practitioners=practitioners,
                          selected_status=status_filter,
                          selected_practitioner=practitioner_filter)


@admin_bp.route('/leave/add', methods=['POST'])
@login_required
def add_leave():
    staff_id = request.form.get('staff_id', type=int)
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    leave_type = request.form.get('leave_type', 'Leave')
    reason = request.form.get('reason', '')
    status = request.form.get('status', 'Approved')
    
    if not staff_id or not start_date or not end_date:
        flash('Staff, start date, and end date are required.', 'error')
        return redirect(url_for('admin.leave_management'))
    
    leave = StaffLeave(
        staff_id=staff_id,
        start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
        end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
        leave_type=leave_type,
        reason=reason,
        status=status,
        created_by=current_user.id
    )
    db.session.add(leave)
    db.session.commit()
    flash(f'{leave_type} added successfully for {leave.duration_days} day(s).', 'success')
    return redirect(url_for('admin.leave_management'))


@admin_bp.route('/leave/<int:id>/delete', methods=['POST'])
@login_required
def delete_leave(id):
    leave = StaffLeave.query.get_or_404(id)
    db.session.delete(leave)
    db.session.commit()
    flash('Leave entry deleted.', 'success')
    return redirect(url_for('admin.leave_management'))


@admin_bp.route('/rooms')
@login_required
def rooms_management():
    rooms = Room.query.order_by(Room.name).all()
    return render_template('admin/rooms.html', rooms=rooms)


@admin_bp.route('/rooms/add', methods=['POST'])
@login_required
def add_room():
    name = request.form.get('name')
    description = request.form.get('description', '')
    room_type = request.form.get('room_type', 'Consultation')
    capacity = request.form.get('capacity', 1, type=int)
    floor = request.form.get('floor', '')
    equipment = request.form.get('equipment', '')
    
    if not name:
        flash('Room name is required.', 'error')
        return redirect(url_for('admin.rooms_management'))
    
    room = Room(
        name=name,
        description=description,
        room_type=room_type,
        capacity=capacity,
        floor=floor,
        equipment=equipment
    )
    db.session.add(room)
    db.session.commit()
    flash(f'Room "{name}" added successfully.', 'success')
    return redirect(url_for('admin.rooms_management'))


@admin_bp.route('/rooms/<int:id>/edit', methods=['POST'])
@login_required
def edit_room(id):
    room = Room.query.get_or_404(id)
    room.name = request.form.get('name', room.name)
    room.description = request.form.get('description', room.description)
    room.room_type = request.form.get('room_type', room.room_type)
    room.capacity = request.form.get('capacity', room.capacity, type=int)
    room.floor = request.form.get('floor', room.floor)
    room.equipment = request.form.get('equipment', room.equipment)
    room.is_active = 'is_active' in request.form
    db.session.commit()
    flash(f'Room "{room.name}" updated.', 'success')
    return redirect(url_for('admin.rooms_management'))


@admin_bp.route('/rooms/<int:id>/delete', methods=['POST'])
@login_required
def delete_room(id):
    room = Room.query.get_or_404(id)
    db.session.delete(room)
    db.session.commit()
    flash(f'Room "{room.name}" deleted.', 'success')
    return redirect(url_for('admin.rooms_management'))
