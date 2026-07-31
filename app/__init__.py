from flask import Flask
from app.config import config
from app.extensions import db, login_manager, migrate, mail, csrf, limiter


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    migrate.init_app(app, db)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    print(f"[MAIL CONFIG] Server: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}")
    print(f"[MAIL CONFIG] Username: {app.config.get('MAIL_USERNAME')}")
    print(f"[MAIL CONFIG] Sender: {app.config.get('MAIL_DEFAULT_SENDER')}")
    
    from app.models import user, patient, staff, service, appointment, schedule, notification, settings, audit
    
    from app.auth import auth_bp
    from app.main import main_bp
    from app.admin import admin_bp
    from app.booking import booking_bp
    from app.patient import patient_bp
    from app.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(booking_bp, url_prefix='/booking')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    @app.context_processor
    def inject_globals():
        from app.models.settings import ClinicSettings
        settings = ClinicSettings.query.first()
        return dict(
            clinic_settings=settings,
            clinic_name=app.config.get('CLINIC_NAME', 'Venus Clinic'),
            current_year=__import__('datetime').datetime.now().year
        )
    
    return app