import csv
import io

from flask import Blueprint, make_response, render_template, request
from sqlalchemy import or_

from auth_helpers import role_required
from extensions import db
from models import Resource, Session

resources_bp = Blueprint("resources", __name__)


def filtered_query(args):
    query = Resource.query
    term = args.get("q", "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(or_(Resource.session_title.ilike(like), Resource.description.ilike(like), Resource.prerequisite.ilike(like), Resource.resource_type.ilike(like)))
    day, kind, title = args.get("day", ""), args.get("resource_type", ""), args.get("session_title", "")
    if day in {f"Day {n}" for n in range(1, 7)}:
        query = query.filter(Resource.day == day)
    if kind in ("PDF", "Documentation", "Article", "Video", "Website", "Other"):
        query = query.filter(Resource.resource_type == kind)
    if title:
        query = query.filter(Resource.session_title == title)
    return query.order_by(Resource.day, Resource.session_title, Resource.time_slot)


def directory_context():
    return {
        "resources": filtered_query(request.args).all(),
        "days": [f"Day {n}" for n in range(1, 7)],
        "types": ("PDF", "Documentation", "Article", "Video", "Website", "Other"),
        "sessions": Session.query.order_by(Session.sort_order).all(),
        "role": "user",
    }


@resources_bp.get("/user/dashboard")
@role_required("user")
def user_dashboard():
    user = request.auth_principal
    recent = Resource.query.order_by(Resource.created_at.desc()).limit(5).all()
    categories = db.session.query(Resource.resource_type, db.func.count(Resource.id)).group_by(Resource.resource_type).order_by(Resource.resource_type).all()
    return render_template("user_dashboard.html", user=user, recent=recent, categories=categories, role="user")


@resources_bp.get("/user/resources")
@role_required("user")
def directory():
    return render_template("resources.html", **directory_context())


@resources_bp.get("/user/resources/<int:resource_id>")
@role_required("user")
def detail(resource_id):
    resource = db.get_or_404(Resource, resource_id)
    return render_template("resource_detail.html", resource=resource, role="user")


@resources_bp.get("/user/resources/export.csv")
@role_required("user")
def export_csv():
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    columns = ("session_title", "day", "time_slot", "resource_type", "description", "url", "prerequisite")
    writer.writerow(columns)
    for resource in filtered_query(request.args).all():
        writer.writerow([getattr(resource, col) for col in columns])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=workshop-resources.csv"
    return response
