
from app import create_app
from app.extensions import db
from app.models import Property, User


app = create_app()

with app.app_context():

    # Find the two temporary test properties.
    rahul_property = Property.query.filter_by(
        id=2,
        landlord_id=5,
        property_name="Rahul Test Apartment"
    ).first()

    amit_property = Property.query.filter_by(
        id=3,
        landlord_id=15,
        property_name="Amit Test Apartment"
    ).first()

    # Find Amit's temporary test account.
    amit = User.query.filter_by(
        id=15,
        email="amit.primestay.test@example.com"
    ).first()

    # Delete temporary properties.
    if rahul_property:
        db.session.delete(rahul_property)

    if amit_property:
        db.session.delete(amit_property)

    # Delete Amit only if his test properties were found
    # and there are no other properties or tenancies.
    if amit:
        if amit.properties or amit.tenancies:
            raise RuntimeError(
                "Amit has related records. Cleanup stopped."
            )

        db.session.delete(amit)

    db.session.commit()

    print("Temporary ownership test data cleaned up.")
