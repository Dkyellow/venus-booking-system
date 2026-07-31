from flask import jsonify, request
from datetime import datetime, date
from app.api import api_bp
from app.models.service import Service
from app.models.staff import Staff
from app.models.patient import Patient
from app.models.appointment import Appointment, AppointmentStatus, AppointmentHistory
from app.extensions import db
from app.services.scheduling_engine import SchedulingEngine
from app.services.notification_service import NotificationService


@api_bp.route('/services')
def api_services():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order, Service.name).all()
    return jsonify({
        'services': [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'duration': s.duration,
            'buffer_time': s.buffer_time,
            'price': float(s.price) if s.price else 0,
            'color': s.color,
            'icon': s.icon or 'fa-stethoscope',
            'category_id': s.category_id,
            'max_advance_days': s.max_advance_days
        } for s in services]
    })


@api_bp.route('/services/<int:service_id>/practitioners')
def api_service_practitioners(service_id):
    service = Service.query.get_or_404(service_id)
    practitioners = Staff.query.filter(
        Staff.is_active == True,
        Staff.is_practitioner == True,
        Staff.services.any(Service.id == service_id)
    ).all()
    
    if not practitioners:
        practitioners = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    
    return jsonify({
        'practitioners': [{
            'id': p.id,
            'name': p.display_name,
            'specialization': p.specialization,
            'photo_url': p.photo_url,
            'color': p.color,
            'bio': p.bio
        } for p in practitioners]
    })


@api_bp.route('/booking/available-dates')
def api_available_dates():
    service_id = request.args.get('service_id', type=int)
    practitioner_id = request.args.get('practitioner_id', type=int)
    
    if not service_id:
        return jsonify({'error': 'service_id required'}), 400
    
    engine = SchedulingEngine()
    dates = engine.get_available_dates(service_id, practitioner_id)
    return jsonify({'dates': dates})


@api_bp.route('/booking/slots')
def api_available_slots():
    service_id = request.args.get('service_id', type=int)
    practitioner_id = request.args.get('practitioner_id', type=int)
    target_date = request.args.get('date')
    
    if not service_id or not target_date:
        return jsonify({'error': 'service_id and date required'}), 400
    
    try:
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    engine = SchedulingEngine()
    slots = engine.get_available_slots(service_id, target_date, practitioner_id)
    return jsonify({'slots': slots})


@api_bp.route('/booking/create', methods=['POST'])
def api_create_booking():
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    required_fields = ['service_id', 'date', 'start_time', 'end_time', 'first_name', 'last_name', 'email', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'{field} is required'}), 400
    
    service = Service.query.get(data['service_id'])
    if not service:
        return jsonify({'success': False, 'message': 'Service not found'}), 404
    
    try:
        start_dt = datetime.strptime(f"{data['date']} {data['start_time']}", '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(f"{data['date']} {data['end_time']}", '%Y-%m-%d %H:%M')
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date/time format'}), 400
    
    practitioner_id = data.get('practitioner_id')
    if practitioner_id:
        practitioner_id = int(practitioner_id) if str(practitioner_id).isdigit() else None
    
    engine = SchedulingEngine()
    can_book, message = engine.can_book_appointment(data['service_id'], practitioner_id, start_dt, end_dt)
    
    if not can_book:
        return jsonify({'success': False, 'message': message}), 400
    
    patient = Patient.query.filter(
        (Patient.email == data['email'].lower()) | (Patient.phone == data['phone'])
    ).first()
    
    if not patient:
        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'].lower(),
            phone=data['phone'],
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            gender=data.get('gender')
        )
        db.session.add(patient)
        db.session.flush()
    
    reference = engine.create_booking_reference()
    
    appointment = Appointment(
        reference=reference,
        patient_id=patient.id,
        practitioner_id=practitioner_id,
        service_id=data['service_id'],
        date=start_dt.date(),
        start_time=start_dt,
        end_time=end_dt,
        status=AppointmentStatus.CONFIRMED,
        reason=data.get('reason'),
        notes=data.get('notes')
    )
    db.session.add(appointment)
    db.session.commit()
    
    history = AppointmentHistory(
        appointment_id=appointment.id,
        action='created',
        new_value='Booking created via online portal'
    )
    db.session.add(history)
    db.session.commit()
    
    email_sent = False
    email_error = None
    try:
        email_sent = NotificationService.notify_booking_confirmed(appointment)
    except Exception as e:
        email_error = str(e)
        import logging
        logging.error(f"Email notification failed: {e}")
    
    return jsonify({
        'success': True,
        'reference': reference,
        'message': f'Appointment booked successfully! Reference: {reference}',
        'email_sent': email_sent,
        'email_error': email_error
    })


