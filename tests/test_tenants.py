
def test_landlord_can_search_for_tenant(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "rahul@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Landlord",
        "email": "amit@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the landlord.
    client.post("/auth/login", json={
        "email": "amit@example.com",
        "password": "PrimeStay123!"
    })

    # Search for the tenant.
    response = client.get(
        "/api/tenants/search?email=rahul@example.com"
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["tenant"]["full_name"] == "Rahul Sharma"
    assert result["tenant"]["email"] == "rahul@example.com"
    assert "password_hash" not in result["tenant"]


def test_tenant_cannot_search_for_other_tenants(client):
    client.post("/auth/register", json={
        "full_name": "Tenant One",
        "email": "tenantone@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    client.post("/auth/login", json={
        "email": "tenantone@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get(
        "/api/tenants/search?email=rahul@example.com"
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_search_tenants(client):
    response = client.get(
        "/api/tenants/search?email=rahul@example.com"
    )

    assert response.status_code == 401


def test_tenant_search_rejects_missing_email(client):
    client.post("/auth/register", json={
        "full_name": "Search Landlord",
        "email": "searchlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "searchlandlord@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get("/api/tenants/search")

    assert response.status_code == 400

    assert response.get_json()["error"] == (
        "Tenant email is required."
    )


def test_landlord_cannot_find_inactive_tenant(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Inactive Tenant",
        "email": "inactive@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register and log in a landlord.
    client.post("/auth/register", json={
        "full_name": "Active Landlord",
        "email": "active@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "active@example.com",
        "password": "PrimeStay123!"
    })

    # Deactivate the tenant account in the test database.
    from app.models import User
    from app.extensions import db

    tenant = User.query.filter_by(
        email="inactive@example.com"
    ).first()

    tenant.is_active = False
    db.session.commit()

    # Search for the inactive tenant.
    response = client.get(
        "/api/tenants/search?email=inactive@example.com"
    )

    assert response.status_code == 404

def test_tenant_search_rejects_invalid_email(client):
    client.post("/auth/register", json={
        "full_name": "Validation Landlord",
        "email": "validation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "validation@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get(
        "/api/tenants/search?email=invalid-email"
    )

    assert response.status_code == 400

    assert response.get_json()["error"] == (
        "Invalid email address."
    )

def test_landlord_can_view_tenant_details(client):
    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "rahulprofile@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Profile Landlord",
        "email": "profilelandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "profilelandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Retrieve tenant ID from database.
    from app.models import User

    tenant = User.query.filter_by(
        email="rahulprofile@example.com"
    ).first()

    response = client.get(
        f"/api/tenants/{tenant.id}"
    )

    assert response.status_code == 200

    result = response.get_json()

    assert result["tenant"]["full_name"] == "Rahul Sharma"
    assert result["tenant"]["email"] == "rahulprofile@example.com"
    assert "password_hash" not in result["tenant"]

def test_landlord_cannot_view_nonexistent_tenant(client):
    client.post("/auth/register", json={
        "full_name": "Profile Landlord",
        "email": "missingtenant@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/login", json={
        "email": "missingtenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get("/api/tenants/99999")

    assert response.status_code == 404

    assert response.get_json()["error"] == "Tenant not found."