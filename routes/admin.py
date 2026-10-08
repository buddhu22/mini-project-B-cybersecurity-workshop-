from datetime import datetime, timezone

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required, set_access_cookies
from werkzeug.security import check_password_hash

from auth_helpers import clear_auth, issue_tokens, revoke_from_cookie, role_required
from extensions import db, limiter
from models import AdminAccount, AuditEvent, AuthSession, Resource, Session as WorkshopSession
from validators import REVIEW_STATUSES, validate_resource

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def audit(action, resource_id=None):
    db.session.add(AuditEvent(action=action, resource_id=resource_id, actor_role="admin"))
    db.session.commit()
    current_app.logger.info("ADMIN %s resource_id=%s", action, resource_id if resource_id is not None else "none")


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password", "")
        admin = AdminAccount.query.filter_by(username=username).first() if username and len(password) <= 256 else None
        if not admin or not check_password_hash(admin.password_hash, password):
            current_app.logger.warning("ADMIN LOGIN FAILURE")
            flash("Invalid username/email or password.", "error")
            return render_template("admin_login.html", username=username), 401
        response = redirect(url_for("admin.dashboard"))
        issue_tokens(response, admin, "admin")
        audit("ADMIN LOGIN")
        return response
    return render_template("admin_login.html", username="")


@admin_bp.post("/logout")
def logout():
    revoke_from_cookie()
    session.clear()
    response = redirect(url_for("admin.login"))
    clear_auth(response)
    flash("Administrator session signed out.", "success")
    return response


@admin_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return "Forbidden", 403
    from auth_helpers import get_active_session
    row, issue = get_active_session(claims, "admin", touch=True)
    if issue:
        response = current_app.make_response(("Session expired", 401))
        clear_auth(response)
        return response
    access = create_access_token(identity=str(get_jwt_identity()), additional_claims={"role": "admin", "sid": row.id})
    response = current_app.make_response({"ok": True})
    set_access_cookies(response, access)
    return response


@admin_bp.get("/renew")
@jwt_required(refresh=True)
def renew():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return "Forbidden", 403
    from auth_helpers import get_active_session
    row, issue = get_active_session(claims, "admin", touch=True)
    if issue:
        return redirect(url_for("admin.login"))
    access = create_access_token(identity=str(get_jwt_identity()), additional_claims={"role": "admin", "sid": row.id})
    target = request.args.get("next", "")
    if not target.startswith("/admin/") or target.startswith("//"):
        target = url_for("admin.dashboard")
    response = redirect(target)
    set_access_cookies(response, access)
    return response


@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    day_counts = [(f"Day {n}", Resource.query.filter_by(day=f"Day {n}").count()) for n in range(1, 7)]
    type_counts = db.session.query(Resource.resource_type, db.func.count(Resource.id)).group_by(Resource.resource_type).order_by(Resource.resource_type).all()
    needs_review = Resource.query.filter(Resource.resource_review_status.in_(("Not Reviewed", "Needs Review", "Broken"))).count()
    recent = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(8).all()
    return render_template("admin.html", day_counts=day_counts, type_counts=type_counts, needs_review=needs_review, recent=recent, role="admin", session_count=WorkshopSession.query.count(), resource_count=Resource.query.count())


@admin_bp.get("/reports")
@role_required("admin")
def reports():
    day_counts = [(f"Day {n}", Resource.query.filter_by(day=f"Day {n}").count()) for n in range(1, 7)]
    type_counts = db.session.query(Resource.resource_type, db.func.count(Resource.id)).group_by(Resource.resource_type).order_by(Resource.resource_type).all()
    return render_template("reports.html", day_counts=day_counts, type_counts=type_counts, role="admin")


@admin_bp.get("/settings")
@role_required("admin")
def settings():
    return render_template("admin_settings.html", role="admin", access_minutes=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"] // 60, refresh_days=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"] // (24 * 60 * 60), secure_cookies=current_app.config["JWT_COOKIE_SECURE"])


@admin_bp.get("/resources")
@role_required("admin")
def resource_list():
    from routes.resources import directory_context
    context = directory_context()
    context["role"] = "admin"
    return render_template("resources.html", **context)


