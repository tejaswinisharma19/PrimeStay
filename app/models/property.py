
from app.extensions import db


class Property(db.Model):

    __tablename__ = "properties"

    __table_args__ = (
        db.CheckConstraint(
            "property_type IN ('apartment', 'house')",
            name="ck_properties_type"
        ),
        db.CheckConstraint(
            "bedrooms IS NULL OR bedrooms >= 0",
            name="ck_properties_bedrooms"
        ),
        db.CheckConstraint(
            "bathrooms IS NULL OR bathrooms >= 0",
            name="ck_properties_bathrooms"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    landlord_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    property_name = db.Column(
        db.String(150),
        nullable=False
    )

    property_type = db.Column(
        db.String(30),
        nullable=False
    )

    address_line = db.Column(
        db.String(255),
        nullable=False
    )

    city = db.Column(
        db.String(100),
        nullable=False
    )

    state = db.Column(
        db.String(100),
        nullable=False
    )

    postal_code = db.Column(
        db.String(10),
        nullable=False
    )

    bedrooms = db.Column(
        db.Integer,
        nullable=True
    )

    bathrooms = db.Column(
        db.Integer,
        nullable=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=db.true()
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )
    
    landlord = db.relationship(
        "User",
        back_populates="properties"
    )
    
    tenancies = db.relationship(
        "Tenancy",
        back_populates="property",
        lazy=True
    )

    def __repr__(self):
        return f"<Property {self.property_name}>"
