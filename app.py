import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_jwt
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

load_dotenv()

from config import Config
from extensions import csrf, db, jwt, limiter
from models import AdminAccount, AuthSession
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.main import main_bp
from routes.resources import resources_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config.get("FLASK_ENV") == "production" and (
        len(app.config.get("SECRET_KEY", "")) < 32
        or len(app.config.get("JWT_SECRET_KEY", "")) < 32
        or app.config.get("SECRET_KEY") == "local-development-only-change-me"
    ):
        raise RuntimeError("Production requires unique secret keys of at least 32 characters.")
    if app.testing:
        app.config["RATELIMIT_ENABLED"] = False
    db.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(admin_bp)

    @app.get("/provided-resources/<path:filename>")
    def provided_resource(filename):
        resource_dir = Path(app.root_path) / "resources"
        allowed = {path.name for path in resource_dir.iterdir() if path.is_file()}
        if filename not in allowed:
            return render_template("error.html", code=404, message="The requested resource file was not found."), 404
        return __import__("flask").send_from_directory(resource_dir, filename, as_attachment=False)

    log_dir = Path(app.instance_path).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if not app.testing and not any(isinstance(handler, RotatingFileHandler) for handler in app.logger.handlers):
        handler = RotatingFileHandler(log_dir / "audit.log", maxBytes=256_000, backupCount=3, encoding="utf-8")
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403, message="This account does not have permission to access that page."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="The requested page was not found."), 404

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @jwt.token_in_blocklist_loader
    def token_revoked(_header, claims):
        row = db.session.get(AuthSession, claims.get("sid"))
        if not row or row.revoked_at:
            return True
        return False

    def jwt_failure(message, status=401):
        destination = "admin.login" if request.path.startswith("/admin") else "auth.user_login"
        response = app.make_response(redirect(url_for(destination)))
        from auth_helpers import clear_auth
        clear_auth(response)
        return response

    @jwt.expired_token_loader
    def expired_token(_header, claims):
        if claims.get("type") == "access":
            path = request.full_path.removesuffix("?")
            if claims.get("role") == "user" and request.path.startswith("/user/"):
                return redirect(url_for("auth.user_renew", next=path))
            if claims.get("role") == "admin" and request.path.startswith("/admin/"):
                return redirect(url_for("admin.renew", next=path))
        return jwt_failure("Token expired")

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jwt_failure("Invalid token")

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jwt_failure("Missing token")

    @jwt.revoked_token_loader
    def revoked_token(_header, claims):
        return jwt_failure("Revoked token")

    return app


app = create_app()


def initialize_database():
    """Create schema, migrate the earlier timetable schema, and seed local records."""
    inspector = inspect(db.engine)
    if inspector.has_table("workshop_sessions"):
        constraints = inspector.get_unique_constraints("workshop_sessions")
        if any(item.get("column_names") == ["title"] for item in constraints):
            with db.engine.begin() as connection:
                connection.execute(text("CREATE TABLE workshop_sessions_new (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(200) NOT NULL, day VARCHAR(10) NOT NULL, time_slot VARCHAR(40) NOT NULL, sort_order INTEGER NOT NULL, CONSTRAINT uq_day_session_order UNIQUE (day, sort_order))"))
                connection.execute(text("INSERT INTO workshop_sessions_new (id, title, day, time_slot, sort_order) SELECT id, title, day, time_slot, sort_order FROM workshop_sessions"))
                connection.execute(text("DROP TABLE workshop_sessions"))
                connection.execute(text("ALTER TABLE workshop_sessions_new RENAME TO workshop_sessions"))
    db.create_all()
    from data.seed_resources import seed_resources
    seed_resources()
    username, password = app.config.get("ADMIN_USERNAME"), app.config.get("ADMIN_PASSWORD")
    if username and password and not AdminAccount.query.filter_by(username=username).first():
        db.session.add(AdminAccount(username=username, password_hash=generate_password_hash(password)))
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        initialize_database()
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
