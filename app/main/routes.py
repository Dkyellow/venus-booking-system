from flask import render_template
from app.main import main_bp
from app.models.service import Service, ServiceCategory
from app.models.staff import Staff


@main_bp.route('/')
def index():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order).all()
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.sort_order).all()
    practitioners = Staff.query.filter_by(is_active=True, is_practitioner=True).all()
    return render_template('main/index.html', services=services, categories=categories, practitioners=practitioners)
