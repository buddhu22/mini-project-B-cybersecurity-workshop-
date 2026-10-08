from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

from flask import abort, current_app, redirect, request, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token, get_jwt, get_jwt_identity, jwt_required, set_access_cookies, set_refresh_cookies, unset_jwt_cookies

from extensions import db
from models import AdminAccount, AuthSession, UserAccount


def utc_now():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def issue_tokens(response, principal, role):
    sid = str(uuid4())
    identity = str(principal.id)
    claims = {"role": role, "sid": sid}
    access = create_access_token(identity=identity, additional_claims=claims)
    refresh = create_refresh_token(identity=identity, additional_claims=claims)
    refresh_jti = decode_token(refresh)["jti"]
    db.session.add(AuthSession(id=sid, role=role, principal_id=principal.id, refresh_jti=refresh_jti, last_activity=utc_now()))
    db.session.commit()
    set_access_cookies(response, access)
    set_refresh_cookies(response, refresh)
    return response


def clear_auth(response):
    unset_jwt_cookies(response)
    return response


def revoke_from_cookie():
    token = request.cookies.get(current_app.config["JWT_REFRESH_COOKIE_NAME"])
    if not token:
        return
    try:
        claims = decode_token(token, allow_expired=True)
        session_row = db.session.get(AuthSession, claims.get("sid"))
        if session_row and not session_row.revoked_at:
            session_row.revoked_at = utc_now()
            db.session.commit()
    except Exception:
        db.session.rollback()


def get_active_session(claims, role, touch=True):
    row = db.session.get(AuthSession, claims.get("sid"))
    if not row or row.revoked_at or row.role != role:
        return None, "invalid"
    if touch:
        row.last_activity = utc_now()
        db.session.commit()
    return row, None


def role_required(role):
    def decorate(view):
        @wraps(view)
        @jwt_required()
        def wrapped(*args, **kwargs):
            claims = get_jwt()
            if claims.get("role") != role:
                abort(403)
            session_row, issue = get_active_session(claims, role)
            if issue:
                return clear_auth(redirect(url_for("admin.login" if role == "admin" else "auth.user_login")))
            principal_id = int(get_jwt_identity())
            principal_model = UserAccount if role == "user" else AdminAccount
            principal = db.session.get(principal_model, principal_id)
            if not principal:
                return clear_auth(redirect(url_for("admin.login" if role == "admin" else "auth.user_login")))
            request.auth_principal = principal
            request.auth_session = session_row
            return view(*args, **kwargs)
        return wrapped
    return decorate


def refresh_user_session(touch=True):
    claims = get_jwt()
    if claims.get("role") != "user":
        return None, ("Unauthorized", 403)
    row, issue = get_active_session(claims, "user", touch=touch)
    if issue:
        return None, ("Session expired", 401)
    user = db.session.get(UserAccount, int(get_jwt_identity()))
    if not user:
        return None, ("Unauthorized", 401)
    access = create_access_token(identity=str(user.id), additional_claims={"role": "user", "sid": row.id})
    return access, None
