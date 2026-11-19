
from datetime import date
from uuid import uuid4

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db

from app.models import (
    User,
    Property,
    Tenancy,
    RentalAgreement,
    RentObligation,
    Payment
)


app = create_app()


with app.app_context():

    try:

        print("\nSTARTING DATABASE RELATIONSHIP TEST\n")

        # 1. Create a landlord
        landlord = User(
            full_name="Test Landlord",
            email=f"landlord_{uuid4().hex[:8]}@example.com",
            password_hash=generate_password_hash("TemporaryPassword123!"),
            role="landlord"
        )

        # 2. Create a tenant
        tenant = User(
            full_name="Test Tenant",
            email=f"tenant_{uuid4().hex[:8]}@example.com",
            password_hash=generate_password_hash("TemporaryPassword123!"),
            role="tenant"
        )

        db.session.add_all([landlord, tenant])
        db.session.flush()

        print("Landlord and tenant created.")

        # 3. Create a property belonging to the landlord
        property = Property(
            landlord=landlord,
            property_name="Test Apartment",
            property_type="apartment",
            address_line="Test Street",
            city="Indore",
            state="Madhya Pradesh",
            postal_code="452001",
            bedrooms=2,
            bathrooms=1
        )

        db.session.add(property)
        db.session.flush()

        print("Property linked to landlord.")

        # 4. Create a tenancy for the tenant
        tenancy = Tenancy(
            property=property,
            tenant=tenant,
            start_date=date(2026, 11, 1),
            monthly_rent=10000,
            security_deposit=20000,
            rent_due_day=5,
            status="active"
        )

        db.session.add(tenancy)
        db.session.flush()

        print("Tenancy linked to property and tenant.")

        # 5. Create a rental agreement
        agreement = RentalAgreement(
            tenancy=tenancy,
            agreement_number=f"TEST-{uuid4().hex[:8]}",
            agreement_type="initial",
            start_date=date(2026, 11, 1),
            end_date=date(2027, 10, 31),
            signed_on=date(2026, 11, 1),
            status="signed"
        )

        db.session.add(agreement)

        print("Rental agreement linked to tenancy.")

        # 6. Create November rent obligation
        rent = RentObligation(
            tenancy=tenancy,
            period_start=date(2026, 11, 1),
            period_end=date(2026, 11, 30),
            amount_due=10000,
            due_date=date(2026, 11, 5),
            status="partially_paid"
        )

        db.session.add(rent)
        db.session.flush()

        print("Rent obligation linked to tenancy.")

        # 7. Create first verified payment
        payment_1 = Payment(
            rent_obligation=rent,
            recorder=landlord,
            amount=4000,
            payment_date=date(2026, 11, 5),
            payment_method="upi",
            reference_number=f"TEST-UPI-{uuid4().hex[:8]}",
            status="verified"
        )

        # 8. Create second unconfirmed payment
        payment_2 = Payment(
            rent_obligation=rent,
            recorder=landlord,
            amount=3000,
            payment_date=date(2026, 11, 6),
            payment_method="cash",
            status="recorded"
        )

        db.session.add_all([payment_1, payment_2])

        db.session.flush()

        print("Both payment records created.")

        # 9. Verify relationships
        assert property.landlord.id == landlord.id
        assert property in landlord.properties

        assert tenancy.property.id == property.id
        assert tenancy.tenant.id == tenant.id
        assert tenancy in tenant.tenancies

        assert agreement in tenancy.rental_agreements
        assert rent in tenancy.rent_obligations

        assert payment_1 in rent.payments
        assert payment_2 in rent.payments

        assert payment_1.recorder.id == landlord.id

        print("\nALL RELATIONSHIP CHECKS PASSED!")

        # 10. Calculate verified payments only
        verified_total = (
            db.session.query(
                db.func.coalesce(db.func.sum(Payment.amount), 0)
            )
            .filter(
                Payment.rent_obligation_id == rent.id,
                Payment.status == "verified"
            )
            .scalar()
        )

        print("\nPAYMENT SUMMARY")
        print("---------------------------")
        print("Total rent due:       ₹10,000")
        print("Verified payments:   ₹", verified_total)
        print("Unconfirmed payment:  ₹3,000")
        print("Remaining balance:   ₹", rent.amount_due - verified_total)

        assert verified_total == 4000

        print("\nEND-TO-END DATABASE TEST PASSED!")

    except Exception:

        db.session.rollback()
        raise

    finally:

        # Remove all temporary test records.
        db.session.rollback()

        print("\nTemporary test records rolled back.")
