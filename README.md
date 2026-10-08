# Secure Workshop Resource Directory

A Flask application for the six-day workshop timetable and its supplied learning materials. Visitors first choose the participant or administrator portal. Participants create an account or sign in; administrator credentials are provisioned from environment variables. User and admin actions are authorized on the server with role-bearing JWTs in HttpOnly cookies.

## Features

- Public authentication landing page at /, then separate user and admin login flows.
- Participant signup, email/password login, password hashing, refreshable access tokens, logout revocation, and a five-minute inactivity timeout on the login portal.
- Separate administrator login with no public admin signup; admin-only dashboard, resource CRUD, reports, settings, and audit logs.
- Protected session timetable, resource search/filter/detail, and filtered CSV export for signed-in participants.
- Exact 11-session workshop timetable, with the two Day 5 Mini-Project slots retained separately.
- Provided workshop documents served locally from resources/; the application never fetches submitted URLs.
- Input validation, Jinja autoescaping, SQLAlchemy ORM filters, CSRF protection, login rate limits, audit events, and security headers.

## Architecture and stack

Python 3.11+, Flask, Flask-SQLAlchemy / SQLAlchemy, SQLite, Jinja2, Flask-JWT-Extended, Flask-WTF, Flask-Limiter, python-dotenv, and pytest. Blueprints separate authentication, participant resources/sessions, and administration. User and admin JWTs carry only an account subject, role, session id, and standard JWT claims. Database session rows track refresh-token revocation and participant activity.

## Project structure

~~~text
app.py, config.py, extensions.py, models.py, validators.py, auth_helpers.py
routes/             public/user/admin route groups
templates/          public portals, user pages, admin pages, forms
static/css/          responsive portal styles
static/js/           login-portal inactivity timeout and admin cookie refresh (never reads JWTs)
data/                timetable and provided-resource seeding
resources/           supplied workshop PDFs and slide deck
tests/               authentication, authorization, resource, and security tests
docs/                threat model and test report
logs/                rotating audit log
~~~

## Installation and configuration

From the project directory in PowerShell:

~~~powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env
~~~

Before first initialization, edit .env and set strong, private values for FLASK_SECRET_KEY, FLASK_JWT_SECRET_KEY, ADMIN_USERNAME, and ADMIN_PASSWORD. ADMIN_PASSWORD is hashed with Werkzeug before the admin account is saved. .env is ignored by Git. Example values are placeholders for local setup only. If no admin environment values are configured, no administrator account is created. An existing admin password is not overwritten on every startup; change/reset it through controlled database administration.

Token lifetimes are configurable:

~~~text
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=1
~~~

Cookies are HttpOnly and SameSite=Lax. Secure is enabled when FLASK_ENV=production; production must use HTTPS and strong secrets. SQLite defaults to the project workshop.db.

## Initialize data and run

~~~powershell
python data/seed_resources.py
python app.py
~~~

Initialization creates/migrates the SQLite schema, seeds all 11 timetable entries and the provided resource references, and provisions the first admin from environment configuration. Open http://127.0.0.1:5000/.

### Deploy on Render

Create a Python Web Service connected to this repository. Use `pip install -r requirements.txt` as the build command and `gunicorn app:app` as the start command. Render startup initializes the database schema, workshop seed data, and first administrator from environment variables.

Set `FLASK_SECRET_KEY`, `FLASK_JWT_SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` in the Render service environment. SQLite on Render is ephemeral by default, so use Render Postgres or a persistent disk if participant accounts and admin changes must survive restarts and deployments.

### Portal URLs

- Landing page: /  
- Participant choice page: /user/auth  
- Participant login: /user/login  
- Participant signup: /user/signup  
- Participant dashboard: /user/dashboard  
- Administrator login: /admin/login  
- Administrator dashboard: /admin/dashboard

There is no /admin/signup route and no role dropdown. Admin credentials are configured through environment variables and saved as a password hash.

## Authentication and authorization

- werkzeug.security password hashing protects participant and administrator passwords.
- Flask-JWT-Extended creates signed access and refresh tokens. Tokens are placed only in HttpOnly cookies named workshop_access_token and workshop_refresh_token, never browser storage.
- The role claim must match each protected blueprint. A user token receives HTTP 403 on admin pages.
- Refresh-session records hold a refresh JTI, role, account id, last activity, and revocation timestamp. Logout revokes the associated session and clears cookies.
- Access tokens last 15 minutes; refresh tokens last one day by default. Browser requests renew access tokens through refresh routes. A valid refresh token can renew an expired access token.
- The participant login portal times out after five minutes without activity and displays a timeout message. Once signed in, the participant dashboard has no inactivity countdown or inactivity-based logout. Access/refresh token lifetimes still apply, and browser requests renew access tokens through the refresh route.
- Flask-WTF CSRF tokens protect every POST form and AJAX POST. Login endpoints are rate-limited to five requests per minute per client IP. The default rate-limit store is in-memory for this local prototype.

## Participant resource features

Signed-in participants can browse the timetable, search and filter resources by day/type/session, view details, open supplied/local or HTTP(S) links, and export the currently filtered directory as CSV. Participants cannot create, update, or delete resources. The admin dashboard provides resource counts by day/type, review status totals, recent activity, and protected CRUD.

## Security controls and audit

- Required fields, lengths, supported resource types/days, and URL schemes are checked on the server.
- Arbitrary user URLs are never requested. Only HTTP(S) URLs and allowlisted packaged local resource paths are accepted.
- Jinja autoescaping is used for user data; user-controlled values are not marked safe.
- Search/filter uses SQLAlchemy ORM expressions, not SQL string construction.
- Security headers include a restrictive Content Security Policy, frame denial, MIME sniffing protection, and referrer policy.
- Audit database rows and logs/audit.log contain action/actor/resource identifiers only. Passwords, JWTs, secrets, and full form contents are excluded.

See docs/threat-model.md and docs/test-report.md.

## Run tests

~~~powershell
python -m pytest -q
~~~

Tests use an isolated SQLite database and temporary test accounts. No network scanning or real penetration testing is performed.

## Known limits and safe use

- The local Flask server and SQLite are for coursework, not public deployment.
- Flask-Limiter uses in-memory counters by default; configure a shared persistent storage backend for a multi-process deployment.
- Admin credentials are provisioned from environment at initial setup. There is no public registration or password reset UI.
- Use trusted, non-sensitive resource references. Never enter real personal data or share .env.
- Secure cookies require HTTPS in production; do not expose the development server directly to the internet.
