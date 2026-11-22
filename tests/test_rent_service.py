from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models import Payment, RentObligation, Tenancy, User
from app.rent.service import (
    calculate_outstanding_amount,
    calculate_period_amount,
    calculate_verified_amount,
    generate_monthly_obligation,
    get_obligation_summary,
    update_obligation_status,
)
from tests.conftest import client


def test_prorated_rent_for_november():
    amount = calculate_period_amount(
        Decimal("12000"),
        date(2026, 11, 15),
        date(2026, 11, 30)
    )

    assert amount == Decimal("6400.00")


def test_prorated_rent_for_february():
    amount = calculate_period_amount(
        Decimal("12000"),
        date(2027, 2, 15),
        date(2027, 2, 28)
    )

    assert amount == Decimal("6000.00")


def test_full_month_rent():
    amount = calculate_period_amount(
        Decimal("12000"),
        date(2026, 11, 1),
        date(2026, 11, 30)
    )

    assert amount == Decimal("12000.00")


def test_leap_year_february():
    amount = calculate_period_amount(
        Decimal("12000"),
        date(2028, 2, 1),
        date(2028, 2, 29)
    )

    assert amount == Decimal("12000.00")


def test_invalid_rent_period():
    with pytest.raises(ValueError):
        calculate_period_amount(
            Decimal("12000"),
            date(2026, 11, 20),
            date(2026, 11, 10)
        )


def test_rent_period_cannot_cross_months():
    with pytest.raises(ValueError):
        calculate_period_amount(
            Decimal("12000"),
            date(2026, 11, 25),
            date(2026, 12, 5)
        )


def test_zero_rent_is_rejected():
    with pytest.raises(ValueError):
        calculate_period_amount(
            Decimal("0"),
            date(2026, 11, 1),
            date(2026, 11, 30)
        )


def create_test_tenancy(client, app, start_date="2026-11-15",
                        end_date="2027-02-15", status="active"):

    # Register a tenant.
    client.post("/auth/register", json={
        "full_name": "Rahul Sharma",
        "email": "renttenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    # Register a landlord.
    client.post("/auth/register", json={
        "full_name": "Amit Sharma",
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!",
        "role": "landlord"
    })

    # Log in as landlord.
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
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
    with app.app_context():
        tenant = User.query.filter_by(
            email="renttenant@example.com"
        ).first()

        tenant_id = tenant.id

    # Create a tenancy.
    tenancy_response = client.post("/api/tenancies", json={
        "property_id": property_id,
        "tenant_id": tenant_id,
        "start_date": start_date,
        "end_date": end_date,
        "monthly_rent": "12000.00",
        "security_deposit": "24000.00",
        "rent_due_day": 5
    })

    assert tenancy_response.status_code == 201

    tenancy_id = tenancy_response.get_json()["tenancy"]["id"]

    # Change status when testing inactive tenancies.
    if status != "active":
        with app.app_context():
            tenancy = db.session.get(Tenancy, tenancy_id)
            tenancy.status = status
            db.session.commit()

    return tenancy_id


def test_generate_first_month_prorated_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2026, 11, 1)
        )

        assert obligation.amount_due == Decimal("6400.00")
        assert obligation.period_start == date(2026, 11, 15)
        assert obligation.period_end == date(2026, 11, 30)
        assert obligation.due_date == date(2026, 11, 15)
        assert obligation.status == "pending"


def test_generate_full_month_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2026, 12, 1)
        )

        assert obligation.amount_due == Decimal("12000.00")
        assert obligation.period_start == date(2026, 12, 1)
        assert obligation.period_end == date(2026, 12, 31)
        assert obligation.due_date == date(2026, 12, 5)


def test_generate_last_month_prorated_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2027, 2, 1)
        )

        assert obligation.amount_due == Decimal("6428.57")
        assert obligation.period_start == date(2027, 2, 1)
        assert obligation.period_end == date(2027, 2, 15)
        assert obligation.due_date == date(2027, 2, 5)


def test_completed_tenancy_does_not_generate_obligation(client, app):
    tenancy_id = create_test_tenancy(
        client, app, status="completed"
    )

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2026, 12, 1)
        )

        assert obligation is None


def test_terminated_tenancy_does_not_generate_obligation(client, app):
    tenancy_id = create_test_tenancy(
        client, app, status="terminated"
    )

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2026, 12, 1)
        )

        assert obligation is None


