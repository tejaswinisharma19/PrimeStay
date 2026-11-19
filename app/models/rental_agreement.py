
from app.extensions import db


class RentalAgreement(db.Model):

    __tablename__ = "rental_agreements"

    __table_args__ = (

        db.CheckConstraint(
            "agreement_type IN ('initial', 'renewal')",
            name="ck_rental_agreements_type"
        ),

        db.CheckConstraint(
            "status IN ('draft', 'signed', 'expired', 'terminated')",
            name="ck_rental_agreements_status"
        ),

        db.CheckConstraint(
            "end_date >= start_date",
            name="ck_rental_agreements_dates"
        ),

        db.UniqueConstraint(
            "agreement_number",
            name="uq_rental_agreements_number"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    tenancy_id = db.Column(
        db.Integer,
        db.ForeignKey("tenancies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    agreement_number = db.Column(
        db.String(50),
        nullable=False
    )

    agreement_type = db.Column(
        db.String(20),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    signed_on = db.Column(
        db.Date,
        nullable=True
    )

    document_path = db.Column(
        db.String(500),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="draft"
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
    
    tenancy = db.relationship(
        "Tenancy",
        back_populates="rental_agreements"
    )

    def __repr__(self):
        return (
            f"<RentalAgreement {self.agreement_number}: "
            f"tenancy={self.tenancy_id}>"
        )
