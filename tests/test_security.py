from datetime import timedelta

from conftest import post_with_csrf
from extensions import db
from models import AuditEvent, AuthSession, Resource, Session


def test_csrf_blocks_state_changing_post_without_token(client):
    response = client.post("/user/signup", data={"full_name": "A", "email": "a@example.test", "password": "StrongPassword123!", "confirm_password": "StrongPassword123!"})
    assert response.status_code == 400


def test_signup_rejects_oversized_password(client):
    password = "A" + "a" * 255 + "1!"
    response = post_with_csrf(client, "/user/signup", {"full_name": "Large Password", "email": "large@example.test", "password": password, "confirm_password": password})
    assert response.status_code == 400


def test_sql_injection_search_is_plain_text(user_client, app):
    with app.app_context():
        item = Session.query.filter_by(day="Day 1").first()
        db.session.add(Resource(session_title=item.title, day=item.day, time_slot=item.time_slot, resource_type="PDF", description="Ordinary resource", url="https://example.org", prerequisite="None"))
        db.session.commit()
    response = user_client.get("/user/resources?q=%27+OR+%271%27%3D%271")
    assert b"Ordinary resource" not in response.data


def test_audit_log_records_admin_actions_without_form_contents(admin_client, app):
    with app.app_context():
        events = AuditEvent.query.all()
        assert any(event.action == "ADMIN LOGIN" for event in events)
        assert all(not event.resource_id or event.action != "ADMIN LOGIN" for event in events)


def test_user_is_forbidden_from_audit_and_admin_resource_routes(user_client):
    assert user_client.get("/admin/audit-logs").status_code == 403
    assert user_client.get("/admin/resources").status_code == 403


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
