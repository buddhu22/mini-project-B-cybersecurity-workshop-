import re

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models import AdminAccount


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-long-enough-for-session-signing",
        "JWT_SECRET_KEY": "test-jwt-secret-key-long-enough-for-signing",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "WTF_CSRF_ENABLED": True,
    })
    with app.app_context():
        db.create_all()
        from data.seed_resources import seed_sessions
        seed_sessions()
        db.session.add(AdminAccount(username="workshop-admin", password_hash=generate_password_hash("TestAdminPass123!")))
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_value(response):
    found = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert found, f"Form should include a CSRF token; response was {response.status_code} {response.location}"
    return found.group(1).decode()


def post_with_csrf(client, path, data, referer=None):
    page = client.get(referer or path)
    token = csrf_value(page)
    response = client.post(path, data={**data, "csrf_token": token}, headers={"Referer": "http://localhost/" + path.lstrip("/")})
    if response.status_code == 400 and b"CSRF" in response.data:
        raise AssertionError(f"CSRF failed on {path}; session_cookie={bool(client.get_cookie('session'))}; page_status={page.status_code}")
    return response


@pytest.fixture
def user_client(app):
    client = app.test_client()
    post_with_csrf(client, "/user/signup", {
        "full_name": "Workshop Participant",
        "email": "participant@example.test",
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
    })
    post_with_csrf(client, "/user/login", {"email": "participant@example.test", "password": "StrongPassword123!"})
    return client


@pytest.fixture
def admin_client(app):
    client = app.test_client()
    response = post_with_csrf(client, "/admin/login", {"username": "workshop-admin", "password": "TestAdminPass123!"})
    assert response.status_code == 302 and client.get_cookie("workshop_access_token"), f"Admin fixture login failed: {response.status_code} {response.get_data(as_text=True)}"
    return client
