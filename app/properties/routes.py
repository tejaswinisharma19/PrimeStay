
from flask import jsonify, request, g

from app.extensions import db
from app.models import Property
from app.auth.decorators import role_required
from app.properties import properties



@properties.route("", methods=["POST"])
@role_required("landlord")
def create_property():

    # 1. Receive JSON data.
    data = request.get_json(silent=True)

    # 2. Check whether a valid JSON object was provided.
    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    # 3. Define the required fields.
    required_fields = [
        "property_name",
        "property_type",
        "address_line",
        "city",
        "state",
        "postal_code"
    ]

    # 4. Check for missing or empty required fields.
    for field in required_fields:

        value = data.get(field)

        if not isinstance(value, str) or not value.strip():
            return jsonify({
                "error": f"{field} is required and must be a non-empty string."
            }), 400

    # 5. Extract and clean the text fields.
    property_name = data["property_name"].strip()
    property_type = data["property_type"].strip().lower()
    address_line = data["address_line"].strip()
    city = data["city"].strip()
    state = data["state"].strip()
    postal_code = data["postal_code"].strip()

    # 6. Validate property type.
    if property_type not in ["apartment", "house"]:
        return jsonify({
            "error": "Property type must be apartment or house."
        }), 400

    # 7. Validate maximum field lengths.
    if len(property_name) > 150:
        return jsonify({
            "error": "Property name cannot exceed 150 characters."
        }), 400

    if len(address_line) > 255:
        return jsonify({
            "error": "Address cannot exceed 255 characters."
        }), 400

    if len(city) > 100 or len(state) > 100:
        return jsonify({
            "error": "City and state cannot exceed 100 characters."
        }), 400

    if len(postal_code) > 10:
        return jsonify({
            "error": "Postal code cannot exceed 10 characters."
        }), 400

    # 8. Validate optional numeric fields.
    bedrooms = data.get("bedrooms")
    bathrooms = data.get("bathrooms")

    for field, value in [
        ("bedrooms", bedrooms),
        ("bathrooms", bathrooms)
    ]:

        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int):
                return jsonify({
                    "error": f"{field} must be a whole number."
                }), 400

            if value < 0:
                return jsonify({
                    "error": f"{field} cannot be negative."
                }), 400

    # 9. Validate optional description.
    description = data.get("description")

    if description is not None:
        if not isinstance(description, str):
            return jsonify({
                "error": "Description must be a string."
            }), 400

        description = description.strip()

    # 10. Create the property.
    new_property = Property(
        landlord_id=g.current_user.id,
        property_name=property_name,
        property_type=property_type,
        address_line=address_line,
        city=city,
        state=state,
        postal_code=postal_code,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        description=description
    )

    # 11. Save the property in PostgreSQL.
    try:
        db.session.add(new_property)
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Unable to create property. Please try again."
        }), 500

    # 12. Return the created property.
    return jsonify({
        "message": "Property created successfully.",
        "property": {
            "id": new_property.id,
            "landlord_id": new_property.landlord_id,
            "property_name": new_property.property_name,
            "property_type": new_property.property_type,
            "address_line": new_property.address_line,
            "city": new_property.city,
            "state": new_property.state,
            "postal_code": new_property.postal_code,
            "bedrooms": new_property.bedrooms,
            "bathrooms": new_property.bathrooms,
            "description": new_property.description,
            "is_active": new_property.is_active
        }
    }), 201
    
    


@properties.route("", methods=["GET"])
@role_required("landlord")
def get_properties():

    # Get the logged-in landlord's ID.
    landlord_id = g.current_user.id

    # Read the optional status query parameter.
    status = request.args.get("status", "active").lower()

    # Start with properties belonging to this landlord.
    query = Property.query.filter_by(
        landlord_id=landlord_id
    )

    # Filter properties based on the requested status.
    if status == "active":
        query = query.filter_by(is_active=True)

    elif status == "inactive":
        query = query.filter_by(is_active=False)

    elif status == "all":
        pass

    else:
        return jsonify({
            "error": "Invalid status. Use active, inactive, or all."
        }), 400

    # Retrieve properties, newest first.
    property_list = query.order_by(
        Property.created_at.desc()
    ).all()

    # Convert database records into JSON.
    properties_data = []

    for property in property_list:
        properties_data.append({
            "id": property.id,
            "property_name": property.property_name,
            "property_type": property.property_type,
            "address_line": property.address_line,
            "city": property.city,
            "state": property.state,
            "postal_code": property.postal_code,
            "bedrooms": property.bedrooms,
            "bathrooms": property.bathrooms,
            "description": property.description,
            "is_active": property.is_active,
            "created_at": property.created_at.isoformat()
        })

    return jsonify({
        "count": len(properties_data),
        "properties": properties_data
    }), 200

