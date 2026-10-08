from datetime import timedelta

from flask_jwt_extended import create_access_token, decode_token
from werkzeug.security import check_password_hash

from conftest import post_with_csrf
from extensions import db
from models import AuthSession, UserAccount


def signup(client, name="Participant", email="person@example.test", password="StrongPassword123!"):
    return post_with_csrf(client, "/user/signup", {"full_name": name, "email": email, "password": password, "confirm_password": password})


def login_user(client, email="person@example.test", password="StrongPassword123!"):
    return post_with_csrf(client, "/user/login", {"email": email, "password": password})


def test_signup_hashes_password_and_login_sets_httponly_jwts(client, app):
    assert signup(client).status_code == 302
    with app.app_context():
        user = UserAccount.query.filter_by(email="person@example.test").one()
        assert user.password_hash != "StrongPassword123!"
        assert check_password_hash(user.password_hash, "StrongPassword123!")
    response = login_user(client)
    assert response.status_code == 302 and response.location.endswith("/user/dashboard")
    cookies = "\n".join(response.headers.getlist("Set-Cookie"))
    assert "workshop_access_token=" in cookies and "HttpOnly" in cookies
    assert "workshop_refresh_token=" in cookies and "HttpOnly" in cookies
    access = client.get_cookie("workshop_access_token").value
    with app.app_context():
        assert decode_token(access)["role"] == "user"
    assert "localStorage" not in client.get("/user/dashboard").get_data(as_text=True)


def test_invalid_login_uses_generic_message(client):
    signup(client)
    response = post_with_csrf(client, "/user/login", {"email": "person@example.test", "password": "wrong"})
    assert response.status_code == 401
    assert b"Invalid username/email or password." in response.data


def test_user_login_portal_has_five_minute_inactivity_timeout(client):
    response = client.get("/user/login")
    assert response.status_code == 200
    assert b'data-login-timeout="300"' in response.data
    assert b"login-timeout.js" in response.data
    assert b"Login portal timed out due to inactivity." in response.data
    assert b"doesn't exist" not in response.data and b"incorrect" not in response.data


def test_user_jwt_protects_dashboard_and_role_separates_admin(client, user_client):
    assert user_client.get("/user/dashboard").status_code == 200
    assert user_client.get("/user/resources").status_code == 200
    assert user_client.get("/admin/dashboard").status_code == 403


def test_admin_login_and_admin_jwt(client, app):
    page = client.get("/admin/login")
    assert b"Admin Username" in page.data and b"Create Account" not in page.data
    response = post_with_csrf(client, "/admin/login", {"username": "workshop-admin", "password": "TestAdminPass123!"})
    assert response.status_code == 302 and response.location.endswith("/admin/dashboard")
    token = client.get_cookie("workshop_access_token").value
    with app.app_context():
        assert decode_token(token)["role"] == "admin"
    assert client.get("/admin/dashboard").status_code == 200
    assert client.get("/admin/resources").status_code == 200
    assert client.get("/admin/audit-logs").status_code == 200


def test_invalid_admin_login_generic_and_no_public_signup(client):
    response = post_with_csrf(client, "/admin/login", {"username": "missing", "password": "not-it"})
    assert response.status_code == 401 and b"Invalid username/email or password." in response.data
    assert client.get("/admin/signup").status_code == 404


def test_user_logout_revokes_refresh_and_clears_jwt(user_client, app):
    refresh = user_client.get_cookie("workshop_refresh_token").value
    with app.app_context():
        claims = decode_token(refresh)
    response = post_with_csrf(user_client, "/user/logout", {}, referer="/user/dashboard")
    assert response.status_code == 302 and response.location.endswith("/user/login")
    assert user_client.get_cookie("workshop_access_token") is None
    with app.app_context():
        assert db.session.get(AuthSession, claims["sid"]).revoked_at is not None


def test_admin_logout_clears_admin_jwt(admin_client):
    response = post_with_csrf(admin_client, "/admin/logout", {}, referer="/admin/dashboard")
    assert response.status_code == 302 and response.location.endswith("/admin/login")
    assert admin_client.get_cookie("workshop_access_token") is None


def test_admin_refresh_renews_admin_access_cookie(admin_client):
    old_token = admin_client.get_cookie("workshop_access_token").value
    response = post_with_csrf(admin_client, "/admin/refresh", {}, referer="/admin/dashboard")
    assert response.status_code == 200 and response.json["ok"] is True
    assert admin_client.get_cookie("workshop_access_token").value != old_token


def test_expired_access_token_redirects_to_login(client, app):
    signup(client)
    login_user(client)
    with app.app_context():
        user = UserAccount.query.filter_by(email="person@example.test").one()
        auth = AuthSession.query.filter_by(principal_id=user.id, role="user").one()
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(seconds=-2), additional_claims={"role": "user", "sid": auth.id})
    client.set_cookie("workshop_access_token", token)
    response = client.get("/user/dashboard", follow_redirects=True)
    assert response.status_code == 200 and b"Welcome, Participant" in response.data


def test_user_dashboard_has_no_post_login_session_timer(user_client):
    response = user_client.get("/user/dashboard")
    assert response.status_code == 200
    assert b"timeout-countdown" not in response.data
    assert b"timeout-warning" not in response.data
    assert b"session.js" not in response.data


def test_user_session_is_not_expired_by_inactivity(user_client, app):
    with app.app_context():
        auth = AuthSession.query.filter_by(role="user").one()
        auth.last_activity = auth.last_activity - timedelta(minutes=31)
        db.session.commit()
    response = user_client.get("/user/dashboard")
    assert response.status_code == 200


def test_refresh_token_renews_access_cookie(user_client):
    old_token = user_client.get_cookie("workshop_access_token").value
    response = post_with_csrf(user_client, "/user/refresh", {}, referer="/user/dashboard")
    assert response.status_code == 200 and response.json["ok"] is True
    assert user_client.get_cookie("workshop_access_token").value != old_token
