
from app import create_app
from app.extensions import db
from app.models import User, Property


app = create_app()

with app.app_context():

    # Find Rahul and Amit.
    rahul = db.session.get(User, 5)
    amit = db.session.get(User, 15)

    if not rahul or not amit:
        raise RuntimeError("Test landlord accounts not found.")

    # Check whether test properties already exist.
    rahul_property = Property.query.filter_by(
        property_name="Rahul Test Apartment",
        landlord_id=rahul.id
    ).first()

    amit_property = Property.query.filter_by(
        property_name="Amit Test Apartment",
        landlord_id=amit.id
    ).first()

    # Create Rahul's property if it does not exist.
    if not rahul_property:

        rahul_property = Property(
            landlord_id=rahul.id,
            property_name="Rahul Test Apartment",
            property_type="apartment",
            address_line="101 Test Street",
            city="Indore",
            state="Madhya Pradesh",
            postal_code="452001",
            bedrooms=2,
            bathrooms=2
        )

        db.session.add(rahul_property)

    # Create Amit's property if it does not exist.
    if not amit_property:

        amit_property = Property(
            landlord_id=amit.id,
            property_name="Amit Test Apartment",
            property_type="apartment",
            address_line="202 Test Street",
            city="Indore",
            state="Madhya Pradesh",
            postal_code="452002",
            bedrooms=3,
            bathrooms=2
        )

        db.session.add(amit_property)

    # Save both properties.
    db.session.commit()

    print("OWNERSHIP TEST DATA CREATED")
    print("--------------------------------")

    print(
        "Rahul:",
        rahul_property.id if rahul_property.id else "Pending"
    )

    print(
        "Amit:",
        amit_property.id if amit_property.id else "Pending"
    )