def test_duplicate_obligation_is_not_created(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        first = generate_monthly_obligation(
            tenancy,
            date(2026, 12, 1)
        )

        second = generate_monthly_obligation(
            tenancy,
            date(2026, 12, 1)
        )

        assert first.id == second.id

        obligations = RentObligation.query.filter_by(
            tenancy_id=tenancy_id
        ).all()

        assert len(obligations) == 1


def test_month_outside_tenancy_does_not_generate_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy,
            date(2026, 10, 1)
        )

        assert obligation is None

        obligations = RentObligation.query.filter_by(
            tenancy_id=tenancy_id
        ).all()

        assert len(obligations) == 0


def create_test_payment(
    obligation,
    amount,
    status="recorded"
):
    payment = Payment(
        rent_obligation_id=obligation.id,
        recorded_by=obligation.tenancy.tenant_id,
        amount=Decimal(str(amount)),
        payment_date=date(2026, 12, 5),
        payment_method="upi",
        status=status
    )

    db.session.add(payment)
    db.session.flush()

    return payment


def test_no_payments_means_full_outstanding(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)

        obligation = generate_monthly_obligation(
            tenancy, date(2026, 12, 1)
        )

        assert calculate_verified_amount(obligation) == Decimal("0.00")
        assert calculate_outstanding_amount(obligation) == Decimal("12000.00")
        assert update_obligation_status(obligation) == "pending"


def test_recorded_payment_does_not_reduce_outstanding(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "5000", "recorded")

        assert calculate_verified_amount(obligation) == Decimal("0.00")
        assert calculate_outstanding_amount(obligation) == Decimal("12000.00")


def test_rejected_payment_does_not_reduce_outstanding(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "5000", "rejected")

        assert calculate_outstanding_amount(obligation) == Decimal("12000.00")


def test_partial_verified_payment(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "5000", "verified")

        assert calculate_verified_amount(obligation) == Decimal("5000.00")
        assert calculate_outstanding_amount(obligation) == Decimal("7000.00")
        assert update_obligation_status(obligation) == "partially_paid"


def test_multiple_verified_payments(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "5000", "verified")
        create_test_payment(obligation, "3000", "verified")

        assert calculate_verified_amount(obligation) == Decimal("8000.00")
        assert calculate_outstanding_amount(obligation) == Decimal("4000.00")


def test_fully_paid_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "12000", "verified")

        assert update_obligation_status(obligation) == "paid"
        assert calculate_outstanding_amount(obligation) == Decimal("0.00")


def test_overpayment_is_rejected(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "13000", "verified")

        with pytest.raises(ValueError):
            update_obligation_status(obligation)


def test_overdue_obligation(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        summary = get_obligation_summary(
            obligation,
            today=date(2026, 12, 10)
        )

        assert summary["is_overdue"] is True


def test_fully_paid_obligation_is_not_overdue(client, app):
    tenancy_id = create_test_tenancy(client, app)

    with app.app_context():
        tenancy = db.session.get(Tenancy, tenancy_id)
        obligation = generate_monthly_obligation(tenancy, date(2026, 12, 1))

        create_test_payment(obligation, "12000", "verified")
        update_obligation_status(obligation)

        summary = get_obligation_summary(
            obligation,
            today=date(2026, 12, 10)
        )

        assert summary["is_overdue"] is False


def test_landlord_can_generate_rent(client, app):
    tenancy_id = create_test_tenancy(client, app)

    response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-11"
    })

    assert response.status_code == 201

    result = response.get_json()

    assert result["message"] == "Rent obligation generated successfully."
    assert result["obligation"]["amount_due"] == "6400.00"
    assert result["obligation"]["period_start"] == "2026-11-15"
    assert result["obligation"]["period_end"] == "2026-11-30"


def test_generating_same_month_does_not_duplicate_rent(client, app):
    tenancy_id = create_test_tenancy(client, app)

    first = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })

    second = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.get_json()["message"] == "Rent obligation already exists."


def test_tenant_cannot_generate_rent(client, app):
    tenancy_id = create_test_tenancy(client, app)

    client.post("/auth/logout")

    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })

    assert response.status_code == 403


def test_rent_generation_requires_login(client):
    response = client.post("/api/rent/generate", json={
        "tenancy_id": 1,
        "month": "2026-12"
    })

    assert response.status_code == 401


def test_invalid_month_is_rejected(client, app):
    tenancy_id = create_test_tenancy(client, app)

    response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-13"
    })

    assert response.status_code == 400


def test_completed_tenancy_cannot_generate_rent_through_api(client, app):
    tenancy_id = create_test_tenancy(
        client, app, status="completed"
    )

    response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })

    assert response.status_code == 400


def test_landlord_can_list_rent_obligations(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post(
        "/api/rent/generate",
        json={"tenancy_id": tenancy_id, "month": "2026-11"}
    )
    assert generate_response.status_code == 201

    response = client.get("/api/rent/obligations")

    assert response.status_code == 200
    result = response.get_json()

    assert result["count"] == 1
    assert result["obligations"][0]["tenancy_id"] == tenancy_id
    assert result["obligations"][0]["amount_due"] == "6400.00"
    assert result["obligations"][0]["outstanding_amount"] == "6400.00"


def test_tenant_can_list_own_rent_obligations(client, app):
    tenancy_id = create_test_tenancy(client, app)

    client.post(
        "/api/rent/generate",
        json={"tenancy_id": tenancy_id, "month": "2026-11"}
    )

    client.post("/auth/logout")
    client.post(
        "/auth/login",
        json={
            "email": "renttenant@example.com",
            "password": "PrimeStay123!"
        }
    )

    response = client.get("/api/rent/obligations")

    assert response.status_code == 200
    result = response.get_json()
    assert result["count"] == 1
    assert result["obligations"][0]["tenancy_id"] == tenancy_id


def test_rent_obligations_requires_login(client):
    response = client.get("/api/rent/obligations")

    assert response.status_code == 401


def test_landlord_sees_only_own_rent_obligations(client, app):
    first_tenancy_id = create_test_tenancy(client, app)
    # Generate rent for the first landlord's tenancy.
    first_rent_response = client.post(
        "/api/rent/generate",
        json={
            "tenancy_id": first_tenancy_id,
            "month": "2026-11"
        }
    )

    assert first_rent_response.status_code == 201

    # Create a second independent landlord and tenancy.
    client.post("/auth/logout")

    client.post(
        "/auth/register",
        json={
            "full_name": "Second Landlord",
            "email": "secondlandlord@example.com",
            "password": "PrimeStay123!",
            "role": "landlord"
        }
    )

    client.post(
        "/auth/login",
        json={
            "email": "secondlandlord@example.com",
            "password": "PrimeStay123!"
        }
    )


    property_response = client.post(
        "/api/properties",
        json={
            "property_name": "Second Apartment",
            "property_type": "apartment",
            "address_line": "Vijay Nagar",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "postal_code": "452010",
            "bedrooms": 2,
            "bathrooms": 2
        }
    )
    assert property_response.status_code == 201, property_response.get_json()
    second_property_id = property_response.get_json()["property"]["id"]

    client.post("/auth/logout")

    client.post(
        "/auth/login",
        json={
            "email": "renttenant@example.com",
            "password": "PrimeStay123!"
        }
    )

    second_tenancy_response = client.post(
        "/auth/register",
        json={
            "full_name": "Second Tenant",
            "email": "secondtenant@example.com",
            "password": "PrimeStay123!",
            "role": "tenant"
        }
    )
    assert second_tenancy_response.status_code == 201

    client.post("/auth/logout")
    client.post(
        "/auth/login",
        json={
            "email": "secondlandlord@example.com",
            "password": "PrimeStay123!"
        }
    )

    second_tenancy_response = client.post(
        "/api/tenancies",
        json={
            "property_id": second_property_id,
            "tenant_id": second_tenancy_response.get_json()["user"]["id"],
            "start_date": "2026-11-15",
            "monthly_rent": 12000,
            "security_deposit": 5000,
            "rent_due_day": 5
        }
    )
    assert second_tenancy_response.status_code == 201

    second_tenancy_id = second_tenancy_response.get_json()["tenancy"]["id"]

    client.post(
        "/api/rent/generate",
        json={"tenancy_id": second_tenancy_id, "month": "2026-11"}
    )

    # Log back in as the first landlord.
    client.post("/auth/logout")
    client.post(
        "/auth/login",
        json={
            "email": "rentlandlord@example.com",
            "password": "PrimeStay123!"
        }
    )

    response = client.get("/api/rent/obligations")

    assert response.status_code == 200
    result = response.get_json()

    assert result["count"] == 1
    assert result["obligations"][0]["tenancy_id"] == first_tenancy_id











def test_tenant_can_record_payment(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post(
        "/api/rent/generate",
        json={
            "tenancy_id": tenancy_id,
            "month": "2026-12"
        }
    )
    assert generate_response.status_code == 201

    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    login_response = client.post(
        "/auth/login",
        json={
            "email": "renttenant@example.com",
            "password": "PrimeStay123!"
        }
    )
    assert login_response.status_code == 200

    response = client.post(
        "/api/rent/payments",
        json={
            "rent_obligation_id": obligation_id,
            "amount": "5000.00",
            "payment_date": "2026-12-05",
            "payment_method": "upi",
            "reference_number": "UPI-TEST-001",
            "notes": "December rent payment"
        }
    )

    assert response.status_code == 201

    result = response.get_json()
    assert result["payment"]["amount"] == "5000.00"
    assert result["payment"]["status"] == "recorded"
    assert result["payment"]["payment_method"] == "upi"

    with app.app_context():
        obligation = db.session.get(RentObligation, obligation_id)

        assert calculate_verified_amount(obligation) == Decimal("0.00")
        assert calculate_outstanding_amount(obligation) == Decimal("12000.00")



def test_tenant_cannot_pay_another_tenants_obligation(client, app):
    first_tenancy_id = create_test_tenancy(client, app)

    client.post("/auth/logout")

    client.post("/auth/register", json={
        "full_name": "Second Tenant",
        "email": "secondtenant@example.com",
        "password": "PrimeStay123!",
        "role": "tenant"
    })

    client.post("/auth/login", json={
        "email": "secondtenant@example.com",
        "password": "PrimeStay123!"
    })

    client.post("/auth/logout")

    # Log in as the landlord and create a second property.
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!"
    })

    second_tenant_id = None
    with app.app_context():
        second_tenant = User.query.filter_by(
            email="secondtenant@example.com"
        ).first()
        second_tenant_id = second_tenant.id

    property_response = client.post("/api/properties", json={
        "property_name": "Second Rental Property",
        "property_type": "apartment",
        "address_line": "22 Test Road",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001",
        "bedrooms": 2,
        "bathrooms": 1
    })
    assert property_response.status_code == 201

    second_property_id = property_response.get_json()["property"]["id"]

    second_tenancy_response = client.post("/api/tenancies", json={
        "property_id": second_property_id,
        "tenant_id": second_tenant_id,
        "start_date": "2026-11-15",
        "monthly_rent": 12000,
        "security_deposit": 5000,
        "rent_due_day": 5
    })
    assert second_tenancy_response.status_code == 201

    # Generate an obligation for the first tenant.
    first_rent_response = client.post("/api/rent/generate", json={
        "tenancy_id": first_tenancy_id,
        "month": "2026-12"
    })
    assert first_rent_response.status_code == 201

    first_obligation_id = first_rent_response.get_json()["obligation"]["id"]

    # Log in as the second tenant and attempt to pay the first tenant's rent.
    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "secondtenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": first_obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })

    assert response.status_code == 404
    assert response.get_json()["error"] == "Rent obligation not found."



def test_pending_payment_amount_is_reserved_to_prevent_overpayment(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    assert generate_response.status_code == 201

    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    first_payment = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "8000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    assert first_payment.status_code == 201

    second_payment = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-06",
        "payment_method": "upi"
    })

    assert second_payment.status_code == 409
    assert "exceeds" in second_payment.get_json()["error"].lower()

    with app.app_context():
        payments = Payment.query.filter_by(
            rent_obligation_id=obligation_id
        ).all()

        assert len(payments) == 1
        assert payments[0].status == "recorded"
        assert payments[0].amount == Decimal("8000.00")



@pytest.mark.parametrize("invalid_amount", [
    0,
    -500,
    "abc",
    "100.999",
    True
])
def test_invalid_payment_amount_is_rejected(client, app, invalid_amount):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": invalid_amount,
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })

    assert response.status_code == 400


@pytest.mark.parametrize("invalid_date", [
    "2026-13-05",
    "05-12-2026",
    "not-a-date"
])
def test_invalid_payment_date_is_rejected(client, app, invalid_date):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": invalid_date,
        "payment_method": "upi"
    })

    assert response.status_code == 400


def test_invalid_payment_method_is_rejected(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "bitcoin"
    })

    assert response.status_code == 400



def test_payment_recording_requires_login(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })

    assert response.status_code == 401



