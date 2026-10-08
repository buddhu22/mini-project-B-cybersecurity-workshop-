from flask import Blueprint, render_template, request

from auth_helpers import role_required
from models import Resource, Session as WorkshopSession

main_bp = Blueprint("main", __name__)


@main_bp.get("/user/sessions")
@role_required("user")
def sessions():
    days = [(f"Day {i}", WorkshopSession.query.filter_by(day=f"Day {i}").order_by(WorkshopSession.sort_order).all()) for i in range(1, 7)]
    return render_template("sessions.html", days=days, role="user")
