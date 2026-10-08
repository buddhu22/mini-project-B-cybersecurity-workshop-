# Threat model — Secure Workshop Resource Directory

## Scope

Local educational Flask app with participant accounts, a separately provisioned administrator login, SQLite, workshop resources, and role-protected pages. This is not a production identity provider or deployment design.

## 1. Assets

- Participant email, display name, and password hash.
- Administrator username and password hash.
- Access/refresh JWTs, role claims, and revocable session rows.
- Workshop timetable, resource metadata, and packaged workshop files.
- SQLite database, audit events, Flask/JWT signing keys, and logs.

## 2. Trust boundaries

- Browser forms and query parameters enter the app as untrusted input.
- The browser receives signed JWT cookies; HttpOnly prevents page JavaScript from reading them.
- Flask-WTF validates CSRF tokens on state-changing POST requests.
- Route decorators validate JWT signature/type/expiry/revocation and the role claim before accessing protected views.
- SQLAlchemy passes query values as parameters to SQLite.
- User content passes through Jinja autoescaping before HTML output.
- Resource URL strings are stored but never fetched by the app. Packaged files are served from a fixed local directory.
- Admin provisioning crosses the environment configuration/database boundary; there is no public admin signup.

## 3. Threat actors

- Anonymous visitor attempting account abuse, login guessing, or CSRF.
- Participant attempting to reach admin CRUD, reports, or audit data.
- Malicious participant submitting script-shaped text, SQL-looking search input, or unsafe URLs.
- Local person with access to project files, environment secrets, or the database.

## 4. Threats and mitigations

| Threat | Mitigation |
|---|---|
| Password disclosure | Werkzeug password hashing; generic login errors; no password logging or JWT claims. |
| User creates an admin account | Admin signup route does not exist. Admin accounts are provisioned only from environment configuration and stored as hashes. |
| JWT theft through browser script | Access/refresh JWTs use HttpOnly cookies and are never written to Web Storage or exposed to JavaScript. Jinja escaping and a restrictive CSP reduce script injection risk. |
| User JWT accesses admin | Protected routes require the admin role claim and a live admin session row; user-role token requests return 403. |
| Replay of revoked/expired sessions | JWT expiration checks plus server-side refresh-session records and revocation at logout. |
| CSRF against cookie-authenticated actions | Flask-WTF CSRF tokens are required for POST forms and same-origin AJAX refresh/logout requests. SameSite=Lax is also set. |
| Brute force | Login/signup endpoints are rate-limited and failures log only a generic action, never the submitted password. The default limiter storage is process-local. |
| Stale participant login portal | The unauthenticated participant login form is disabled after five minutes without activity and displays a timeout message. |
| Stored/reflected XSS | Jinja autoescaping remains enabled; untrusted values are never marked safe; CSP disallows inline scripts. |
| SQL injection | SQLAlchemy ORM filters use parameter binding; no SQL string concatenation with user input. |
| Dangerous URL schemes or SSRF | URL validation restricts to HTTP(S) with a host or an allowlisted packaged local filename. The application never visits submitted URLs. |
| Sensitive information in audit data | Audit events contain role, action, timestamp, and resource id only. No form bodies, password, JWT, or key is logged. |
| Secret leakage/insecure cookie deployment | .env is ignored; examples contain placeholders. Cookies are HttpOnly/SameSite and Secure when production mode is selected; production requires HTTPS and strong unique secrets. |

## 5. Residual risks

The local dev server, SQLite, and in-memory rate limiter are not suitable for public multi-process deployment. An administrator with environment and database access controls the app. Secure cookies are off in local HTTP development. Production requires HTTPS, secret management, persistent rate-limit storage, deployment hardening, backups, and operational monitoring.