@properties.route("/<int:property_id>", methods=["GET"])
@role_required("landlord")
def get_property(property_id):

    # Retrieve the property only if it belongs to the logged-in landlord.
    property = Property.query.filter_by(
        id=property_id,
        landlord_id=g.current_user.id
    ).first()

    # Return 404 if the property does not exist or belongs to another landlord.
    if not property:
        return jsonify({
            "error": "Property not found."
        }), 404

    # Return the property details.
    return jsonify({
        "property": {
            "id": property.id,
            "property_name": property.property_name,
            "property_type": property.property_type,
            "address_line": property.address_line,
            "city": property.city,
            "state": property.state,
            "postal_code": property.postal_code,
            "bedrooms": property.bedrooms,
            "bathrooms": property.bathrooms,
            "description": property.description,
            "is_active": property.is_active,
            "created_at": property.created_at.isoformat(),
            "updated_at": property.updated_at.isoformat()
        }
    }), 200

@properties.route("/<int:property_id>", methods=["PATCH"])
@role_required("landlord")
def update_property(property_id):

    # Find the property belonging to the logged-in landlord.
    property = Property.query.filter_by(
        id=property_id,
        landlord_id=g.current_user.id
    ).first()

    if not property:
        return jsonify({
            "error": "Property not found."
        }), 404

    # Receive JSON data.
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    if not data:
        return jsonify({
            "error": "At least one field must be provided."
        }), 400

    # Define the fields that can be updated.
    allowed_fields = {
        "property_name",
        "property_type",
        "address_line",
        "city",
        "state",
        "postal_code",
        "bedrooms",
        "bathrooms",
        "description"
    }

    # Reject unknown fields.
    unknown_fields = set(data.keys()) - allowed_fields

    if unknown_fields:
        return jsonify({
            "error": "Unsupported fields: " + ", ".join(sorted(unknown_fields))
        }), 400

    # Validate text fields.
    text_limits = {
        "property_name": 150,
        "address_line": 255,
        "city": 100,
        "state": 100,
        "postal_code": 10
    }

    for field, max_length in text_limits.items():

        if field in data:
            value = data[field]

            if not isinstance(value, str) or not value.strip():
                return jsonify({
                    "error": f"{field} must be a non-empty string."
                }), 400

            if len(value.strip()) > max_length:
                return jsonify({
                    "error": f"{field} cannot exceed {max_length} characters."
                }), 400

    # Validate property type.
    if "property_type" in data:

        property_type = data["property_type"]

        if not isinstance(property_type, str):
            return jsonify({
                "error": "Property type must be a string."
            }), 400

        property_type = property_type.strip().lower()

        if property_type not in ["apartment", "house"]:
            return jsonify({
                "error": "Property type must be apartment or house."
            }), 400

        data["property_type"] = property_type

    # Validate bedroom and bathroom counts.
    for field in ["bedrooms", "bathrooms"]:

        if field in data:

            value = data[field]

            if isinstance(value, bool) or not isinstance(value, int):
                return jsonify({
                    "error": f"{field} must be a whole number."
                }), 400

            if value < 0:
                return jsonify({
                    "error": f"{field} cannot be negative."
                }), 400

    # Validate description.
    if "description" in data:

        if data["description"] is not None and not isinstance(
            data["description"], str
        ):
            return jsonify({
                "error": "Description must be a string or null."
            }), 400

        if isinstance(data["description"], str):
            data["description"] = data["description"].strip()

    # Apply the validated changes.
    for field in data:
        value = data[field]

        if isinstance(value, str):
            value = value.strip()

        setattr(property, field, value)

    # Save changes to PostgreSQL.
    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Unable to update property. Please try again."
        }), 500

    # Return updated property information.
    return jsonify({
        "message": "Property updated successfully.",
        "property": {
            "id": property.id,
            "property_name": property.property_name,
            "property_type": property.property_type,
            "address_line": property.address_line,
            "city": property.city,
            "state": property.state,
            "postal_code": property.postal_code,
            "bedrooms": property.bedrooms,
            "bathrooms": property.bathrooms,
            "description": property.description,
            "is_active": property.is_active
        }
    }), 200

@properties.route("/<int:property_id>", methods=["DELETE"])
@role_required("landlord")
def delete_property(property_id):

    # Find the property belonging to the logged-in landlord.
    property = Property.query.filter_by(
        id=property_id,
        landlord_id=g.current_user.id
    ).first()

    # If the property does not exist or belongs to another landlord.
    if not property:
        return jsonify({
            "error": "Property not found."
        }), 404

    # Prevent deletion if the property is already inactive.
    if not property.is_active:
        return jsonify({
            "error": "Property is already inactive."
        }), 400

    # Soft delete: preserve the database record.
    property.is_active = False

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "error": "Unable to deactivate property. Please try again."
        }), 500

    return jsonify({
        "message": "Property deactivated successfully.",
        "property_id": property.id,
        "is_active": property.is_active
    }), 200