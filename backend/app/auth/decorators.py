from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def role_required(*allowed_roles):
    """
    Decorator to restrict route access by role stored in JWT claims.
    Usage:
        @auth_bp.get("/admin-only")
        @role_required("admin")
        def admin_view():
            ...
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            # Verify JWT is present and valid
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": "Access denied: insufficient permissions"
                }), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper