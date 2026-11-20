
import email

from flask import jsonify, request, g

from app.models import User
from app.auth.decorators import role_required
from app.tenants import tenants


@tenants.route("/search", methods=["GET"])
@role_required("landlord")
def search_tenant():

    # Read the email from the URL query parameter.
    email = request.args.get("email", "")

    # Validate the email input.
    if not email or not email.strip():
        return jsonify({
            "error": "Tenant email is required."
        }), 400

    email = email.strip()

    # Validate basic email structure.
    if (
       email.count("@") != 1
       or email.startswith("@")
       or email.endswith("@")
       or "." not in email.split("@")[1]
    ):

     return jsonify({
        "error": "Invalid email address."
    }), 400

    # Search only for active tenant accounts.
    tenant = User.query.filter_by(
        email=email,
        role="tenant",
        is_active=True
    ).first()

    # Return an error if no matching tenant exists.
    if not tenant:
        return jsonify({
            "error": "No active tenant found with this email."
        }), 404

    # Return safe tenant information.
    return jsonify({
        "tenant": {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "phone": tenant.phone
        }
    }), 200


@tenants.route("/<int:tenant_id>", methods=["GET"])
@role_required("landlord")
def get_tenant(tenant_id):

    # Find an active user with the tenant role.
    tenant = User.query.filter_by(
        id=tenant_id,
        role="tenant",
        is_active=True
    ).first()

    # Return 404 if the tenant does not exist.
    if not tenant:
        return jsonify({
            "error": "Tenant not found."
        }), 404

    # Return safe tenant information.
    return jsonify({
        "tenant": {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "email": tenant.email,
            "phone": tenant.phone,
            "created_at": tenant.created_at.isoformat()
        }
    }), 200
