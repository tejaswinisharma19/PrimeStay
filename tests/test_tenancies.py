
def test_landlord_can_create_tenancy(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "rahultenancy@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "amittenancy@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "amittenancy@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Sunrise Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010",
        "bedrooms": 2,
        "bathrooms": 2
    })

    assert property_response.status_code == 201

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve tenant ID.
    from app.models import User

    tenant = User.query.filter_by(
        email="rahultenancy@example.com"
    ).first()

    # Create tenancy.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00",
        "security_deposit": "24000.00",
        "rent_due_day": 5
    })

    assert tenancy_response.status_code == 201

    result = tenancy_response.get_json()

    assert result["message"] == "Tenancy created successfully."
    assert result["tenancy"]["property_id"] == property_id
    assert result["tenancy"]["tenant_id"] == tenant.id
    assert result["tenancy"]["monthly_rent"] == "12000.00"
    assert result["tenancy"]["security_deposit"] == "24000.00"
    assert result["tenancy"]["rent_due_day"] == 5
    assert result["tenancy"]["status"] == "active"


def test_landlord_cannot_create_tenancy_for_another_landlords_property(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "rahulownership@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register first landlord.
    client.post("/auth/register", json={
        "full_name": "First Landlord",
        "email": "firstlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "firstlandlord@example.com",
        "password": "PrimeStay123!"
    })

    # First landlord creates a property.
    property_response = client.post("/api/properties", json={
        "property_name": "First Landlord Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Log out first landlord.
    client.post("/auth/logout")

    # Register and log in second landlord.
    client.post("/auth/register", json={
        "full_name": "Second Landlord",
        "email": "secondlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "secondlandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Retrieve tenant ID.
    from app.models import User

    tenant = User.query.filter_by(
        email="rahulownership@example.com"
    ).first()

    # Attempt to create tenancy for someone else's property.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00",
        "security_deposit": "24000.00",
        "rent_due_day": 5
    })

    assert response.status_code == 404

    assert response.get_json()["error"] == (
        "Property not found or unavailable."
    )

def test_landlord_cannot_create_tenancy_with_invalid_tenant(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Tenant Validation Landlord",
        "email": "tenantvalidation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "tenantvalidation@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Validation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Attempt to create tenancy with a nonexistent tenant ID.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": 99999,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 404

    assert response.get_json()["error"] == (
        "Active tenant not found."
    )



def test_landlord_cannot_be_used_as_tenant(client):
    # Register the landlord.
    client.post("/auth/register", json={
        "full_name": "Role Validation Landlord",
        "email": "rolevalidation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "rolevalidation@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Role Validation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Find the landlord's own user ID.
    from app.models import User

    landlord = User.query.filter_by(
        email="rolevalidation@example.com"
    ).first()

    # Try using the landlord's ID as the tenant ID.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": landlord.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 404
    assert response.get_json()["error"] == "Active tenant not found."


def test_tenant_cannot_create_tenancy(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Unauthorized Tenant",
        "email": "unauthorized@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Log in as the tenant.
    client.post("/auth/login", json={
        "email": "unauthorized@example.com",
        "password": "PrimeStay123!"
    })

    # Attempt to create a tenancy.
    response = client.post("/api/tenancies", json={
        "property_id": 1,
        "tenant_id": 1,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 403
    assert response.get_json()["error"] == "You do not have permission to access this resource."


def test_unauthenticated_user_cannot_create_tenancy(client):
    # Attempt to create a tenancy without logging in.
    response = client.post("/api/tenancies", json={
        "property_id": 1,
        "tenant_id": 1,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required."


def test_tenancy_creation_rejects_missing_required_field(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Missing Field Landlord",
        "email": "missingfield@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "missingfield@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Missing Field Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Send a request without monthly_rent.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": 99999,
        "start_date": "2026-12-01"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "monthly_rent is required."



def test_tenancy_creation_rejects_invalid_start_date(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Date Landlord",
        "email": "invaliddate@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "invaliddate@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Date Validation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Date Validation Tenant",
        "email": "datevalidationtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="datevalidationtenant@example.com"
    ).first()

    # Submit an incorrectly formatted start date.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "01-12-2026",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Dates must use YYYY-MM-DD format."


def test_tenancy_creation_rejects_end_date_before_start_date(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Date Range Landlord",
        "email": "daterange@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "daterange@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Date Range Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Date Range Tenant",
        "email": "daterangetenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="daterangetenant@example.com"
    ).first()

    # Submit an end date earlier than the start date.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2026-11-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "End date cannot be before start date."


def test_tenancy_creation_rejects_zero_monthly_rent(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Rent Validation Landlord",
        "email": "rentvalidation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "rentvalidation@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Rent Validation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rent Validation Tenant",
        "email": "rentvalidationtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="rentvalidationtenant@example.com"
    ).first()

    # Attempt to create a tenancy with zero rent.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "0"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid rent or security deposit amount."



def test_tenancy_creation_rejects_negative_monthly_rent(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Negative Rent Landlord",
        "email": "negativerent@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "negativerent@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Negative Rent Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Negative Rent Tenant",
        "email": "negativerenttenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="negativerenttenant@example.com"
    ).first()

    # Attempt to create a tenancy with negative rent.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "-5000.00"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid rent or security deposit amount."



def test_tenancy_creation_rejects_negative_security_deposit(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Deposit Validation Landlord",
        "email": "depositvalidation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "depositvalidation@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Deposit Validation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Deposit Validation Tenant",
        "email": "deposittenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="deposittenant@example.com"
    ).first()

    # Attempt to create a tenancy with a negative deposit.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00",
        "security_deposit": "-5000.00"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid rent or security deposit amount."


def test_tenancy_creation_rejects_invalid_rent_due_day(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Due Day Landlord",
        "email": "dueday@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "dueday@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Due Day Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Due Day Tenant",
        "email": "duedaytenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="duedaytenant@example.com"
    ).first()

    # Attempt to create a tenancy with an invalid due day.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00",
        "rent_due_day": 31
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Rent due day must be between 1 and 28."


def test_property_cannot_have_two_active_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Duplicate Tenancy Landlord",
        "email": "duplicatetenancy@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "duplicatetenancy@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Sunrise Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register the first tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Tenant",
        "email": "rahuldupe@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register the second tenant.
    client.post("/auth/register", json={
        "full_name": "Priya Tenant",
        "email": "priyadupe@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    rahul = User.query.filter_by(
        email="rahuldupe@example.com"
    ).first()

    priya = User.query.filter_by(
        email="priyadupe@example.com"
    ).first()

    # Create the first active tenancy for Rahul.
    first_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": rahul.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert first_response.status_code == 201

    # Attempt to create another active tenancy for Priya
    # in the same property.
    second_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": priya.id,
        "start_date": "2027-01-01",
        "monthly_rent": "13000.00"
    })

    assert second_response.status_code == 409
    assert "already has an active tenancy" in second_response.get_json()["error"]


def test_tenancy_cannot_be_created_for_inactive_property(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Inactive Property Landlord",
        "email": "inactiveproperty@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "inactiveproperty@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Renovation Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Deactivate the property.
    delete_response = client.delete(
        f"/api/properties/{property_id}"
    )

    assert delete_response.status_code == 200

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Inactive Property Tenant",
        "email": "inactivepropertytenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="inactivepropertytenant@example.com"
    ).first()

    # Attempt to create a tenancy for the inactive property.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 404
    assert response.get_json()["error"] == "Property not found or unavailable."


def test_inactive_tenant_cannot_be_assigned_to_tenancy(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Inactive Tenant Landlord",
        "email": "inactivetenantlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "inactivetenantlandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Inactive Tenant Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Inactive Account Tenant",
        "email": "inactiveaccounttenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.extensions import db
    from app.models import User

    tenant = User.query.filter_by(
        email="inactiveaccounttenant@example.com"
    ).first()

    # Deactivate the tenant account.
    tenant.is_active = False
    db.session.commit()

    # Attempt to assign the inactive tenant.
    response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert response.status_code == 404
    assert response.get_json()["error"] == "Active tenant not found."


def test_landlord_can_view_their_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Tenancy List Landlord",
        "email": "tenancylist@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "tenancylist@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Green Valley Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Tenancy List Tenant",
        "email": "tenancylisttenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="tenancylisttenant@example.com"
    ).first()

    # Create a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "15000.00",
        "security_deposit": "30000.00",
        "rent_due_day": 5
    })

    assert create_response.status_code == 201

    # Retrieve the landlord's tenancies.
    response = client.get("/api/tenancies")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 1
    assert len(data["tenancies"]) == 1

    tenancy = data["tenancies"][0]

    assert tenancy["property"]["name"] == "Green Valley Apartment"
    assert tenancy["tenant"]["full_name"] == "Tenancy List Tenant"
    assert tenancy["tenant"]["email"] == "tenancylisttenant@example.com"
    assert tenancy["monthly_rent"] == "15000.00"
    assert tenancy["security_deposit"] == "30000.00"
    assert tenancy["rent_due_day"] == 5
    assert tenancy["status"] == "active"



def test_landlord_cannot_view_another_landlords_tenancies(client):
    # Register Landlord A.
    client.post("/auth/register", json={
        "full_name": "Landlord A",
        "email": "landlord.a@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as Landlord A.
    client.post("/auth/login", json={
        "email": "landlord.a@example.com",
        "password": "PrimeStay123!"
    })

    # Create Landlord A's property.
    property_response = client.post("/api/properties", json={
        "property_name": "Green Valley Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Tenant",
        "email": "isolationtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="isolationtenant@example.com"
    ).first()

    # Create a tenancy under Landlord A.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "15000.00"
    })

    assert create_response.status_code == 201

    # Log out Landlord A.
    client.post("/auth/logout")

    # Register Landlord B.
    client.post("/auth/register", json={
        "full_name": "Landlord B",
        "email": "landlord.b@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as Landlord B.
    client.post("/auth/login", json={
        "email": "landlord.b@example.com",
        "password": "PrimeStay123!"
    })

    # Landlord B requests their tenancy records.
    response = client.get("/api/tenancies")

    assert response.status_code == 200

    data = response.get_json()

    # Landlord B must not see Landlord A's tenancy.
    assert data["count"] == 0
    assert data["tenancies"] == []


def test_landlord_can_filter_active_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Active Filter Landlord",
        "email": "activefilter@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "activefilter@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Active Filter Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Active Filter Tenant",
        "email": "activefiltertenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="activefiltertenant@example.com"
    ).first()

    # Create an active tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert create_response.status_code == 201

    # Request only active tenancies.
    response = client.get("/api/tenancies?status=active")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 1
    assert data["tenancies"][0]["status"] == "active"


def test_landlord_can_filter_completed_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Completed Filter Landlord",
        "email": "completedfilter@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "completedfilter@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Completed Filter Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Completed Filter Tenant",
        "email": "completedfiltertenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.extensions import db
    from app.models import Tenancy, User

    tenant = User.query.filter_by(
        email="completedfiltertenant@example.com"
    ).first()

    # Create a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert create_response.status_code == 201

    # Change its status to completed for testing.
    tenancy = Tenancy.query.filter_by(
        property_id=property_id
    ).first()

    tenancy.status = "completed"
    db.session.commit()

    # Request completed tenancies.
    response = client.get("/api/tenancies?status=completed")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 1
    assert data["tenancies"][0]["status"] == "completed"


def test_landlord_can_filter_terminated_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Terminated Filter Landlord",
        "email": "terminatedfilter@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "terminatedfilter@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Terminated Filter Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Terminated Filter Tenant",
        "email": "terminatedfiltertenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.extensions import db
    from app.models import Tenancy, User

    tenant = User.query.filter_by(
        email="terminatedfiltertenant@example.com"
    ).first()

    # Create a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert create_response.status_code == 201

    # Change the tenancy status for testing.
    tenancy = Tenancy.query.filter_by(
        property_id=property_id
    ).first()

    tenancy.status = "terminated"
    db.session.commit()

    # Request terminated tenancies.
    response = client.get("/api/tenancies?status=terminated")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 1
    assert data["tenancies"][0]["status"] == "terminated"


def test_landlord_can_view_all_tenancies(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "All Status Landlord",
        "email": "allstatus@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "allstatus@example.com",
        "password": "PrimeStay123!"
    })

    from app.extensions import db
    from app.models import Tenancy, User

    # Register three tenants.
    tenant_emails = [
        "allstatus1@example.com",
        "allstatus2@example.com",
        "allstatus3@example.com"
    ]

    tenants = []

    for index, email in enumerate(tenant_emails, start=1):
        client.post("/auth/register", json={
            "full_name": f"All Status Tenant {index}",
            "email": email,
            "password": "PrimeStay123!",
            "role": "tenant"
        })

        tenant = User.query.filter_by(email=email).first()
        tenants.append(tenant)

    # Create three different properties and tenancies.
    statuses = ["active", "completed", "terminated"]

    for index, status in enumerate(statuses, start=1):
        property_response = client.post("/api/properties", json={
            "property_name": f"All Status Apartment {index}",
            "property_type": "apartment",
            "address_line": f"Palasia Road {index}",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452001"
        })

        property_id = property_response.get_json()["property"]["id"]

        tenancy_response = client.post("/api/tenancies", json={
            "property_id": property_id,
            "tenant_id": tenants[index - 1].id,
            "start_date": "2026-12-01",
            "monthly_rent": "12000.00"
        })

        assert tenancy_response.status_code == 201

        tenancy = Tenancy.query.filter_by(
            property_id=property_id
        ).first()

        tenancy.status = status

    db.session.commit()

    # Request all tenancies.
    response = client.get("/api/tenancies?status=all")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 3

    returned_statuses = {
        tenancy["status"]
        for tenancy in data["tenancies"]
    }

    assert returned_statuses == {
        "active",
        "completed",
        "terminated"
    }


def test_landlord_cannot_use_invalid_tenancy_status_filter(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Status Landlord",
        "email": "invalidstatus@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "invalidstatus@example.com",
        "password": "PrimeStay123!"
    })

    # Request tenancies using an unsupported status.
    response = client.get("/api/tenancies?status=pending")

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid status filter."


def test_property_can_have_new_tenancy_after_previous_is_completed(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Property Reuse Landlord",
        "email": "propertyreuse@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "propertyreuse@example.com",
        "password": "PrimeStay123!"
    })

    # Create a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Green Valley Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register the first tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Previous Tenant",
        "email": "rahulprevious@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register the second tenant.
    client.post("/auth/register", json={
        "full_name": "Priya New Tenant",
        "email": "priyanew@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.extensions import db
    from app.models import Tenancy, User

    rahul = User.query.filter_by(
        email="rahulprevious@example.com"
    ).first()

    priya = User.query.filter_by(
        email="priyanew@example.com"
    ).first()

    # Create Rahul's tenancy.
    first_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": rahul.id,
        "start_date": "2026-12-01",
        "monthly_rent": "12000.00"
    })

    assert first_response.status_code == 201

    # Mark Rahul's tenancy as completed.
    previous_tenancy = Tenancy.query.filter_by(
        property_id=property_id
    ).first()

    previous_tenancy.status = "completed"
    db.session.commit()

    # Create a new tenancy for Priya in the same property.
    second_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": priya.id,
        "start_date": "2027-12-01",
        "monthly_rent": "14000.00"
    })

    assert second_response.status_code == 201

    # Verify that both tenancy records are preserved.
    tenancies = Tenancy.query.filter_by(
        property_id=property_id
    ).all()

    assert len(tenancies) == 2

    statuses = {tenancy.status for tenancy in tenancies}

    assert statuses == {"active", "completed"}


def test_tenant_cannot_view_tenancy_list(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Restricted List Tenant",
        "email": "restrictedlist@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Log in as the tenant.
    client.post("/auth/login", json={
        "email": "restrictedlist@example.com",
        "password": "PrimeStay123!"
    })

    # Attempt to access the landlord's tenancy list.
    response = client.get("/api/tenancies")

    assert response.status_code == 403
    assert response.get_json()["error"] == "You do not have permission to access this resource."


def test_unauthenticated_user_cannot_view_tenancy_list(client):
    # Attempt to retrieve tenancies without logging in.
    response = client.get("/api/tenancies")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required."



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

    assert property_response.status_code == 201
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


def test_landlord_cannot_view_another_landlords_individual_tenancy(client):
    # Register Landlord A.
    client.post("/auth/register", json={
        "full_name": "Individual Landlord A",
        "email": "individual.landlord.a@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "individual.landlord.a@example.com",
        "password": "PrimeStay123!"
    })

    # Landlord A creates a property.
    property_response = client.post("/api/properties", json={
        "property_name": "Landlord A Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Individual Access Tenant",
        "email": "individual.access.tenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    from app.models import User

    tenant = User.query.filter_by(
        email="individual.access.tenant@example.com"
    ).first()

    # Landlord A creates a tenancy.
    create_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "monthly_rent": "15000.00"
    })

    assert create_response.status_code == 201

    tenancy_id = create_response.get_json()["tenancy"]["id"]

    # Log out Landlord A.
    client.post("/auth/logout")

    # Register and log in Landlord B.
    client.post("/auth/register", json={
        "full_name": "Individual Landlord B",
        "email": "individual.landlord.b@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "individual.landlord.b@example.com",
        "password": "PrimeStay123!"
    })

    # Landlord B attempts to access Landlord A's tenancy.
    response = client.get(f"/api/tenancies/{tenancy_id}")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Tenancy not found."


def test_landlord_cannot_view_nonexistent_tenancy(client):
    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Nonexistent Tenancy Landlord",
        "email": "nonexistent.tenancy@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "nonexistent.tenancy@example.com",
        "password": "PrimeStay123!"
    })

    # Request a tenancy ID that does not exist.
    response = client.get("/api/tenancies/999999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Tenancy not found."


def test_tenant_cannot_view_individual_tenancy(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Restricted Individual Tenant",
        "email": "restricted.individual@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Log in as the tenant.
    client.post("/auth/login", json={
        "email": "restricted.individual@example.com",
        "password": "PrimeStay123!"
    })

    # Attempt to access an individual tenancy.
    response = client.get("/api/tenancies/1")

    assert response.status_code == 403
    assert response.get_json()["error"] == (
        "You do not have permission to access this resource."
    )


def test_unauthenticated_user_cannot_view_individual_tenancy(client):
    # Attempt to access an individual tenancy without logging in.
    response = client.get("/api/tenancies/1")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required."
