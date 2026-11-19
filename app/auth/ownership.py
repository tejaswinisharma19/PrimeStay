
from app.models import Property


def get_landlord_property(property_id, landlord_id):

    """
    Retrieve a property only if it belongs to
    the currently authenticated landlord.
    """

    property = Property.query.filter_by(
        id=property_id,
        landlord_id=landlord_id
    ).first()

    return property