def test_payment_recording_requires_login(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")

    response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })

    assert response.status_code == 401



def test_landlord_can_verify_tenant_payment(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    assert generate_response.status_code == 201

    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    payment_response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    assert payment_response.status_code == 201

    payment_id = payment_response.get_json()["payment"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!"
    })

    verify_response = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "verify"}
    )

    assert verify_response.status_code == 200
    assert verify_response.get_json()["payment"]["status"] == "verified"

    with app.app_context():
        obligation = db.session.get(RentObligation, obligation_id)

        assert calculate_verified_amount(obligation) == Decimal("5000.00")
        assert calculate_outstanding_amount(obligation) == Decimal("7000.00")
        assert obligation.status == "partially_paid"


def test_landlord_can_reject_tenant_payment(client, app):
    tenancy_id = create_test_tenancy(client, app)

    generate_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    assert generate_response.status_code == 201

    obligation_id = generate_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    payment_response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    assert payment_response.status_code == 201

    payment_id = payment_response.get_json()["payment"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!"
    })

    reject_response = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "reject"}
    )

    assert reject_response.status_code == 200
    assert reject_response.get_json()["payment"]["status"] == "rejected"

    with app.app_context():
        obligation = db.session.get(RentObligation, obligation_id)

        assert calculate_verified_amount(obligation) == Decimal("0.00")
        assert calculate_outstanding_amount(obligation) == Decimal("12000.00")
        assert obligation.status == "pending"



def test_landlord_cannot_verify_another_landlords_payment(client, app):
    first_tenancy_id = create_test_tenancy(client, app)

    first_rent = client.post("/api/rent/generate", json={
        "tenancy_id": first_tenancy_id,
        "month": "2026-12"
    })
    assert first_rent.status_code == 201

    first_obligation_id = first_rent.get_json()["obligation"]["id"]

    # Create a second independent landlord.
    client.post("/auth/logout")
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

    second_property = client.post("/api/properties", json={
        "property_name": "Second Landlord Property",
        "property_type": "apartment",
        "address_line": "25 Test Road",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "postal_code": "452001",
        "bedrooms": 2,
        "bathrooms": 1
    })
    assert second_property.status_code == 201

    # Record the first tenant's payment.
    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    payment_response = client.post("/api/rent/payments", json={
        "rent_obligation_id": first_obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    assert payment_response.status_code == 201

    payment_id = payment_response.get_json()["payment"]["id"]

    # Second landlord attempts to verify the first landlord's payment.
    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "secondlandlord@example.com",
        "password": "PrimeStay123!"
    })

    response = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "verify"}
    )

    assert response.status_code == 404

    with app.app_context():
        payment = db.session.get(Payment, payment_id)
        assert payment.status == "recorded"



def test_verified_payment_cannot_be_reviewed_again(client, app):
    tenancy_id = create_test_tenancy(client, app)

    rent_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = rent_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    payment_response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    assert payment_response.status_code == 201

    payment_id = payment_response.get_json()["payment"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!"
    })

    first_review = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "verify"}
    )
    assert first_review.status_code == 200

    second_review = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "reject"}
    )

    assert second_review.status_code == 409

    with app.app_context():
        payment = db.session.get(Payment, payment_id)
        assert payment.status == "verified"



def test_invalid_payment_review_action_is_rejected(client, app):
    tenancy_id = create_test_tenancy(client, app)

    rent_response = client.post("/api/rent/generate", json={
        "tenancy_id": tenancy_id,
        "month": "2026-12"
    })
    obligation_id = rent_response.get_json()["obligation"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "renttenant@example.com",
        "password": "PrimeStay123!"
    })

    payment_response = client.post("/api/rent/payments", json={
        "rent_obligation_id": obligation_id,
        "amount": "5000",
        "payment_date": "2026-12-05",
        "payment_method": "upi"
    })
    payment_id = payment_response.get_json()["payment"]["id"]

    client.post("/auth/logout")
    client.post("/auth/login", json={
        "email": "rentlandlord@example.com",
        "password": "PrimeStay123!"
    })

    response = client.patch(
        f"/api/rent/payments/{payment_id}/verify",
        json={"action": "approve"}
    )

    assert response.status_code == 400

    with app.app_context():
        payment = db.session.get(Payment, payment_id)
        assert payment.status == "recorded"
