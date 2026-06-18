"""
Role-based access-control decorators.
"""

from functools import wraps
from flask import abort
from flask_login import current_user


def roles_required(*roles):
    """
    Restrict a view to users holding at least one of the given roles.
    Usage: @roles_required("Admin")  or  @roles_required("Admin", "HOD")
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not any(current_user.has_role(r) for r in roles):
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped
    return decorator
