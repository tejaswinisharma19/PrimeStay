from flask import Blueprint, jsonify, request, session
from app.auth.service import register_user, authenticate_user
from app.models import User
from flask import Blueprint


from app.extensions import db


auth = Blueprint(
    "auth",
    __name__,
    url_prefix="/auth"
)


@auth.route("/register", methods=["POST"])
def register():

    # 1. Receive JSON data from the client.
    data = request.get_json(silent=True)

    # 2. Check whether valid JSON was provided.
    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    # 3. Extract registration fields.
    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")
    role = data.get("role")

    # 4. Validate the data types.
    if not all(
        isinstance(value, str)
        for value in [full_name, email, password, role]
    ):
        return jsonify({
            "error": "Full name, email, password and role must be strings."
        }), 400

    if phone is not None and not isinstance(phone, str):
        return jsonify({
            "error": "Phone must be a string."
        }), 400

    # 5. Call our registration service.
    user, error = register_user(
        full_name=full_name,
        email=email,
        password=password,
        phone=phone,
        role=role
    )

    # 6. Handle registration errors.
    if error:

        status_code = (
            409
            if error == "An account with this email already exists."
            else 400
        )

        return jsonify({
            "error": error
        }), status_code

    # 7. Return successful registration response.
    return jsonify({
        "message": "Account created successfully.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }), 201


@auth.route("/login", methods=["POST"])
def login():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    email = data.get("email")
    password = data.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({
            "error": "Email and password must be strings."
        }), 400

    user, error = authenticate_user(email, password)

    if error:
        return jsonify({
            "error": error
        }), 401

    # Clear any previous session data.
    session.clear()

    # Store the authenticated user's ID.
    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }), 200


@auth.route("/me", methods=["GET"])
def get_current_user():

    # Check whether a user ID exists in the session.
    user_id = session.get("user_id")

    # If no user is logged in, return 401.
    if not user_id:
        return jsonify({
            "error": "Authentication required."
        }), 401

    # Find the user using the ID stored in the session.
    user = db.session.get(User, user_id)

    # Check whether the account still exists and is active.
    if not user or not user.is_active:
        session.clear()

        return jsonify({
            "error": "User account not found or inactive."
        }), 401

    # Return safe user information.
    return jsonify({
        "authenticated": True,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        }
    }), 200


@auth.route("/logout", methods=["POST"])
def logout():

    # Remove all data stored in the current session.
    session.clear()

    return jsonify({
        "message": "Logout successful."
    }), 200
