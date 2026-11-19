
from app.extensions import db


class Tenancy(db.Model):

    __tablename__ = "tenancies"

    __table_args__ = (

        db.CheckConstraint(
            "monthly_rent > 0",
            name="ck_tenancies_monthly_rent"
        ),

        db.CheckConstraint(
            "security_deposit >= 0",
            name="ck_tenancies_security_deposit"
        ),

        db.CheckConstraint(
            "rent_due_day BETWEEN 1 AND 28",
            name="ck_tenancies_rent_due_day"
        ),

        db.CheckConstraint(
            "status IN ('active', 'completed', 'terminated')",
            name="ck_tenancies_status"
        ),

        db.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_tenancies_dates"
        ),

        db.Index(
            "uq_tenancies_one_active_per_property",
            "property_id",
            unique=True,
            postgresql_where=db.text("status = 'active'")
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    property_id = db.Column(
        db.Integer,
        db.ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=True
    )

    monthly_rent = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    security_deposit = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0
    )

    rent_due_day = db.Column(
        db.SmallInteger,
        nullable=False,
        default=5
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active"
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
    
    property = db.relationship(
        "Property",
        back_populates="tenancies"
    )

    tenant = db.relationship(
        "User",
        back_populates="tenancies",
        foreign_keys=[tenant_id]
    )
    
    rental_agreements = db.relationship(
        "RentalAgreement",
        back_populates="tenancy",
        lazy=True
    )
    
    rent_obligations = db.relationship(
        "RentObligation",
        back_populates="tenancy",
        lazy=True
    )

    def __repr__(self):
        return f"<Tenancy {self.id}: property={self.property_id}, tenant={self.tenant_id}>"
