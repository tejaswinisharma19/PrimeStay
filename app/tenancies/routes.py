from datetime import date
from decimal import Decimal, InvalidOperation

from flask import jsonify, request, g
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Tenancy, Property, User
from app.auth.decorators import role_required
from app.tenancies import tenancies


@tenancies.route("", methods=["POST"])
@role_required("landlord")
def create_tenancy():

    # Receive JSON data.
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    # Define required fields.
    required_fields = [
        "property_id",
        "tenant_id",
        "start_date",
        "monthly_rent"
    ]

    # Check missing fields.
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({
                "error": f"{field} is required."
            }), 400

    # Validate property and tenant IDs.
    property_id = data["property_id"]
    tenant_id = data["tenant_id"]

    for field, value in [
        ("property_id", property_id),
        ("tenant_id", tenant_id)
    ]:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            return jsonify({
                "error": f"{field} must be a positive integer."
            }), 400

    # Find the landlord's own active property.
    property = Property.query.filter_by(
        id=property_id,
        landlord_id=g.current_user.id,
        is_active=True
    ).first()

    if not property:
        return jsonify({
            "error": "Property not found or unavailable."
        }), 404

    # Find an active tenant account.
    tenant = User.query.filter_by(
        id=tenant_id,
        role="tenant",
        is_active=True
    ).first()

    if not tenant:
        return jsonify({
            "error": "Active tenant not found."
        }), 404

    # Validate rental dates.
    try:
        if not isinstance(data["start_date"], str):
            raise ValueError

        start_date = date.fromisoformat(data["start_date"])

        end_date = None

        if data.get("end_date") is not None:
            if not isinstance(data["end_date"], str):
                raise ValueError

            end_date = date.fromisoformat(data["end_date"])

        if end_date and end_date < start_date:
            return jsonify({
                "error": "End date cannot be before start date."
            }), 400

    except ValueError:
        return jsonify({
            "error": "Dates must use YYYY-MM-DD format."
        }), 400

    # Validate monthly rent and security deposit.
    try:
        if isinstance(data["monthly_rent"], bool):
            raise InvalidOperation

        monthly_rent = Decimal(str(data["monthly_rent"]))

        if not monthly_rent.is_finite() or monthly_rent <= 0:
            raise InvalidOperation

        if "security_deposit" in data:
            if isinstance(data["security_deposit"], bool):
                raise InvalidOperation

            security_deposit = Decimal(
                str(data["security_deposit"])
            )
        else:
            security_deposit = Decimal("0")

        if (
            not security_deposit.is_finite()
            or security_deposit < 0
        ):
            raise InvalidOperation

        if (
            monthly_rent.as_tuple().exponent < -2
            or security_deposit.as_tuple().exponent < -2
            or monthly_rent > Decimal("99999999.99")
            or security_deposit > Decimal("99999999.99")
        ):
            raise InvalidOperation

    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "error": "Invalid rent or security deposit amount."
        }), 400

    # Validate rent due day.
    rent_due_day = data.get("rent_due_day", 5)

    if (
        isinstance(rent_due_day, bool)
        or not isinstance(rent_due_day, int)
        or not 1 <= rent_due_day <= 28
    ):
        return jsonify({
            "error": "Rent due day must be between 1 and 28."
        }), 400

    # Create the tenancy record.
    tenancy = Tenancy(
        property_id=property_id,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        monthly_rent=monthly_rent,
        security_deposit=security_deposit,
        rent_due_day=rent_due_day,
        status="active"
    )

    # Save to PostgreSQL.
    try:
        db.session.add(tenancy)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "error": "This property already has an active tenancy or the tenancy details violate a database constraint."
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Unable to create tenancy. Please try again."
        }), 500

    # Return the newly created tenancy.
    return jsonify({
        "message": "Tenancy created successfully.",
        "tenancy": {
            "id": tenancy.id,
            "property_id": tenancy.property_id,
            "tenant_id": tenancy.tenant_id,
            "start_date": tenancy.start_date.isoformat(),
            "end_date": (
                tenancy.end_date.isoformat()
                if tenancy.end_date else None
            ),
            "monthly_rent": str(tenancy.monthly_rent),
            "security_deposit": str(tenancy.security_deposit),
            "rent_due_day": tenancy.rent_due_day,
            "status": tenancy.status
        }
    }), 201


