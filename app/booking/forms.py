from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional


class PublicBookingForm(FlaskForm):
    service_id = HiddenField('Service', validators=[DataRequired()])
    practitioner_id = HiddenField('Practitioner')
    date = HiddenField('Date', validators=[DataRequired()])
    start_time = HiddenField('Start Time', validators=[DataRequired()])
    end_time = HiddenField('End Time', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=7, max=20)])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    gender = SelectField('Gender', choices=[('', 'Prefer not to say'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    reason = TextAreaField('Reason for Visit', validators=[Optional()])
    notes = TextAreaField('Additional Notes', validators=[Optional()])


class ManageBookingForm(FlaskForm):
    reference = StringField('Booking Reference', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
