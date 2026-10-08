import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required, set_access_cookies
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from auth_helpers import clear_auth, get_active_session, issue_tokens, refresh_user_session, revoke_from_cookie
from extensions import db, limiter
from models import AuditEvent, UserAccount

auth_bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@auth_bp.get("/")
def portal():
    return render_template("auth_portal.html")


@auth_bp.get("/user/auth")
def user_portal():
    return render_template("user_portal.html")


@auth_bp.route("/user/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def user_signup():
    errors = {}
    values = {key: "" for key in ("full_name", "email")}
    if request.method == "POST":
        values = {key: (request.form.get(key) or "").strip() for key in values}
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not values["full_name"] or len(values["full_name"]) > 120:
            errors["full_name"] = "Enter your name (up to 120 characters)."
        email = values["email"].lower()
        if len(email) > 254 or not EMAIL_RE.fullmatch(email):
            errors["email"] = "Enter a valid email address."
        elif UserAccount.query.filter(func.lower(UserAccount.email) == email).first():
            errors["email"] = "An account with this email already exists."
        if len(password) < 12 or len(password) > 256 or not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password) or not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
            errors["password"] = "Use at least 12 characters with uppercase, lowercase, number, and symbol."
        if password != confirm:
            errors["confirm_password"] = "Passwords do not match."
        if not errors:
            user = UserAccount(full_name=values["full_name"], email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            db.session.add(AuditEvent(action="USER SIGNUP", resource_id=None, actor_role="user"))
            db.session.commit()
            current_app.logger.info("USER SIGNUP account_id=%s", user.id)
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("auth.user_login"))
    return render_template("user_signup.html", errors=errors, values=values), (400 if errors else 200)


@auth_bp.route("/user/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def user_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password", "")
        user = UserAccount.query.filter(func.lower(UserAccount.email) == email).first() if email and len(password) <= 256 else None
        if not user or not check_password_hash(user.password_hash, password):
            current_app.logger.warning("USER LOGIN FAILURE")
            flash("Invalid username/email or password.", "error")
            return render_template("user_login.html", email=email), 401
        response = redirect(url_for("resources.user_dashboard"))
        issue_tokens(response, user, "user")
        db.session.add(AuditEvent(action="USER LOGIN", resource_id=None, actor_role="user"))
        db.session.commit()
        current_app.logger.info("USER LOGIN account_id=%s", user.id)
        return response
    return render_template("user_login.html", email="")


@auth_bp.post("/user/logout")
def user_logout():
    revoke_from_cookie()
    session.clear()
    response = redirect(url_for("auth.user_login"))
    clear_auth(response)
    flash("You have been signed out.", "success")
    return response


@auth_bp.post("/user/refresh")
@jwt_required(refresh=True)
def user_refresh():
    access, error = refresh_user_session(touch=request.headers.get("X-User-Activity") == "1")
    if error:
        revoke_from_cookie()
        response = current_app.make_response(("Session expired", 401))
        clear_auth(response)
        return response
    response = current_app.make_response({"ok": True})
    from flask_jwt_extended import set_access_cookies
    set_access_cookies(response, access)
    return response


@auth_bp.get("/user/renew")
@jwt_required(refresh=True)
def user_renew():
    claims = get_jwt()
    if claims.get("role") != "user":
        return "Forbidden", 403
    auth_row, issue = get_active_session(claims, "user", touch=True)
    if issue:
        return redirect(url_for("auth.user_login"))
    access = create_access_token(identity=str(get_jwt_identity()), additional_claims={"role": "user", "sid": auth_row.id})
    target = request.args.get("next", "")
    if not target.startswith("/user/") or target.startswith("//"):
        target = url_for("resources.user_dashboard")
    response = redirect(target)
    set_access_cookies(response, access)
    return response
