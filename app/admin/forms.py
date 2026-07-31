from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SelectField,
                     TextAreaField, DateField, TimeField, IntegerField,
                     DecimalField, FileField, ColorField)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from datetime import datetime


class ServiceForm(FlaskForm):
    name = StringField('Service Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=5, max=480)])
    buffer_time = IntegerField('Buffer Time (minutes)', validators=[Optional(), NumberRange(min=0, max=120)], default=15)
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    price = DecimalField('Price', validators=[Optional(), NumberRange(min=0)], places=2, default=0)
    color = StringField('Color', default='#4F46E5')
    is_active = BooleanField('Active', default=True)
    is_online_bookable = BooleanField('Online Bookable', default=True)
    max_advance_days = IntegerField('Max Advance Booking (days)', validators=[Optional()], default=60)
    min_advance_hours = IntegerField('Min Advance Booking (hours)', validators=[Optional()], default=2)
    sort_order = IntegerField('Sort Order', validators=[Optional()], default=0)


class StaffForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    specialization = StringField('Specialization', validators=[Optional(), Length(max=100)])
    title = StringField('Title', validators=[Optional(), Length(max=50)])
    bio = TextAreaField('Biography', validators=[Optional()])
    color = StringField('Color', default='#4F46E5')
    consultation_fee = DecimalField('Consultation Fee', validators=[Optional()], places=2, default=0)
    is_active = BooleanField('Active', default=True)
    is_practitioner = BooleanField('Is Practitioner', default=True)


class ScheduleForm(FlaskForm):
    staff_id = SelectField('Practitioner', coerce=int, validators=[DataRequired()])
    day_of_week = SelectField('Day', coerce=int, validators=[DataRequired()],
                              choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
                                       (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])
    start_time = TimeField('Start Time', validators=[DataRequired()], format='%H:%M')
    end_time = TimeField('End Time', validators=[DataRequired()], format='%H:%M')
    is_active = BooleanField('Active', default=True)


class BlockedTimeForm(FlaskForm):
    staff_id = SelectField('Practitioner', coerce=int, validators=[DataRequired()])
    start_time = StringField('Start', validators=[DataRequired()])
    end_time = StringField('End', validators=[DataRequired()])
    reason = StringField('Reason', validators=[Optional(), Length(max=200)])


class HolidayForm(FlaskForm):
    name = StringField('Holiday Name', validators=[DataRequired(), Length(max=100)])
    date = DateField('Date', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    is_recurring = BooleanField('Recurring Annually', default=False)


class SettingsForm(FlaskForm):
    clinic_name = StringField('Clinic Name', validators=[DataRequired()])
    clinic_email = StringField('Email', validators=[DataRequired(), Email()])
    clinic_phone = StringField('Phone', validators=[DataRequired()])
    clinic_address = TextAreaField('Address', validators=[DataRequired()])
    clinic_website = StringField('Website', validators=[Optional()])
    timezone = SelectField('Timezone', choices=[
        ('UTC', 'UTC'), ('US/Eastern', 'Eastern Time'), ('US/Central', 'Central Time'),
        ('US/Pacific', 'Pacific Time'), ('Europe/London', 'London'), ('Europe/Paris', 'Paris'),
        ('Asia/Dubai', 'Dubai'), ('Asia/Kolkata', 'India'), ('Asia/Singapore', 'Singapore')
    ], default='UTC')
    brand_primary_color = StringField('Primary Color', default='#4F46E5')
    brand_secondary_color = StringField('Secondary Color', default='#7C3AED')
    brand_accent_color = StringField('Accent Color', default='#06B6D4')
    enable_email_notifications = BooleanField('Email Notifications', default=True)
    enable_whatsapp_notifications = BooleanField('WhatsApp Notifications', default=False)
    enable_google_calendar_sync = BooleanField('Google Calendar Sync', default=False)


class AppointmentForm(FlaskForm):
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    practitioner_id = SelectField('Practitioner', coerce=int, validators=[Optional()])
    service_id = SelectField('Service', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    start_time = StringField('Start Time', validators=[DataRequired()])
    end_time = StringField('End Time', validators=[DataRequired()])
    reason = TextAreaField('Reason', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    internal_notes = TextAreaField('Internal Notes', validators=[Optional()])


class PatientForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Select'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    address = TextAreaField('Address', validators=[Optional()])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional()])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Optional()])
    medical_notes = TextAreaField('Medical Notes', validators=[Optional()])
