import requests
import logging
from flask import current_app
from app.models.notification import WhatsAppLog
from app.extensions import db
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppService:
    
    @staticmethod
    def send_message(phone, message, appointment_id=None):
        api_url = current_app.config.get('WHATSAPP_API_URL')
        api_token = current_app.config.get('WHATSAPP_API_TOKEN')
        
        if not api_url or not api_token:
            logger.warning("WhatsApp API not configured")
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            payload = {
                'messaging_product': 'whatsapp',
                'to': phone,
                'type': 'text',
                'text': {'body': message}
            }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                log = WhatsAppLog(
                    recipient=phone,
                    message=message,
                    status='sent',
                    appointment_id=appointment_id,
                    sent_at=datetime.utcnow()
                )
                db.session.add(log)
                db.session.commit()
                return True
            else:
                logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
                log = WhatsAppLog(
                    recipient=phone,
                    message=message,
                    status='failed',
                    error_message=response.text,
                    appointment_id=appointment_id
                )
                db.session.add(log)
                db.session.commit()
                return False
        except Exception as e:
            logger.error(f"WhatsApp send failed: {str(e)}")
            log = WhatsAppLog(
                recipient=phone,
                message=message,
                status='failed',
                error_message=str(e),
                appointment_id=appointment_id
            )
            db.session.add(log)
            db.session.commit()
            return False
    
    @staticmethod
    def booking_confirmation_message(appointment):
        patient_name = appointment.patient.full_name
        service_name = appointment.service.name
        date_str = appointment.date.strftime('%B %d, %Y')
        time_str = appointment.start_time.strftime('%I:%M %p')
        reference = appointment.reference
        practitioner_name = appointment.practitioner.full_name if appointment.practitioner else "Any Available"
        
        return (
            f"🏥 *Venus Medical Clinic*\n\n"
            f"Hi {patient_name}, your appointment has been confirmed!\n\n"
            f"📋 *Booking Details*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 Reference: {reference}\n"
            f"🩺 Service: {service_name}\n"
            f"👨‍⚕️ Practitioner: {practitioner_name}\n"
            f"📅 Date: {date_str}\n"
            f"🕐 Time: {time_str}\n"
            f"⏱️ Duration: {appointment.service.duration} minutes\n\n"
            f"Please arrive 10 minutes before your appointment.\n\n"
            f"📞 Contact: {current_app.config.get('CLINIC_PHONE', '+1 (555) 123-4567')}\n"
            f"📍 Address: {current_app.config.get('CLINIC_ADDRESS', '123 Medical Drive')}\n\n"
            f"To manage your booking, visit our website."
        )
    
    @staticmethod
    def reminder_message(appointment, hours_before=24):
        patient_name = appointment.patient.full_name
        service_name = appointment.service.name
        date_str = appointment.date.strftime('%B %d, %Y')
        time_str = appointment.start_time.strftime('%I:%M %p')
        
        return (
            f"🏥 *Venus Medical Clinic*\n\n"
            f"Hi {patient_name}, this is a friendly reminder!\n\n"
            f"⏰ Your appointment is in {hours_before} hours\n\n"
            f"📋 *Details*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 Reference: {appointment.reference}\n"
            f"🩺 Service: {service_name}\n"
            f"📅 Date: {date_str}\n"
            f"🕐 Time: {time_str}\n"
            f"📍 Location: {current_app.config.get('CLINIC_ADDRESS', '123 Medical Drive')}\n\n"
            f"Please arrive 10 minutes early. If you need to reschedule, contact us at {current_app.config.get('CLINIC_PHONE', '+1 (555) 123-4567')}"
        )
    
    @staticmethod
    def rescheduled_message(appointment):
        patient_name = appointment.patient.full_name
        date_str = appointment.date.strftime('%B %d, %Y')
        time_str = appointment.start_time.strftime('%I:%M %p')
        
        return (
            f"🏥 *Venus Medical Clinic*\n\n"
            f"Hi {patient_name}, your appointment has been rescheduled.\n\n"
            f"📋 *New Details*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 Reference: {appointment.reference}\n"
            f"📅 New Date: {date_str}\n"
            f"🕐 New Time: {time_str}\n"
            f"🩺 Service: {appointment.service.name}\n\n"
            f"Contact us at {current_app.config.get('CLINIC_PHONE', '+1 (555) 123-4567')} if you need further changes."
        )
    
    @staticmethod
    def cancellation_message(appointment, reason=None):
        patient_name = appointment.patient.full_name
        date_str = appointment.date.strftime('%B %d, %Y')
        
        msg = (
            f"🏥 *Venus Medical Clinic*\n\n"
            f"Hi {patient_name}, your appointment has been cancelled.\n\n"
            f"📋 *Cancelled Details*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🔖 Reference: {appointment.reference}\n"
            f"📅 Date: {date_str}\n"
            f"🩺 Service: {appointment.service.name}\n"
        )
        
        if reason:
            msg += f"\n📝 Reason: {reason}\n"
        
        msg += (
            f"\nTo rebook, visit our website or call {current_app.config.get('CLINIC_PHONE', '+1 (555) 123-4567')}"
        )
        
        return msg
