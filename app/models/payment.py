
from app.extensions import db


class Payment(db.Model):

    __tablename__ = "payments"

    __table_args__ = (

        db.CheckConstraint(
            "amount > 0",
            name="ck_payments_amount"
        ),

        db.CheckConstraint(
            "payment_method IN ('cash', 'upi', 'bank_transfer', 'cheque', 'other')",
            name="ck_payments_method"
        ),

        db.CheckConstraint(
            "status IN ('recorded', 'verified', 'rejected')",
            name="ck_payments_status"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    rent_obligation_id = db.Column(
        db.Integer,
        db.ForeignKey("rent_obligations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    recorded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    payment_date = db.Column(
        db.Date,
        nullable=False
    )

    payment_method = db.Column(
        db.String(30),
        nullable=False
    )

    reference_number = db.Column(
        db.String(100),
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="recorded"
    )

    notes = db.Column(
        db.Text,
        nullable=True
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
    
    rent_obligation = db.relationship(
        "RentObligation",
        back_populates="payments"
    )

    recorder = db.relationship(
        "User",
        back_populates="recorded_payments",
        foreign_keys=[recorded_by]
    )

    def __repr__(self):
        return (
            f"<Payment {self.id}: "
            f"amount={self.amount}, "
            f"status={self.status}>"
        )

