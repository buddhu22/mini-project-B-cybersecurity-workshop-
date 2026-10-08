import csv
import io

from conftest import post_with_csrf
from extensions import db
from models import Resource, Session


def resource_form(app, title="Rapid Web Application Development using Flask", day="Day 4", description="Flask notes", url="https://example.org/flask.pdf"):
    with app.app_context():
        item = Session.query.filter_by(title=title, day=day).order_by(Session.sort_order).first()
        return {"session_id": str(item.id), "session_title": title, "day": day, "resource_type": "PDF", "description": description, "url": url, "prerequisite": "Python basics"}


def test_public_root_is_auth_choice_and_sessions_are_protected(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"Welcome to the Workshop Portal" in page.data
    assert b"Continue as User" in page.data and b"Administrator Login" in page.data
    assert client.get("/user/sessions").status_code == 302


def test_admin_can_create_update_delete_resource(admin_client, app):
    created = post_with_csrf(admin_client, "/admin/resources/create", resource_form(app))
    assert created.status_code == 302
    resource_id = int(created.location.rsplit("/", 1)[-1])
    edit_path = f"/admin/resources/{resource_id}/edit"
    data = resource_form(app, description="Updated Flask resource")
    data["resource_review_status"] = "Working"
    updated = post_with_csrf(admin_client, edit_path, data)
    assert updated.status_code == 302
    with app.app_context():
        resource = db.session.get(Resource, resource_id)
        assert resource.description == "Updated Flask resource"
        assert resource.resource_review_status == "Working"
    deleted = post_with_csrf(admin_client, f"/admin/resources/{resource_id}/delete", {}, referer=f"/admin/resources/{resource_id}")
    assert deleted.status_code == 302
    with app.app_context():
        assert db.session.get(Resource, resource_id) is None


def test_admin_form_rejects_malicious_url(admin_client, app):
    data = resource_form(app, url="javascript:alert(1)")
    response = post_with_csrf(admin_client, "/admin/resources/create", data)
    assert response.status_code == 400
    with app.app_context():
        assert Resource.query.count() == 0


def test_xss_looking_name_is_escaped(client):
    post_with_csrf(client, "/user/signup", {"full_name": "<script>alert('x')</script>", "email": "xss@example.test", "password": "StrongPassword123!", "confirm_password": "StrongPassword123!"})
    post_with_csrf(client, "/user/login", {"email": "xss@example.test", "password": "StrongPassword123!"})
    response = client.get("/user/dashboard")
    assert b"&lt;script&gt;" in response.data
    assert b"<script>alert(" not in response.data


def test_authenticated_search_and_filtered_csv(user_client, admin_client, app):
    post_with_csrf(admin_client, "/admin/resources/create", resource_form(app), referer="/admin/dashboard")
    response = user_client.get("/user/resources?q=Flask&day=Day+4")
    assert b"Flask notes" in response.data
    csv_response = user_client.get("/user/resources/export.csv?q=Flask&day=Day+4")
    rows = list(csv.reader(io.StringIO(csv_response.get_data(as_text=True))))
    assert rows[0] == ["session_title", "day", "time_slot", "resource_type", "description", "url", "prerequisite"]
    assert len(rows) == 2 and rows[1][1] == "Day 4"


def test_admin_csv_is_admin_only(user_client, admin_client):
    assert user_client.get("/admin/resources/export.csv").status_code == 403
    assert admin_client.get("/admin/resources/export.csv").status_code == 200
