
from app.models import User, Property
from app.extensions import db
from app.auth.security import hash_password


def create_test_user(full_name, email, role):
    """
    Create a user directly in the test database.
    This helper supports roles that cannot use public registration.
    """

    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password("TestPassword123@"),
        role=role
    )

    db.session.add(user)
    db.session.commit()

    return user


def test_unauthenticated_user_cannot_access_landlord_area(client):
    response = client.get("/test/landlord")

    assert response.status_code == 401


def test_landlord_can_access_landlord_area(client):
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "RBAC Landlord",
            "email": "rbac.landlord@example.com",
            "password": "TestPassword123@",
            "role": "landlord"
        }
    )

    assert registration_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "rbac.landlord@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200

    response = client.get("/test/landlord")

    assert response.status_code == 200


def test_tenant_cannot_access_landlord_area(client):
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "RBAC Tenant",
            "email": "rbac.tenant@example.com",
            "password": "TestPassword123@",
            "role": "tenant"
        }
    )

    assert registration_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "rbac.tenant@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200

    response = client.get("/test/landlord")

    assert response.status_code == 403


def test_maintenance_staff_can_access_maintenance_area(client, app):
    with app.app_context():
        create_test_user(
            full_name="RBAC Maintenance Staff",
            email="rbac.maintenance@example.com",
            role="maintenance_staff"
        )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "rbac.maintenance@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200

    response = client.get("/test/maintenance")

    assert response.status_code == 200


def test_landlord_cannot_access_maintenance_area(client):
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "Another RBAC Landlord",
            "email": "rbac.landlord2@example.com",
            "password": "TestPassword123@",
            "role": "landlord"
        }
    )

    assert registration_response.status_code == 201

    client.post(
        "/auth/login",
        json={
            "email": "rbac.landlord2@example.com",
            "password": "TestPassword123@"
        }
    )

    response = client.get("/test/maintenance")

    assert response.status_code == 403


def create_test_property(landlord_id, property_name):
    """
    Create a property belonging to a specific landlord.
    """

    property = Property(
        landlord_id=landlord_id,
        property_name=property_name,
        property_type="apartment",
        address_line="101 Test Street",
        city="Indore",
        state="Madhya Pradesh",
        postal_code="452001",
        bedrooms=2,
        bathrooms=1,
        description="Property created for automated testing."
    )

    db.session.add(property)
    db.session.commit()

    return property


def test_landlord_can_access_own_property(client, app):

    with app.app_context():

        # Create landlord A.
        landlord_a = create_test_user(
            full_name="Landlord A",
            email="ownership.landlord.a@example.com",
            role="landlord"
        )

        # Create a property belonging to landlord A.
        property_a = create_test_property(
            landlord_id=landlord_a.id,
            property_name="Landlord A Apartment"
        )

        property_id = property_a.id

    # Log in as landlord A.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "ownership.landlord.a@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200

    # Try to access landlord A's own property.
    response = client.get(
        f"/test/properties/{property_id}"
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["property"]["property_name"] == "Landlord A Apartment"



def test_landlord_cannot_access_another_landlords_property(client, app):

    with app.app_context():

        # Create landlord A.
        landlord_a = create_test_user(
            full_name="Landlord A",
            email="ownership.cross.a@example.com",
            role="landlord"
        )

        # Create landlord B.
        landlord_b = create_test_user(
            full_name="Landlord B",
            email="ownership.cross.b@example.com",
            role="landlord"
        )

        # Create a property belonging to landlord B.
        property_b = create_test_property(
            landlord_id=landlord_b.id,
            property_name="Landlord B Private Apartment"
        )

        property_id = property_b.id

    # Log in as landlord A.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "ownership.cross.a@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200

    # Landlord A attempts to access landlord B's property.
    response = client.get(
        f"/test/properties/{property_id}"
    )

    # Access must be denied.
    assert response.status_code == 404

    data = response.get_json()

    assert data["error"] == "Property not found or access denied."


def test_unauthenticated_user_cannot_access_property(client, app):

    with app.app_context():

        # Create a landlord.
        landlord = create_test_user(
            full_name="Property Owner",
            email="ownership.unauth@example.com",
            role="landlord"
        )

        # Create the landlord's property.
        property = create_test_property(
            landlord_id=landlord.id,
            property_name="Protected Apartment"
        )

        property_id = property.id

    # Do not log in.
    # Directly attempt to access the property.
    response = client.get(
        f"/test/properties/{property_id}"
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Authentication required."
