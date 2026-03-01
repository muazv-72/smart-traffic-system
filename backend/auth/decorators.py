from functools import wraps

from flask import redirect, session, url_for


# Security Decorator: Protects routes from unauthenticated users
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper
