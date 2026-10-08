# Security test report

Executed using pytest with an isolated SQLite database. The full automated test suite is in tests/.

| Test case | Input / action | Expected result | Actual result | Status |
|---|---|---|---|---|
| User signup | Valid name/email and strong matching password | Create account with password hash | Account created; stored value verifies as a hash, not plaintext | PASS |
| User login | Valid email/password | Issue access and refresh JWT cookies | Redirected to user dashboard; both cookies are HttpOnly | PASS |
| Invalid user login | Existing email with wrong password | Generic failure message | Generic login error returned | PASS |
| User JWT creation | Inspect access token claims | Minimal subject/role/session claims | Role is user; no password/hash/profile fields | PASS |
| User protected route | Request dashboard without and with user JWT | Redirect unauthenticated; allow authenticated user | Protected; authenticated user receives 200 | PASS |
| Admin login | Provisioned username/password | Issue admin JWT and redirect | Redirected to admin dashboard; role claim admin | PASS |
| Invalid admin login | Unknown username/password | Generic failure | Generic login error returned | PASS |
| Admin JWT creation | Inspect admin access claims | Role admin | Admin role verified | PASS |
| User attempts admin route | User JWT requests /admin/dashboard | 403 Forbidden | HTTP 403 | PASS |
| Admin access | Admin JWT requests admin dashboard/resources/audit | Allow | HTTP 200 | PASS |
| User logout | POST with CSRF token | Revoke session and clear both JWT cookies | Cookies cleared; AuthSession.revoked_at set | PASS |
| Admin logout | POST with CSRF token | Revoke and clear admin session | Cookies cleared; redirected to admin login | PASS |
| Expired access token | Expired access plus valid refresh | Renew access and continue | Renewal route set new access cookie and returned to dashboard | PASS |
| Participant login portal timeout | Load login page | Configure a five-minute client inactivity timeout and show a timeout message | Login page declares 300 seconds and timeout message | PASS |
| Post-login inactivity | Set activity older than 30 minutes | Keep protected dashboard available without inactivity logout | Dashboard remains available; no countdown or warning rendered | PASS |
| Refresh token | Authenticated refresh POST | Issue new access token | New HttpOnly access cookie returned | PASS |
| Admin refresh token | Admin refresh POST | Keep admin session and renew access token | New HttpOnly admin access cookie returned | PASS |
| Password hashing | Register strong test password | Persist only a secure hash | check_password_hash succeeds; plaintext differs | PASS |
| XSS-looking input | Script-shaped text in account name | Render as escaped text | Encoded HTML shown; no executable script markup | PASS |
| SQL injection-looking input | ' OR '1'='1 search term | No query alteration | ORM search returned no unintended records | PASS |
| Malicious URL scheme | javascript:alert(1) | Reject without fetching | Admin form returned validation error; no record saved | PASS |
| CSRF protection | POST signup without token | Reject state-changing request | HTTP 400 CSRF failure | PASS |
| Oversized password | Signup password longer than 256 characters | Reject before expensive hashing | Validation error returned | PASS |

Additional live checks against the local app: root portal returned 200 and displayed both choices; participant signup/login and dashboard succeeded; user JWT was HttpOnly and received 403 on admin dashboard; admin login/dashboard/logout succeeded.

Command: python -m pytest -q  
Result: **32 passed, 0 failed.**

The in-memory Flask-Limiter emits a deployment warning because it is intended for local coursework use. This suite is not a penetration test or production security certification.
