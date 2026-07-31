from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm
from app.models.user import User, Role
from app.models.patient import Patient
from app.extensions import db


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_redirect_url())
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.first_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or get_redirect_url())
        flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        patient_role = Role.query.filter_by(name='Patient').first()
        if not patient_role:
            patient_role = Role(name='Patient', description='Patient role')
            db.session.add(patient_role)
            db.session.flush()
        
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role_id=patient_role.id
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()
        
        patient = Patient(
            user_id=user.id,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data.lower(),
            phone=form.phone.data
        )
        db.session.add(patient)
        db.session.commit()
        
        login_user(user)
        flash('Account created successfully! Welcome to Venus Clinic.', 'success')
        return redirect(url_for('patient.dashboard'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.is_patient:
        patient = Patient.query.filter_by(user_id=current_user.id).first()
        form = ProfileForm(obj=current_user)
        
        if form.validate_on_submit():
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone = form.phone.data
            if patient:
                patient.first_name = form.first_name.data
                patient.last_name = form.last_name.data
                patient.phone = form.phone.data
                if form.date_of_birth.data:
                    patient.date_of_birth = form.date_of_birth.data
                if form.gender.data:
                    patient.gender = form.gender.data
                if form.address.data:
                    patient.address = form.address.data
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('auth.profile'))
        
        return render_template('patient/profile.html', form=form, patient=patient)
    
    return render_template('auth/profile.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', form=form)


def get_redirect_url():
    if current_user.is_admin:
        return url_for('admin.dashboard')
    elif current_user.is_receptionist:
        return url_for('admin.dashboard')
    elif current_user.is_patient:
        return url_for('patient.dashboard')
    return url_for('main.index')
