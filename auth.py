"""
Admin authentication — single admin, password + Flask session.

Credentials come from the environment:
  ADMIN_USERNAME       (default: "admin")
  ADMIN_PASSWORD_HASH  a werkzeug password hash (preferred)
  ADMIN_PASSWORD       plaintext fallback for local dev only

Generate a hash with:
  python -c "from werkzeug.security import generate_password_hash as g; print(g('yourpassword'))"
"""

import os
from functools import wraps

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def _admin_username():
    return os.getenv("ADMIN_USERNAME", "admin")


def _password_ok(password):
    """Validate a submitted password against the configured hash/plaintext."""
    pw_hash = os.getenv("ADMIN_PASSWORD_HASH")
    if pw_hash:
        return check_password_hash(pw_hash, password)

    # Dev fallback: plaintext env var, or a default so local login works.
    plain = os.getenv("ADMIN_PASSWORD", "admin123")
    return password == plain


def verify_credentials(username, password):
    """True when both username and password match the configured admin."""
    return username == _admin_username() and _password_ok(password)


def login_user():
    session["admin"] = True


def logout_user():
    session.pop("admin", None)


def is_logged_in():
    return bool(session.get("admin"))


def login_required(view):
    """Redirect to the login page for any unauthenticated request."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped
