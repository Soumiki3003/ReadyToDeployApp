from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles: str):
    """Decorator that requires login and checks the user has one of the given roles."""

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated

    return decorator
