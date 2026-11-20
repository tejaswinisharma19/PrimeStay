import pytest
from datetime import date

from app.extensions import db
from app.models import User, RentalAgreement


def test_landlord_can_view_their_own_agreements(client, app):

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "agreementtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "agreementlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "agreementlandlord@example.com",
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

    # Retrieve the tenant ID.
    tenant = User.query.filter_by(
        email="agreementtenant@example.com"
    ).first()

    # Create a tenancy.
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

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Create an agreement directly in the test database.
    with app.app_context():

        agreement = RentalAgreement(
            tenancy_id=tenancy_id,
            agreement_number="PS-2026-001",
            agreement_type="initial",
            start_date=date(2026, 12, 1),
            end_date=date(2027, 11, 30),
            status="draft"
        )

        db.session.add(agreement)
        db.session.commit()

    # Retrieve agreements through the API.
    response = client.get("/api/agreements")

    assert response.status_code == 200

    result = response.get_json()

    assert result["success"] is True
    assert result["count"] == 1

    assert result["agreements"][0]["agreement_number"] == "PS-2026-001"
    assert result["agreements"][0]["tenancy_id"] == tenancy_id
    assert result["agreements"][0]["status"] == "draft"


def test_landlord_cannot_view_another_landlords_agreements(client, app):

    # Register two tenants.
    client.post("/auth/register", json={
        "full_name": "Tenant One",
        "email": "tenantone@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    client.post("/auth/register", json={
        "full_name": "Tenant Two",
        "email": "tenanttwo@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register two landlords.
    client.post("/auth/register", json={
        "full_name": "Landlord One",
        "email": "landlordone@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/register", json={
        "full_name": "Landlord Two",
        "email": "landlordtwo@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Create first landlord's property.
    client.post("/auth/login", json={
        "email": "landlordone@example.com",
        "password": "PrimeStay123!"
    })

    property_one = client.post("/api/properties", json={
        "property_name": "Apartment One",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    }).get_json()["property"]["id"]

    from app.models import User

    tenant_one = User.query.filter_by(
        email="tenantone@example.com"
    ).first()

    tenancy_one = client.post("/api/tenancies", json={
        "property_id": property_one,
        "tenant_id": tenant_one.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    }).get_json()["tenancy"]["id"]

    client.post("/auth/logout")

    # Create second landlord's property.
    client.post("/auth/login", json={
        "email": "landlordtwo@example.com",
        "password": "PrimeStay123!"
    })

    property_two = client.post("/api/properties", json={
        "property_name": "Apartment Two",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    }).get_json()["property"]["id"]

    tenant_two = User.query.filter_by(
        email="tenanttwo@example.com"
    ).first()

    tenancy_two = client.post("/api/tenancies", json={
        "property_id": property_two,
        "tenant_id": tenant_two.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "15000.00"
    }).get_json()["tenancy"]["id"]

    # Create an agreement for each landlord.
    with app.app_context():

        db.session.add_all([
            RentalAgreement(
                tenancy_id=tenancy_one,
                agreement_number="PS-2026-101",
                agreement_type="initial",
                start_date=date(2026, 12, 1),
                end_date=date(2027, 11, 30),
                status="draft"
            ),
            RentalAgreement(
                tenancy_id=tenancy_two,
                agreement_number="PS-2026-102",
                agreement_type="initial",
                start_date=date(2026, 12, 1),
                end_date=date(2027, 11, 30),
                status="draft"
            )
        ])

        db.session.commit()

    # Log back in as the first landlord.
    client.post("/auth/logout")

    client.post("/auth/login", json={
        "email": "landlordone@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get("/api/agreements")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 1

    agreement_numbers = [
        agreement["agreement_number"]
        for agreement in result["agreements"]
    ]

    assert "PS-2026-101" in agreement_numbers
    assert "PS-2026-102" not in agreement_numbers


def test_tenant_can_view_their_own_agreements(client, app):

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "tenantview@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "landlordview@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "landlordview@example.com",
        "password": "PrimeStay123!"
    })

    # Create property.
    property_response = client.post("/api/properties", json={
        "property_name": "Tenant View Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve tenant.
    tenant = User.query.filter_by(
        email="tenantview@example.com"
    ).first()

    # Create tenancy.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    })

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Create agreement.
    with app.app_context():

        agreement = RentalAgreement(
            tenancy_id=tenancy_id,
            agreement_number="PS-2026-201",
            agreement_type="initial",
            start_date=date(2026, 12, 1),
            end_date=date(2027, 11, 30),
            status="signed",
            signed_on=date(2026, 11, 25)
        )

        db.session.add(agreement)
        db.session.commit()

    # Log out landlord.
    client.post("/auth/logout")

    # Log in as tenant.
    client.post("/auth/login", json={
        "email": "tenantview@example.com",
        "password": "PrimeStay123!"
    })

    # Retrieve agreements.
    response = client.get("/api/agreements")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 1
    assert result["agreements"][0]["agreement_number"] == "PS-2026-201"
    assert result["agreements"][0]["status"] == "signed"


def test_tenant_cannot_view_another_tenants_agreements(client, app):

    # Register two tenants.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "rahulisolation@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    client.post("/auth/register", json={
        "full_name": "Priya Sharma",
        "email": "priyaisolation@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "landlordisolation@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "landlordisolation@example.com",
        "password": "PrimeStay123!"
    })

    # Create property.
    property_response = client.post("/api/properties", json={
        "property_name": "Isolation Test Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve both tenants.
    rahul = User.query.filter_by(
        email="rahulisolation@example.com"
    ).first()

    priya = User.query.filter_by(
        email="priyaisolation@example.com"
    ).first()

    # Create Rahul's tenancy.
    rahul_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": rahul.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    })

    rahul_tenancy_id = rahul_response.get_json()["tenancy"]["id"]

    # Complete Rahul's tenancy so the property can be assigned again.
    from app.models import Tenancy

    with app.app_context():
        tenancy = db.session.get(Tenancy, rahul_tenancy_id)
        tenancy.status = "completed"
        db.session.commit()

    # Create Priya's tenancy.
    priya_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": priya.id,
        "start_date": "2027-12-01",
        "end_date": "2028-11-30",
        "monthly_rent": "13000.00"
    })

    priya_tenancy_id = priya_response.get_json()["tenancy"]["id"]

    # Create agreements for both tenants.
    with app.app_context():

        db.session.add_all([
            RentalAgreement(
                tenancy_id=rahul_tenancy_id,
                agreement_number="PS-2026-301",
                agreement_type="initial",
                start_date=date(2026, 12, 1),
                end_date=date(2027, 11, 30),
                status="signed"
            ),
            RentalAgreement(
                tenancy_id=priya_tenancy_id,
                agreement_number="PS-2027-302",
                agreement_type="initial",
                start_date=date(2027, 12, 1),
                end_date=date(2028, 11, 30),
                status="signed"
            )
        ])

        db.session.commit()

    # Log out landlord.
    client.post("/auth/logout")

    # Log in as Rahul.
    client.post("/auth/login", json={
        "email": "rahulisolation@example.com",
        "password": "PrimeStay123!"
    })

    # Retrieve agreements.
    response = client.get("/api/agreements")

    assert response.status_code == 200

    result = response.get_json()

    assert result["count"] == 1

    agreement_numbers = [
        agreement["agreement_number"]
        for agreement in result["agreements"]
    ]

    assert "PS-2026-301" in agreement_numbers
    assert "PS-2027-302" not in agreement_numbers


def test_unauthenticated_user_cannot_view_agreements(client):

    response = client.get("/api/agreements")

    assert response.status_code == 401


def test_maintenance_staff_cannot_view_agreements(client):

    # Register maintenance staff.
    client.post("/auth/register", json={
        "full_name": "Maintenance Staff",
        "email": "maintenanceagreement@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Promote the test account to maintenance staff.
    from app.models import User

    user = User.query.filter_by(
        email="maintenanceagreement@example.com"
    ).first()

    user.role = "maintenance_staff"

    from app.extensions import db
    db.session.commit()

    # Log in as maintenance staff.
    client.post("/auth/login", json={
        "email": "maintenanceagreement@example.com",
        "password": "PrimeStay123!"
    })

    response = client.get("/api/agreements")

    assert response.status_code == 403


def test_landlord_can_create_rental_agreement(client):

    # Register tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "createagreementtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "createagreementlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "createagreementlandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Create property.
    property_response = client.post("/api/properties", json={
        "property_name": "Agreement Test Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve tenant.
    tenant = User.query.filter_by(
        email="createagreementtenant@example.com"
    ).first()

    # Create tenancy.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    })

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Create rental agreement.
    response = client.post("/api/agreements", json={
        "tenancy_id": tenancy_id,
        "agreement_number": "PS-2026-501",
        "agreement_type": "initial",
        "start_date": "2026-12-01",
        "end_date": "2027-11-30"
    })

    assert response.status_code == 201

    result = response.get_json()

    assert result["success"] is True
    assert result["message"] == "Rental agreement created successfully."

    assert result["agreement"]["tenancy_id"] == tenancy_id
    assert result["agreement"]["agreement_number"] == "PS-2026-501"
    assert result["agreement"]["agreement_type"] == "initial"
    assert result["agreement"]["status"] == "draft"
    

@pytest.mark.parametrize(
    "agreement_start, agreement_end, expected_error",
    [
        (
            "2026-11-30",
            "2027-11-30",
            "Agreement cannot start before the tenancy."
        ),
        (
            "2026-12-01",
            "2027-12-01",
            "Agreement cannot end after the tenancy."
        )
    ]
)
def test_agreement_dates_must_be_within_tenancy_period(
    client,
    agreement_start,
    agreement_end,
    expected_error
):

    # Register tenant.
    client.post("/auth/register", json={
        "full_name": "Agreement Date Tenant",
        "email": "agreementdatetenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Agreement Date Landlord",
        "email": "agreementdatelandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "agreementdatelandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Create property.
    property_response = client.post("/api/properties", json={
        "property_name": "Date Validation Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve tenant.
    tenant = User.query.filter_by(
        email="agreementdatetenant@example.com"
    ).first()

    # Create tenancy.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    })

    assert tenancy_response.status_code == 201

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Attempt to create an agreement outside the tenancy period.
    response = client.post("/api/agreements", json={
        "tenancy_id": tenancy_id,
        "agreement_number": "PS-2026-1201",
        "agreement_type": "initial",
        "start_date": agreement_start,
        "end_date": agreement_end
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == expected_error




def test_tenant_cannot_create_rental_agreement(client):

    # Register tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "tenantcreateblocked@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Log in as tenant.
    client.post("/auth/login", json={
        "email": "tenantcreateblocked@example.com",
        "password": "PrimeStay123!"
    })

    # Attempt to create agreement.
    response = client.post("/api/agreements", json={
        "tenancy_id": 1,
        "agreement_number": "PS-2026-601",
        "agreement_type": "initial",
        "start_date": "2026-12-01",
        "end_date": "2027-11-30"
    })

    assert response.status_code == 403


def test_landlord_cannot_create_agreement_for_another_landlords_tenancy(client):

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "ownershiptenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register two landlords.
    client.post("/auth/register", json={
        "full_name": "Landlord One",
        "email": "ownershiplandlordone@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    client.post("/auth/register", json={
        "full_name": "Landlord Two",
        "email": "ownershiplandlordtwo@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as the first landlord.
    client.post("/auth/login", json={
        "email": "ownershiplandlordone@example.com",
        "password": "PrimeStay123!"
    })

    # Create the first landlord's property.
    client.post("/api/properties", json={
        "property_name": "Landlord One Apartment",
        "property_type": "apartment",
        "address_line": "Palasia",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001"
    })

    # Log out.
    client.post("/auth/logout")

    # Log in as the second landlord.
    client.post("/auth/login", json={
        "email": "ownershiplandlordtwo@example.com",
        "password": "PrimeStay123!"
    })

    # Create the second landlord's property.
    property_response = client.post("/api/properties", json={
        "property_name": "Landlord Two Apartment",
        "property_type": "apartment",
        "address_line": "Vijay Nagar",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452010"
    })

    property_id = property_response.get_json()["property"]["id"]

    # Retrieve tenant.
    tenant = User.query.filter_by(
        email="ownershiptenant@example.com"
    ).first()

    # Create tenancy under the second landlord.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant.id,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30",
        "monthly_rent": "12000.00"
    })

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Log out the second landlord.
    client.post("/auth/logout")

    # Log in as the first landlord.
    client.post("/auth/login", json={
        "email": "ownershiplandlordone@example.com",
        "password": "PrimeStay123!"
    })

    # Attempt to create an agreement for the second landlord's tenancy.
    response = client.post("/api/agreements", json={
        "tenancy_id": tenancy_id,
        "agreement_number": "PS-2026-701",
        "agreement_type": "initial",
        "start_date": "2026-12-01",
        "end_date": "2027-11-30"
    })

    assert response.status_code == 404

    assert response.get_json()["error"] == "Tenancy not found."



def test_agreement_creation_rejects_missing_required_fields(client):

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Missing Fields Landlord",
        "email": "missingfieldslandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "missingfieldslandlord@example.com",
        "password": "PrimeStay123!"
    })

    # Submit incomplete agreement data.
    response = client.post("/api/agreements", json={
        "tenancy_id": 1,
        "agreement_number": "PS-2026-801"
    })

    assert response.status_code == 400

    result = response.get_json()

    assert result["error"] == "Missing required fields."

    assert "agreement_type" in result["missing_fields"]
    assert "start_date" in result["missing_fields"]
    assert "end_date" in result["missing_fields"]



import pytest


@pytest.mark.parametrize(
    "tenancy_id",
    ["abc", 0, -5, True]
)
def test_agreement_creation_rejects_invalid_tenancy_id(
    client,
    tenancy_id
):

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Tenancy Landlord",
        "email": "invalidtenancyagreement@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "invalidtenancyagreement@example.com",
        "password": "PrimeStay123!"
    })

    # Submit agreement with invalid tenancy ID.
    response = client.post("/api/agreements", json={
        "tenancy_id": tenancy_id,
        "agreement_number": "PS-2026-901",
        "agreement_type": "initial",
        "start_date": "2026-12-01",
        "end_date": "2027-11-30"
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid tenancy ID."



@pytest.mark.parametrize(
    "agreement_type",
    ["temporary", "permanent", "new", "", None, 123]
)
def test_agreement_creation_rejects_invalid_agreement_type(
    client,
    agreement_type
):

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Type Landlord",
        "email": "invalidtypeagreement@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "invalidtypeagreement@example.com",
        "password": "PrimeStay123!"
    })

    # Submit agreement with invalid type.
    response = client.post("/api/agreements", json={
        "tenancy_id": 1,
        "agreement_number": "PS-2026-1001",
        "agreement_type": agreement_type,
        "start_date": "2026-12-01",
        "end_date": "2027-11-30"
    })

    assert response.status_code == 400

    assert response.get_json()["error"] == (
        "Agreement type must be initial or renewal."
    )
    

@pytest.mark.parametrize(
    "start_date, end_date, expected_error",
    [
        (
            "01-12-2026",
            "2027-11-30",
            "Dates must use YYYY-MM-DD format."
        ),
        (
            "2026-02-30",
            "2027-11-30",
            "Dates must use YYYY-MM-DD format."
        ),
        (
            "2026-12-01",
            "2026-11-30",
            "Agreement end date cannot precede start date."
        ),
        (
            "20261201",
            "2027-11-30",
            "Dates must use YYYY-MM-DD format."
        ),
        (
            "2026/12/01",
            "2027-11-30",
            "Dates must use YYYY-MM-DD format."
        ),
        (
            12345,
            "2027-11-30",
            "Dates must use YYYY-MM-DD format."
        )
    ]
)
def test_agreement_creation_rejects_invalid_dates(
    client,
    start_date,
    end_date,
    expected_error
):

    # Register landlord.
    client.post("/auth/register", json={
        "full_name": "Invalid Date Landlord",
        "email": "invaliddateagreement@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "invaliddateagreement@example.com",
        "password": "PrimeStay123!"
    })

    # Submit agreement with invalid dates.
    response = client.post("/api/agreements", json={
        "tenancy_id": 1,
        "agreement_number": "PS-2026-1101",
        "agreement_type": "initial",
        "start_date": start_date,
        "end_date": end_date
    })

    assert response.status_code == 400
    assert response.get_json()["error"] == expected_error
