import logging
from datetime import datetime, timedelta
from flask import current_app, url_for
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.models.appointment import Appointment
from app.models.settings import ClinicSettings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    
    @staticmethod
    def get_oauth_flow():
        client_id = current_app.config.get('GOOGLE_CALENDAR_CLIENT_ID')
        client_secret = current_app.config.get('GOOGLE_CALENDAR_CLIENT_SECRET')
        redirect_uri = current_app.config.get('GOOGLE_CALENDAR_REDIRECT_URI')
        
        if not client_id or not client_secret:
            return None
        
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=SCOPES
        )
        return flow
    
    @staticmethod
    def get_authorization_url():
        flow = GoogleCalendarService.get_oauth_flow()
        if not flow:
            return None
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        return authorization_url
    
    @staticmethod
    def exchange_code(code):
        flow = GoogleCalendarService.get_oauth_flow()
        if not flow:
            return None
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        return credentials
    
    @staticmethod
    def get_service(credentials):
        return build('calendar', 'v3', credentials=credentials)
    
    @staticmethod
    def create_event(credentials, appointment, calendar_id='primary'):
        try:
            service = GoogleCalendarService.get_service(credentials)
            
            event = {
                'summary': f"{appointment.service.name} - {appointment.patient.full_name}",
                'description': (
                    f"Booking Reference: {appointment.reference}\n"
                    f"Patient: {appointment.patient.full_name}\n"
                    f"Phone: {appointment.patient.phone}\n"
                    f"Email: {appointment.patient.email}\n"
                    f"Service: {appointment.service.name}\n"
                    f"Practitioner: {appointment.practitioner.full_name if appointment.practitioner else 'N/A'}\n"
                    f"Notes: {appointment.notes or 'None'}"
                ),
                'start': {
                    'dateTime': appointment.start_time.isoformat(),
                    'timeZone': current_app.config.get('TIMEZONE', 'UTC'),
                },
                'end': {
                    'dateTime': appointment.end_time.isoformat(),
                    'timeZone': current_app.config.get('TIMEZONE', 'UTC'),
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},
                        {'method': 'popup', 'minutes': 15},
                    ],
                },
            }
            
            if appointment.practitioner and appointment.practitioner.email:
                event['attendees'] = [
                    {'email': appointment.practitioner.email}
                ]
            
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event,
                sendUpdates='all' if 'attendees' in event else 'none'
            ).execute()
            
            return created_event.get('id')
        except Exception as e:
            logger.error(f"Google Calendar event creation failed: {str(e)}")
            return None
    
    @staticmethod
    def update_event(credentials, appointment, calendar_id='primary'):
        if not appointment.google_calendar_event_id:
            return GoogleCalendarService.create_event(credentials, appointment, calendar_id)
        
        try:
            service = GoogleCalendarService.get_service(credentials)
            
            event = {
                'summary': f"{appointment.service.name} - {appointment.patient.full_name}",
                'description': (
                    f"Booking Reference: {appointment.reference}\n"
                    f"Patient: {appointment.patient.full_name}\n"
                    f"Service: {appointment.service.name}\n"
                    f"Practitioner: {appointment.practitioner.full_name if appointment.practitioner else 'N/A'}"
                ),
                'start': {
                    'dateTime': appointment.start_time.isoformat(),
                    'timeZone': current_app.config.get('TIMEZONE', 'UTC'),
                },
                'end': {
                    'dateTime': appointment.end_time.isoformat(),
                    'timeZone': current_app.config.get('TIMEZONE', 'UTC'),
                },
            }
            
            service.events().update(
                calendarId=calendar_id,
                eventId=appointment.google_calendar_event_id,
                body=event,
                sendUpdates='all'
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Google Calendar event update failed: {str(e)}")
            return False
    
    @staticmethod
    def delete_event(credentials, calendar_id='primary', event_id=None):
        if not event_id:
            return True
        
        try:
            service = GoogleCalendarService.get_service(credentials)
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all'
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Google Calendar event deletion failed: {str(e)}")
            return False
    
    @staticmethod
    def generate_add_to_calendar_url(appointment):
        import urllib.parse
        
        start = appointment.start_time.strftime('%Y%m%dT%H%M%SZ')
        end = appointment.end_time.strftime('%Y%m%dT%H%M%SZ')
        
        details = (
            f"Booking Reference: {appointment.reference}\n"
            f"Service: {appointment.service.name}\n"
            f"Practitioner: {appointment.practitioner.full_name if appointment.practitioner else 'N/A'}\n"
            f"Patient: {appointment.patient.full_name}"
        )
        
        params = {
            'action': 'TEMPLATE',
            'text': f"{appointment.service.name} - Venus Clinic",
            'dates': f"{start}/{end}",
            'details': details,
            'location': current_app.config.get('CLINIC_ADDRESS', ''),
        }
        
        return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    def get_ics_content(appointment):
        from icalendar import Calendar, Event as ICalEvent
        from datetime import timezone
        
        cal = Calendar()
        cal.add('prodid', '-//Venus Clinic//Booking System//EN')
        cal.add('version', '2.0')
        
        event = ICalEvent()
        event.add('summary', f"{appointment.service.name} - Venus Clinic")
        event.add('description', (
            f"Booking Reference: {appointment.reference}\n"
            f"Patient: {appointment.patient.full_name}\n"
            f"Service: {appointment.service.name}\n"
            f"Practitioner: {appointment.practitioner.full_name if appointment.practitioner else 'N/A'}"
        ))
        event.add('dtstart', appointment.start_time.replace(tzinfo=timezone.utc))
        event.add('dtend', appointment.end_time.replace(tzinfo=timezone.utc))
        event.add('location', current_app.config.get('CLINIC_ADDRESS', ''))
        event.add('status', 'CONFIRMED')
        event.add('uid', f"{appointment.reference}@venusclinic.com")
        
        cal.add_component(event)
        return cal.to_ical()
