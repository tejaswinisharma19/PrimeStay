
from app.extensions import db


class User(db.Model):

    __tablename__ = "users"

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('landlord', 'tenant', 'maintenance_staff', 'admin')",
            name="ck_users_role"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    full_name = db.Column(
        db.String(150),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    role = db.Column(
        db.String(30),
        nullable=False
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
    
    properties = db.relationship(
        "Property",
        back_populates="landlord",
        lazy=True
    )
    
    tenancies = db.relationship(
        "Tenancy",
        back_populates="tenant",
        foreign_keys="Tenancy.tenant_id",
        lazy=True
    )
    
    recorded_payments = db.relationship(
        "Payment",
        back_populates="recorder",
        foreign_keys="Payment.recorded_by",
        lazy=True
    )

    def __repr__(self):
        return f"<User {self.email}>"
