import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200


def test_booking_page(client):
    response = client.get('/booking/')
    assert response.status_code == 200


def test_login_page(client):
    response = client.get('/auth/login')
    assert response.status_code == 200