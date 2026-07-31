from flask import jsonify, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app.api import api_bp
from app.models.appointment import Appointment
from app.models.audit import GoogleCalendarToken
from app.extensions import db
from app.services.google_calendar_service import GoogleCalendarService


@api_bp.route('/google-calendar/connect')
@login_required
def google_calendar_connect():
    auth_url = GoogleCalendarService.get_authorization_url()
    if not auth_url:
        flash('Google Calendar integration is not configured.', 'danger')
        return redirect(url_for('admin.settings'))
    return redirect(auth_url)


@api_bp.route('/google-calendar/callback')
@login_required
def google_calendar_callback():
    code = request.args.get('code')
    if not code:
        flash('Authorization failed.', 'danger')
        return redirect(url_for('admin.settings'))
    
    credentials = GoogleCalendarService.exchange_code(code)
    if credentials:
        token = GoogleCalendarToken(
            user_id=current_user.id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            client_id=current_app.config.get('GOOGLE_CALENDAR_CLIENT_ID'),
            client_secret=current_app.config.get('GOOGLE_CALENDAR_CLIENT_SECRET'),
            scopes=','.join(credentials.scopes) if credentials.scopes else '',
            expires_at=credentials.expiry,
            is_active=True
        )
        db.session.add(token)
        db.session.commit()
        flash('Google Calendar connected successfully!', 'success')
    else:
        flash('Failed to connect to Google Calendar.', 'danger')
    
    return redirect(url_for('admin.settings'))
