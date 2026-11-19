from functools import wraps

from flask import jsonify, session, g

from app.extensions import db
from app.models import User


def login_required(view_function):
    """
    Allow access only to authenticated users.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        # Get the user ID from the session.
        user_id = session.get("user_id")

        # Reject requests without a login session.
        if not user_id:
            return jsonify({
                "error": "Authentication required."
            }), 401

        # Find the user in the database.
        user = db.session.get(User, user_id)

        # Reject missing or inactive accounts.
        if not user or not user.is_active:
            session.clear()

            return jsonify({
                "error": "Authentication required."
            }), 401

        # Make the current user available to the route.
        g.current_user = user

        return view_function(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    """
    Allow access only to users with specified roles.
    """

    def decorator(view_function):

        @wraps(view_function)
        @login_required
        def wrapped_view(*args, **kwargs):

            # Get the authenticated user.
            current_user = g.current_user

            # Check whether their role is permitted.
            if current_user.role not in allowed_roles:
                return jsonify({
                    "error": "You do not have permission to access this resource."
                }), 403

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator