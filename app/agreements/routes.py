
from datetime import date

from flask import jsonify, g, request
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import RentalAgreement, Tenancy, Property
from app.auth.decorators import role_required
from app.agreements import agreements



@agreements.route("", methods=["GET"])
@role_required("landlord", "tenant")
def list_agreements():

    current_user = g.current_user

    query = (
        RentalAgreement.query
        .join(Tenancy, RentalAgreement.tenancy_id == Tenancy.id)
        .join(Property, Tenancy.property_id == Property.id)
    )

    if current_user.role == "landlord":
        query = query.filter(
            Property.landlord_id == current_user.id
        )

    elif current_user.role == "tenant":
        query = query.filter(
            Tenancy.tenant_id == current_user.id
        )

    agreements_list = query.order_by(
        RentalAgreement.created_at.desc()
    ).all()

    result = []

    for agreement in agreements_list:
        result.append({
            "id": agreement.id,
            "tenancy_id": agreement.tenancy_id,
            "agreement_number": agreement.agreement_number,
            "agreement_type": agreement.agreement_type,
            "start_date": agreement.start_date.isoformat(),
            "end_date": agreement.end_date.isoformat(),
            "signed_on": (
                agreement.signed_on.isoformat()
                if agreement.signed_on else None
            ),
            "status": agreement.status,
            "created_at": agreement.created_at.isoformat()
        })

    return jsonify({
        "success": True,
        "count": len(result),
        "agreements": result
    }), 200


@agreements.route("", methods=["POST"])
@role_required("landlord")
def create_agreement():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must contain valid JSON."
        }), 400

    # Validate required fields.
    required_fields = [
        "tenancy_id",
        "agreement_number",
        "agreement_type",
        "start_date",
        "end_date"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in data
    ]

    if missing_fields:
        return jsonify({
            "error": "Missing required fields.",
            "missing_fields": missing_fields
        }), 400

    # Validate tenancy ID.
    tenancy_id = data["tenancy_id"]

    if (
        isinstance(tenancy_id, bool)
        or not isinstance(tenancy_id, int)
        or tenancy_id <= 0
    ):
        return jsonify({
            "error": "Invalid tenancy ID."
        }), 400

    # Validate agreement number.
    agreement_number = data["agreement_number"]

    if (
        not isinstance(agreement_number, str)
        or not agreement_number.strip()
        or len(agreement_number.strip()) > 50
    ):
        return jsonify({
            "error": "Agreement number must contain 1 to 50 characters."
        }), 400

    agreement_number = agreement_number.strip()

    # Validate agreement type.
    agreement_type = data["agreement_type"]

    if agreement_type not in ("initial", "renewal"):
        return jsonify({
            "error": "Agreement type must be initial or renewal."
        }), 400

    
    # Validate dates.
    start_date_value = data["start_date"]
    end_date_value = data["end_date"]

    # Both dates must be strings.
    if (
       not isinstance(start_date_value, str)
       or not isinstance(end_date_value, str)
    ):
      return jsonify({
        "error": "Dates must use YYYY-MM-DD format."
    }), 400

    try:
     start_date = date.fromisoformat(start_date_value)
     end_date = date.fromisoformat(end_date_value)

    except ValueError:
      return jsonify({
        "error": "Dates must use YYYY-MM-DD format."
    }), 400

   # Enforce the exact YYYY-MM-DD format.
    if (
        start_date.isoformat() != start_date_value
        or end_date.isoformat() != end_date_value
   ):
      return jsonify({
        "error": "Dates must use YYYY-MM-DD format."
    }), 400
      
    # Ensure the agreement end date is not before its start date.
    if end_date < start_date:
      return jsonify({
        "error": "Agreement end date cannot precede start date."
    }), 400


    # Retrieve the tenancy and verify landlord ownership.
    tenancy = (
        Tenancy.query
        .join(Property, Tenancy.property_id == Property.id)
        .filter(
            Tenancy.id == tenancy_id,
            Property.landlord_id == g.current_user.id
        )
        .first()
    )

    if not tenancy:
        return jsonify({
            "error": "Tenancy not found."
        }), 404

    if tenancy.status != "active":
        return jsonify({
            "error": "Agreements can only be created for active tenancies."
        }), 400

    # Validate agreement dates against tenancy dates.
    if start_date < tenancy.start_date:
        return jsonify({
            "error": "Agreement cannot start before the tenancy."
        }), 400

    if tenancy.end_date and end_date > tenancy.end_date:
        return jsonify({
            "error": "Agreement cannot end after the tenancy."
        }), 400

    # Check existing agreements.
    existing_agreements = RentalAgreement.query.filter_by(
        tenancy_id=tenancy.id
    ).all()

    if agreement_type == "initial" and existing_agreements:
        return jsonify({
            "error": "An initial agreement already exists for this tenancy."
        }), 409

    if agreement_type == "renewal" and not existing_agreements:
        return jsonify({
            "error": "A renewal requires an existing agreement."
        }), 400

    # Create the agreement.
    agreement = RentalAgreement(
        tenancy_id=tenancy.id,
        agreement_number=agreement_number,
        agreement_type=agreement_type,
        start_date=start_date,
        end_date=end_date,
        status="draft"
    )

    try:
        db.session.add(agreement)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "Agreement number already exists or database constraint was violated."
        }), 409

    return jsonify({
        "success": True,
        "message": "Rental agreement created successfully.",
        "agreement": {
            "id": agreement.id,
            "tenancy_id": agreement.tenancy_id,
            "agreement_number": agreement.agreement_number,
            "agreement_type": agreement.agreement_type,
            "start_date": agreement.start_date.isoformat(),
            "end_date": agreement.end_date.isoformat(),
            "status": agreement.status
        }
    }), 201