@api_bp.route('/appointments/<int:id>/reschedule', methods=['POST'])
def api_reschedule_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    data = request.get_json()
    
    if 'start_time' in data:
        new_start = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        new_end = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')) if 'end_time' in data else new_start
        
        old_start = appointment.start_time
        appointment.start_time = new_start.replace(tzinfo=None)
        appointment.end_time = new_end.replace(tzinfo=None)
        appointment.date = new_start.date()
        
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid data'}), 400


@api_bp.route('/dashboard/stats')
def api_dashboard_stats():
    from datetime import date, timedelta
    today = date.today()
    
    today_count = Appointment.query.filter(
        Appointment.date == today,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_PROGRESS])
    ).count()
    
    upcoming = Appointment.query.filter(
        Appointment.date > today,
        Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING])
    ).count()
    
    completed = Appointment.query.filter(
        Appointment.date == today,
        Appointment.status == AppointmentStatus.COMPLETED
    ).count()
    
    from app.models.patient import Patient
    total_patients = Patient.query.filter_by(is_active=True).count()
    
    return jsonify({
        'today_count': today_count,
        'upcoming_count': upcoming,
        'completed_count': completed,
        'total_patients': total_patients
    })


@api_bp.route('/appointments')
def api_appointments():
    from flask_login import current_user
    filter_type = request.args.get('filter', 'today')
    today = date.today()
    
    query = Appointment.query
    
    if filter_type == 'today':
        query = query.filter(Appointment.date == today)
    elif filter_type == 'week':
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        query = query.filter(Appointment.date >= week_start, Appointment.date <= week_end)
    elif filter_type == 'month':
        query = query.filter(Appointment.date >= today.replace(day=1))
    
    appointments = query.order_by(Appointment.start_time).limit(50).all()
    
    return jsonify({
        'appointments': [{
            'id': a.id,
            'reference': a.reference,
            'patient_name': a.patient.full_name,
            'service_name': a.service.name,
            'practitioner_name': a.practitioner.full_name if a.practitioner else 'N/A',
            'date': a.date.isoformat(),
            'time': a.start_time.strftime('%I:%M %p'),
            'status': a.status.value,
            'status_color': a.status_color
        } for a in appointments]
    })


@api_bp.route('/calendar/events')
def api_calendar_events():
    from flask import request as req
    start = req.args.get('start')
    end = req.args.get('end')

    query = Appointment.query

    if start:
        try:
            start_date = datetime.fromisoformat(start.replace('Z', '')).date()
            query = query.filter(Appointment.date >= start_date)
        except: pass
    if end:
        try:
            end_date = datetime.fromisoformat(end.replace('Z', '')).date()
            query = query.filter(Appointment.date <= end_date)
        except: pass

    appointments = query.order_by(Appointment.start_time).all()

    status_colors = {
        AppointmentStatus.PENDING: '#F59E0B',
        AppointmentStatus.CONFIRMED: '#4F46E5',
        AppointmentStatus.CHECKED_IN: '#3B82F6',
        AppointmentStatus.IN_PROGRESS: '#06B6D4',
        AppointmentStatus.COMPLETED: '#10B981',
        AppointmentStatus.CANCELLED: '#EF4444',
        AppointmentStatus.NO_SHOW: '#6B7280',
        AppointmentStatus.RESCHEDULED: '#F59E0B',
    }

    events = []
    for apt in appointments:
        color = status_colors.get(apt.status, apt.service.color if apt.service else '#4F46E5')
        practitioner = apt.practitioner.full_name if apt.practitioner else 'Any Available'
        events.append({
            'id': str(apt.id),
            'title': f"{apt.service.name} - {apt.patient.full_name}",
            'start': apt.start_time.isoformat(),
            'end': apt.end_time.isoformat(),
            'color': color,
            'borderColor': color,
            'textColor': '#FFFFFF',
            'extendedProps': {
                'reference': apt.reference,
                'patient': apt.patient.full_name,
                'service': apt.service.name,
                'practitioner': practitioner,
                'status': apt.status.value,
                'statusColor': apt.status_color,
                'notes': apt.notes or ''
            }
        })

    return jsonify({'events': events})