@admin_bp.get("/sessions")
@role_required("admin")
def sessions():
    days = [(f"Day {i}", WorkshopSession.query.filter_by(day=f"Day {i}").order_by(WorkshopSession.sort_order).all()) for i in range(1, 7)]
    return render_template("sessions.html", days=days, role="admin")


@admin_bp.get("/resources/<int:resource_id>")
@role_required("admin")
def resource_detail(resource_id):
    resource = db.get_or_404(Resource, resource_id)
    return render_template("resource_detail.html", resource=resource, role="admin")


@admin_bp.get("/resources/export.csv")
@role_required("admin")
def export_csv():
    from routes.resources import filtered_query
    import csv
    import io
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    columns = ("session_title", "day", "time_slot", "resource_type", "description", "url", "prerequisite")
    writer.writerow(columns)
    for resource in filtered_query(request.args).all():
        writer.writerow([getattr(resource, column) for column in columns])
    response = current_app.make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=workshop-resources.csv"
    return response


@admin_bp.route("/resources/create", methods=["GET", "POST"])
@role_required("admin")
def create_resource():
    sessions = WorkshopSession.query.order_by(WorkshopSession.sort_order).all()
    if request.method == "POST":
        values, status, errors = validate_resource(request.form, {item.title for item in sessions})
        try:
            selected = db.session.get(WorkshopSession, int(request.form.get("session_id", "")))
        except (TypeError, ValueError):
            selected = None
        if not selected or selected.title != values["session_title"] or selected.day != values["day"]:
            errors["session_title"] = "Choose a valid session from the timetable."
        if not errors:
            resource = Resource(**values, time_slot=selected.time_slot, resource_review_status=status)
            db.session.add(resource)
            db.session.commit()
            audit("CREATE", resource.id)
            flash("Resource created.", "success")
            return redirect(url_for("admin.resource_detail", resource_id=resource.id))
        return render_template("resource_form.html", resource=request.form, errors=errors, sessions=sessions, statuses=REVIEW_STATUSES, heading="Add resource", role="admin"), 400
    return render_template("resource_form.html", resource={}, errors={}, sessions=sessions, statuses=REVIEW_STATUSES, heading="Add resource", role="admin")


@admin_bp.route("/resources/<int:resource_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_resource(resource_id):
    resource = db.get_or_404(Resource, resource_id)
    sessions = WorkshopSession.query.order_by(WorkshopSession.sort_order).all()
    if request.method == "POST":
        values, status, errors = validate_resource(request.form, {item.title for item in sessions})
        try:
            selected = db.session.get(WorkshopSession, int(request.form.get("session_id", "")))
        except (TypeError, ValueError):
            selected = None
        if not selected or selected.title != values["session_title"] or selected.day != values["day"]:
            errors["session_title"] = "Choose a valid session from the timetable."
        if not errors:
            for key, value in values.items():
                setattr(resource, key, value)
            resource.time_slot = selected.time_slot
            resource.resource_review_status = status
            resource.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit("UPDATE", resource.id)
            flash("Resource updated.", "success")
            return redirect(url_for("admin.resource_detail", resource_id=resource.id))
        return render_template("resource_form.html", resource=request.form, errors=errors, sessions=sessions, statuses=REVIEW_STATUSES, heading="Edit resource", role="admin"), 400
    resource_values = {key: getattr(resource, key) for key in ("session_title", "day", "time_slot", "resource_type", "description", "url", "prerequisite", "resource_review_status")}
    return render_template("resource_form.html", resource=resource_values, errors={}, sessions=sessions, statuses=REVIEW_STATUSES, heading="Edit resource", role="admin")


@admin_bp.post("/resources/<int:resource_id>/delete")
@role_required("admin")
def delete_resource(resource_id):
    resource = db.get_or_404(Resource, resource_id)
    db.session.delete(resource)
    db.session.commit()
    audit("DELETE", resource_id)
    flash("Resource deleted.", "success")
    return redirect(url_for("admin.resource_list"))


@admin_bp.get("/audit-logs")
@role_required("admin")
def audit_logs():
    events = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(200).all()
    return render_template("audit_logs.html", events=events, role="admin")
