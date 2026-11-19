
from flask import Blueprint, jsonify, g
from flask import request


from app.auth.ownership import get_landlord_property
from app.auth.decorators import login_required, role_required


rbac_test = Blueprint("rbac_test", __name__, url_prefix="/test")


@rbac_test.route("/protected", methods=["GET"])
@login_required
def protected_route():

    return jsonify({
        "message": "You are authenticated!",
        "user": g.current_user.full_name,
        "role": g.current_user.role
    }), 200


@rbac_test.route("/landlord", methods=["GET"])
@role_required("landlord")
def landlord_route():

    return jsonify({
        "message": "Welcome to the landlord area!"
    }), 200


@rbac_test.route("/tenant", methods=["GET"])
@role_required("tenant")
def tenant_route():

    return jsonify({
        "message": "Welcome to the tenant area!"
    }), 200


@rbac_test.route("/maintenance", methods=["GET"])
@role_required("maintenance_staff")
def maintenance_route():

    return jsonify({
        "message": "Welcome to the maintenance area!"
    }), 200
    
    
@rbac_test.route("/properties/<int:property_id>", methods=["GET"])
@role_required("landlord")
def test_property_ownership(property_id):

    # Get the currently authenticated landlord.
    current_user = g.current_user

    # Find the property only if it belongs to this landlord.
    property = get_landlord_property(
        property_id,
        current_user.id
    )

    # If the property does not belong to this landlord,
    # return an access denied response.
    if not property:
        return jsonify({
            "error": "Property not found or access denied."
        }), 404

    return jsonify({
        "message": "Property access granted.",
        "property": {
            "id": property.id,
            "property_name": property.property_name,
            "city": property.city,
            "landlord_id": property.landlord_id
        }
    }), 200