@tenancies.route("", methods=["GET"])
@role_required("landlord")
def list_tenancies():

    # Read the requested status from the URL.
    status = request.args.get("status", "active")

    # Define the allowed status filters.
    allowed_statuses = [
        "active",
        "completed",
        "terminated",
        "all"
    ]

    # Validate the status filter.
    if status not in allowed_statuses:
        return jsonify({
            "error": "Invalid status filter."
        }), 400

    # Start with tenancies belonging only to
    # properties owned by the logged-in landlord.
    query = Tenancy.query.join(
        Property,
        Tenancy.property_id == Property.id
    ).filter(
        Property.landlord_id == g.current_user.id
    )

    # Apply the status filter.
    if status != "all":
        query = query.filter(
            Tenancy.status == status
        )

    # Retrieve the tenancy records.
    records = query.order_by(
        Tenancy.created_at.desc()
    ).all()

    # Prepare the response.
    tenancy_list = []

    for tenancy in records:
        tenancy_list.append({
            "id": tenancy.id,
            "property": {
                "id": tenancy.property.id,
                "name": tenancy.property.property_name
            },
            "tenant": {
                "id": tenancy.tenant.id,
                "full_name": tenancy.tenant.full_name,
                "email": tenancy.tenant.email
            },
            "start_date": tenancy.start_date.isoformat(),
            "end_date": (
                tenancy.end_date.isoformat()
                if tenancy.end_date else None
            ),
            "monthly_rent": str(tenancy.monthly_rent),
            "security_deposit": str(tenancy.security_deposit),
            "rent_due_day": tenancy.rent_due_day,
            "status": tenancy.status
        })

    return jsonify({
        "count": len(tenancy_list),
        "tenancies": tenancy_list
    }), 200


@tenancies.route("/<int:tenancy_id>", methods=["GET"])
@role_required("landlord")
def get_tenancy(tenancy_id):

    # Find the tenancy only if its property belongs
    # to the currently logged-in landlord.
    tenancy = Tenancy.query.join(
        Property,
        Tenancy.property_id == Property.id
    ).filter(
        Tenancy.id == tenancy_id,
        Property.landlord_id == g.current_user.id
    ).first()

    # Return 404 if the tenancy does not exist
    # or does not belong to this landlord.
    if not tenancy:
        return jsonify({
            "error": "Tenancy not found."
        }), 404

    # Return the tenancy details.
    return jsonify({
        "tenancy": {
            "id": tenancy.id,
            "property": {
                "id": tenancy.property.id,
                "name": tenancy.property.property_name,
                "address": tenancy.property.address_line,
                "city": tenancy.property.city,
                "state": tenancy.property.state,
                "postal_code": tenancy.property.postal_code
            },
            "tenant": {
                "id": tenancy.tenant.id,
                "full_name": tenancy.tenant.full_name,
                "email": tenancy.tenant.email,
                "phone": tenancy.tenant.phone
            },
            "start_date": tenancy.start_date.isoformat(),
            "end_date": (
                tenancy.end_date.isoformat()
                if tenancy.end_date else None
            ),
            "monthly_rent": str(tenancy.monthly_rent),
            "security_deposit": str(tenancy.security_deposit),
            "rent_due_day": tenancy.rent_due_day,
            "status": tenancy.status,
            "created_at": tenancy.created_at.isoformat()
        }
    }), 200


def test_landlord_can_view_individual_tenancy(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Individual Tenancy Landlord",
        "email": "individualtenancy@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "individualtenancy@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Sunshine Residency",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Individual Tenancy Tenant",
        "email": "individualtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="individualtenant@example.com"
    ).first()

    # Create a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "18000.00",
        "security_deposit": "36000.00",
        "rent_due_day": 5
    })

    assert create_response.status_code == 201

    tenancy_id = create_response.get_json()["tenancy"]["id"]

    # Retrieve the individual tenancy.
    response = client.get(f"/api/tenancies/{tenancy_id}")

    assert response.status_code == 200

    data = response.get_json()["tenancy"]

    assert data["id"] == tenancy_id
    assert data["property"]["name"] == "Sunshine Residency"
    assert data["property"]["city"] == "Indore"
    assert data["tenant"]["full_name"] == "Individual Tenancy Tenant"
    assert data["tenant"]["email"] == "individualtenant@example.com"
    assert data["start_date"] == "2026-12-01"
    assert data["end_date"] == "2027-11-30"
    assert data["monthly_rent"] == "18000.00"
    assert data["security_deposit"] == "36000.00"
    assert data["rent_due_day"] == 5
    assert data["status"] == "active"
    assert "created_at" in data


def test_landlord_can_view_individual_tenancy(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Individual Tenancy Landlord",
        "email": "individualtenancy@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "individualtenancy@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Sunshine Residency",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Individual Tenancy Tenant",
        "email": "individualtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="individualtenant@example.com"
    ).first()

    # Create a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "18000.00",
        "security_deposit": "36000.00",
        "rent_due_day": 5
    })

    assert create_response.status_code == 201

    tenancy_id = create_response.get_json()["tenancy"]["id"]

    # Retrieve the individual tenancy.
    response = client.get(f"/api/tenancies/{tenancy_id}")

    assert response.status_code == 200

    data = response.get_json()["tenancy"]

    assert data["id"] == tenancy_id
    assert data["property"]["name"] == "Sunshine Residency"
    assert data["property"]["city"] == "Indore"
    assert data["tenant"]["full_name"] == "Individual Tenancy Tenant"
    assert data["tenant"]["email"] == "individualtenant@example.com"
    assert data["start_date"] == "2026-12-01"
    assert data["end_date"] == "2027-11-30"
    assert data["monthly_rent"] == "18000.00"
    assert data["security_deposit"] == "36000.00"
    assert data["rent_due_day"] == 5
    assert data["status"] == "active"
    assert "created_at" in data
