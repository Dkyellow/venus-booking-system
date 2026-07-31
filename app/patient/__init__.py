from flask import Blueprint

patient_bp = Blueprint('patient', __name__, template_folder='../templates/patient')

from app.patient import routes
