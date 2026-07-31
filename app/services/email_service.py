from flask import render_template, current_app
from app.extensions import db
from app.models.notification import EmailLog
from app.models.appointment import Appointment
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class EmailService:
    
    @staticmethod
    def send_email(to, subject, html_body, template_name=None, appointment_id=None):
        try:
            mailjet_key = os.getenv('MAILJET_API_KEY')
            mailjet_secret = os.getenv('MAILJET_SECRET_KEY')
            
            if mailjet_key and mailjet_secret:
                import requests
                import base64
                
                sender_email = os.getenv('MAIL_DEFAULT_SENDER_EMAIL', 'lesliesarai321@gmail.com')
                sender_name = 'Venus Healthcare'
                
                to_email = to if isinstance(to, list) else [to]
                
                import re
                text_body = re.sub(r'<[^>]+>', ' ', html_body)
                text_body = re.sub(r'\s+', ' ', text_body).strip()
                
                data = {
                    'FromEmail': sender_email,
                    'FromName': sender_name,
                    'Subject': subject,
                    'TextPart': text_body,
                    'HtmlPart': html_body,
                    'Recipients': [{'Email': e} for e in to_email]
                }
                
                logo_path = os.path.join(current_app.static_folder, 'logo.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo_data = base64.b64encode(f.read()).decode()
                    data['Attachments'] = [{
                        'ContentType': 'image/png',
                        'Filename': 'logo.png',
                        'Base64Content': logo_data
                    }]
                
                import json
                safe_data = {k: v for k, v in data.items() if k != 'Attachments'}
                print(f"[EMAIL DEBUG] Mailjet payload: {json.dumps(safe_data, indent=2)}")
                print(f"[EMAIL DEBUG] Mailjet key prefix: {mailjet_key[:8]}...")
                
                result = requests.post(
                    'https://api.mailjet.com/v3.1/send',
                    auth=(mailjet_key, mailjet_secret),
                    json=data
                )
                if result.status_code >= 400:
                    print(f"[EMAIL FAILED] Mailjet error: {result.status_code} | {result.text}")
                    raise Exception(f"Mailjet error {result.status_code}: {result.text}")
                print(f"[EMAIL SENT] To: {to} | Subject: {subject} | Status: {result.status_code}")
            elif os.getenv('SENDGRID_API_KEY'):
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId
                import base64
                
                message = Mail(
                    from_email=current_app.config.get('MAIL_DEFAULT_SENDER', 'Venus Healthcare <lesliesarai321@gmail.com>'),
                    to_emails=to if isinstance(to, list) else [to],
                    subject=subject,
                    html_content=html_body
                )
                
                logo_path = os.path.join(current_app.static_folder, 'logo.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo_data = base64.b64encode(f.read()).decode()
                    attachment = Attachment(
                        FileContent(logo_data),
                        FileName('logo.png'),
                        FileType('image/png'),
                        Disposition('inline'),
                        ContentId('logo')
                    )
                    message.attachment = attachment
                
                sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
                sg.send(message)
                print(f"[EMAIL SENT via SendGrid] To: {to} | Subject: {subject}")
            else:
                print(f"[EMAIL SKIPPED] No email API key set. To: {to} | Subject: {subject}")
                return False
            
            log = EmailLog(
                recipient=to if isinstance(to, str) else to[0],
                subject=subject,
                body=html_body,
                template=template_name,
                status='sent',
                appointment_id=appointment_id,
                sent_at=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            print(f"[EMAIL FAILED] To: {to} | Subject: {subject} | Error: {e}")
            log = EmailLog(
                recipient=to if isinstance(to, str) else to[0],
                subject=subject,
                body=html_body,
                template=template_name,
                status='failed',
                error_message=str(e),
                appointment_id=appointment_id
            )
            db.session.add(log)
            db.session.commit()
            return False
    
    @staticmethod
    def send_booking_confirmation(appointment):
        try:
            html = render_template(
                'emails/confirmation.html',
                appointment=appointment,
                patient=appointment.patient,
                practitioner=appointment.practitioner,
                service=appointment.service
            )
            return EmailService.send_email(
                to=appointment.patient.email,
                subject=f"Booking Confirmed - {appointment.reference}",
                html_body=html,
                template_name='confirmation',
                appointment_id=appointment.id
            )
        except Exception as e:
            logger.error(f"Confirmation email failed: {str(e)}")
            return False
    
    @staticmethod
    def send_reminder(appointment, hours_before=24):
        try:
            html = render_template(
                'emails/reminder.html',
                appointment=appointment,
                patient=appointment.patient,
                practitioner=appointment.practitioner,
                service=appointment.service,
                hours_before=hours_before
            )
            return EmailService.send_email(
                to=appointment.patient.email,
                subject=f"Appointment Reminder - {hours_before}h away",
                html_body=html,
                template_name='reminder',
                appointment_id=appointment.id
            )
        except Exception as e:
            logger.error(f"Reminder email failed: {str(e)}")
            return False
    
    @staticmethod
    def send_rescheduled(appointment, old_date, old_time):
        try:
            html = render_template(
                'emails/rescheduled.html',
                appointment=appointment,
                patient=appointment.patient,
                practitioner=appointment.practitioner,
                service=appointment.service,
                old_date=old_date,
                old_time=old_time
            )
            return EmailService.send_email(
                to=appointment.patient.email,
                subject=f"Appointment Rescheduled - {appointment.reference}",
                html_body=html,
                template_name='rescheduled',
                appointment_id=appointment.id
            )
        except Exception as e:
            logger.error(f"Reschedule email failed: {str(e)}")
            return False
    
    @staticmethod
    def send_cancellation(appointment, reason=None):
        try:
            html = render_template(
                'emails/cancelled.html',
                appointment=appointment,
                patient=appointment.patient,
                practitioner=appointment.practitioner,
                service=appointment.service,
                reason=reason
            )
            return EmailService.send_email(
                to=appointment.patient.email,
                subject=f"Appointment Cancelled - {appointment.reference}",
                html_body=html,
                template_name='cancelled',
                appointment_id=appointment.id
            )
        except Exception as e:
            logger.error(f"Cancellation email failed: {str(e)}")
            return False
