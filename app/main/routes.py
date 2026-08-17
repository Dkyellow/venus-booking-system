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


@main_bp.route('/about')
def about():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order).all()
    return render_template('main/about.html', services=services)


@main_bp.route('/services')
def services():
    services = Service.query.filter_by(is_active=True, is_online_bookable=True).order_by(Service.sort_order).all()
    return render_template('main/services.html', services=services)


@main_bp.route('/gallery')
def gallery():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order).all()
    return render_template('main/gallery.html', services=services)


@main_bp.route('/faq')
def faq():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order).all()
    return render_template('main/faq.html', services=services)


@main_bp.route('/contact')
def contact():
    services = Service.query.filter_by(is_active=True).order_by(Service.sort_order).all()
    return render_template('main/contact.html', services=services)