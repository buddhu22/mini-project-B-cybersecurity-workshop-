from datetime import datetime, timezone

from extensions import db


class Session(db.Model):
    __tablename__ = "workshop_sessions"
    __table_args__ = (db.UniqueConstraint("day", "sort_order", name="uq_day_session_order"),)
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    day = db.Column(db.String(10), nullable=False, index=True)
    time_slot = db.Column(db.String(40), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    resources = db.relationship("Resource", backref="workshop_session", primaryjoin="and_(Session.title == foreign(Resource.session_title), Session.day == foreign(Resource.day), Session.time_slot == foreign(Resource.time_slot))", cascade="all, delete-orphan", lazy=True)


class Resource(db.Model):
    __tablename__ = "resources"
    id = db.Column(db.Integer, primary_key=True)
    session_title = db.Column(db.String(200), nullable=False)
    day = db.Column(db.String(10), nullable=False, index=True)
    time_slot = db.Column(db.String(40), nullable=False)
    resource_type = db.Column(db.String(30), nullable=False, index=True)
    description = db.Column(db.String(1000), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    prerequisite = db.Column(db.String(500), nullable=False)
    resource_review_status = db.Column(db.String(30), nullable=False, default="Not Reviewed")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(20), nullable=False)
    resource_id = db.Column(db.Integer, nullable=True)
    actor_role = db.Column(db.String(20), nullable=False, default="admin")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class UserAccount(db.Model):
    __tablename__ = "user_accounts"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AdminAccount(db.Model):
    __tablename__ = "admin_accounts"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AuthSession(db.Model):
    __tablename__ = "auth_sessions"
    id = db.Column(db.String(36), primary_key=True)
    role = db.Column(db.String(10), nullable=False, index=True)
    principal_id = db.Column(db.Integer, nullable=False)
    refresh_jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    last_activity = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
