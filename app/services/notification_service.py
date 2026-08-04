from datetime import datetime, timedelta
from app.extensions import db
from app.models.notification import Notification
from app.models.appointment import Appointment, AppointmentStatus
from app.services.email_service import EmailService
from app.services.whatsapp_service import WhatsAppService


class NotificationService:
    
    @staticmethod
    def create_notification(notification_type, category, message, patient_id=None, 
                          appointment_id=None, user_id=None, subject=None):
        notification = Notification(
            type=notification_type,
            category=category,
            subject=subject,
            message=message,
            patient_id=patient_id,
            appointment_id=appointment_id,
            user_id=user_id,
            status='pending'
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def notify_booking_confirmed(appointment):
        print(f"[NOTIFY] Sending confirmation for {appointment.reference} to {appointment.patient.email}")
        try:
            result = EmailService.send_booking_confirmation(appointment)
            print(f"[NOTIFY] Email result: {result}")
        except Exception as e:
            print(f"[NOTIFY] Email error: {e}")
        
        if appointment.patient.phone:
            try:
                msg = WhatsAppService.booking_confirmation_message(appointment)
                WhatsAppService.send_message(
                    appointment.patient.phone, msg, appointment.id
                )
            except Exception as e:
                print(f"[NOTIFY] WhatsApp error (ignored): {e}")
        
        NotificationService.create_notification(
            'system', 'confirmation',
            f"Appointment {appointment.reference} confirmed",
            patient_id=appointment.patient_id,
            appointment_id=appointment.id
        )
    
    @staticmethod
    def notify_booking_received(appointment):
        print(f"[NOTIFY] Sending booking received for {appointment.reference} to {appointment.patient.email}")
        try:
            result = EmailService.send_booking_received(appointment)
            print(f"[NOTIFY] Email result: {result}")
        except Exception as e:
            print(f"[NOTIFY] Email error: {e}")
        
        NotificationService.create_notification(
            'system', 'booking_received',
            f"Booking {appointment.reference} received, pending confirmation",
            patient_id=appointment.patient_id,
            appointment_id=appointment.id
        )
    
    @staticmethod
    def notify_booking_reminder(appointment, hours_before=24):
        EmailService.send_reminder(appointment, hours_before)
        
        if appointment.patient.phone:
            msg = WhatsAppService.reminder_message(appointment, hours_before)
            WhatsAppService.send_message(
                appointment.patient.phone, msg, appointment.id
            )
        
        NotificationService.create_notification(
            'email', 'reminder',
            f"Reminder sent for appointment {appointment.reference} ({hours_before}h)",
            patient_id=appointment.patient_id,
            appointment_id=appointment.id
        )
    
    @staticmethod
    def notify_booking_rescheduled(appointment, old_date, old_time):
        EmailService.send_rescheduled(appointment, old_date, old_time)
        
        if appointment.patient.phone:
            msg = WhatsAppService.rescheduled_message(appointment)
            WhatsAppService.send_message(
                appointment.patient.phone, msg, appointment.id
            )
        
        NotificationService.create_notification(
            'email', 'rescheduled',
            f"Appointment {appointment.reference} rescheduled",
            patient_id=appointment.patient_id,
            appointment_id=appointment.id
        )
    
    @staticmethod
    def notify_booking_cancelled(appointment, reason=None):
        EmailService.send_cancellation(appointment, reason)
        
        if appointment.patient.phone:
            msg = WhatsAppService.cancellation_message(appointment, reason)
            WhatsAppService.send_message(
                appointment.patient.phone, msg, appointment.id
            )
        
        NotificationService.create_notification(
            'email', 'cancelled',
            f"Appointment {appointment.reference} cancelled",
            patient_id=appointment.patient_id,
            appointment_id=appointment.id
        )
    
    @staticmethod
    def send_pending_reminders():
        now = datetime.utcnow()
        
        reminder_configs = [
            (48, 'reminder_sent_48h'),
            (24, 'reminder_sent_24h'),
            (2, 'reminder_sent_2h'),
        ]
        
        for hours, field in reminder_configs:
            target_time = now + timedelta(hours=hours)
            
            appointments = Appointment.query.filter(
                Appointment.start_time <= target_time,
                Appointment.start_time > now,
                Appointment.status.in_([
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.CHECKED_IN
                ]),
                getattr(Appointment, field) == False
            ).all()
            
            for apt in appointments:
                NotificationService.notify_booking_reminder(apt, hours)
                setattr(apt, field, True)
                db.session.commit()
