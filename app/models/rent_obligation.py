
from app.extensions import db


class RentObligation(db.Model):

    __tablename__ = "rent_obligations"

    __table_args__ = (

        db.CheckConstraint(
            "amount_due > 0",
            name="ck_rent_obligations_amount_due"
        ),

        db.CheckConstraint(
            "period_end >= period_start",
            name="ck_rent_obligations_period_dates"
        ),

        db.CheckConstraint(
            "due_date >= period_start AND due_date <= period_end",
            name="ck_rent_obligations_due_date"
        ),

        db.CheckConstraint(
            "status IN ('pending', 'partially_paid', 'paid')",
            name="ck_rent_obligations_status"
        ),

        db.UniqueConstraint(
            "tenancy_id",
            "period_start",
            name="uq_rent_obligations_tenancy_period"
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

    period_start = db.Column(
        db.Date,
        nullable=False
    )

    period_end = db.Column(
        db.Date,
        nullable=False
    )

    amount_due = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    due_date = db.Column(
        db.Date,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
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
        back_populates="rent_obligations"
    )
    
    payments = db.relationship(
        "Payment",
        back_populates="rent_obligation",
        lazy=True
    )

    def __repr__(self):
        return (
            f"<RentObligation {self.id}: "
            f"tenancy={self.tenancy_id}, "
            f"amount={self.amount_due}>"
        )
