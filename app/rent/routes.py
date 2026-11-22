
from datetime import date
from decimal import Decimal, InvalidOperation
from flask import jsonify, request, g
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Tenancy, Property, RentObligation, Payment
from app.auth.decorators import role_required
from app.rent import rent
from app.rent.service import (
    generate_monthly_obligation,
    get_obligation_summary
)


@rent.route("/generate", methods=["POST"])
@role_required("landlord", "admin")
def generate_rent():

    # Receive JSON data.
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "A valid JSON request body is required."
        }), 400

    # Validate required fields.
    tenancy_id = data.get("tenancy_id")
    month_value = data.get("month")

    if tenancy_id is None:
        return jsonify({
            "error": "Tenancy ID is required."
        }), 400

    if isinstance(tenancy_id, bool) or not isinstance(tenancy_id, int) or tenancy_id <= 0:
        return jsonify({
            "error": "Tenancy ID must be a positive integer."
        }), 400

    # Validate month format.
    if not isinstance(month_value, str):
        return jsonify({
            "error": "Month must use YYYY-MM format."
        }), 400

    try:
        target_month = date.fromisoformat(month_value + "-01")

        if target_month.strftime("%Y-%m") != month_value:
            raise ValueError

    except ValueError:
        return jsonify({
            "error": "Month must use YYYY-MM format."
        }), 400

    # Find the tenancy.
    query = Tenancy.query.join(
        Property,
        Tenancy.property_id == Property.id
    ).filter(
        Tenancy.id == tenancy_id
    )

    # Landlords can only generate rent for their own properties.
    if g.current_user.role == "landlord":
        query = query.filter(
            Property.landlord_id == g.current_user.id
        )

    tenancy = query.first()

    if not tenancy:
        return jsonify({
            "error": "Tenancy not found."
        }), 404

    # Only active tenancies can generate new obligations.
    if tenancy.status != "active":
        return jsonify({
            "error": "Rent can only be generated for active tenancies."
        }), 400

    # Calculate the actual rental period start for this month.
    period_start = max(
        date(target_month.year, target_month.month, 1),
        tenancy.start_date
    )

    # Check whether this obligation already exists.
    existing = RentObligation.query.filter_by(
        tenancy_id=tenancy.id,
        period_start=period_start
    ).first()

    if existing:
        return jsonify({
            "message": "Rent obligation already exists.",
            "obligation": {
                "id": existing.id,
                "tenancy_id": existing.tenancy_id,
                "period_start": existing.period_start.isoformat(),
                "period_end": existing.period_end.isoformat(),
                "amount_due": str(existing.amount_due),
                "due_date": existing.due_date.isoformat(),
                "status": existing.status
            }
        }), 200

    # Generate and save the obligation.
    try:
        obligation = generate_monthly_obligation(
            tenancy,
            target_month
        )

        if obligation is None:
            return jsonify({
                "error": "The requested month does not overlap the tenancy."
            }), 400

        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        # Another request may have created this obligation simultaneously.
        existing = RentObligation.query.filter_by(
            tenancy_id=tenancy.id,
            period_start=period_start
        ).first()

        if existing:
            return jsonify({
                "message": "Rent obligation already exists.",
                "obligation": {
                    "id": existing.id,
                    "tenancy_id": existing.tenancy_id,
                    "period_start": existing.period_start.isoformat(),
                    "period_end": existing.period_end.isoformat(),
                    "amount_due": str(existing.amount_due),
                    "due_date": existing.due_date.isoformat(),
                    "status": existing.status
                }
            }), 200

        return jsonify({
            "error": "Unable to generate rent obligation."
        }), 409

    except Exception:
        db.session.rollback()

        return jsonify({
            "error": "Unable to generate rent obligation. Please try again."
        }), 500

    return jsonify({
        "message": "Rent obligation generated successfully.",
        "obligation": {
            "id": obligation.id,
            "tenancy_id": obligation.tenancy_id,
            "period_start": obligation.period_start.isoformat(),
            "period_end": obligation.period_end.isoformat(),
            "amount_due": str(obligation.amount_due),
            "due_date": obligation.due_date.isoformat(),
            "status": obligation.status
        }
    }), 201


@rent.route("/obligations", methods=["GET"])
@role_required("landlord", "tenant", "admin")
def list_rent_obligations():
    # Start with all rent obligations and connect them to their tenancy and property.
    query = (
        RentObligation.query
        .join(Tenancy, RentObligation.tenancy_id == Tenancy.id)
        .join(Property, Tenancy.property_id == Property.id)
    )

    # Landlords can only view rent obligations for their own properties.
    if g.current_user.role == "landlord":
        query = query.filter(Property.landlord_id == g.current_user.id)

    # Tenants can only view their own rent obligations.
    elif g.current_user.role == "tenant":
        query = query.filter(Tenancy.tenant_id == g.current_user.id)

    # Admins can view all rent obligations.

    obligations = query.order_by(
        RentObligation.period_start.desc()
    ).all()

    results = []

    for obligation in obligations:
        summary = get_obligation_summary(obligation)

        results.append({
            "obligation_id": obligation.id,
            "tenancy_id": obligation.tenancy_id,
            "property_name": obligation.tenancy.property.property_name,
            "period_start": obligation.period_start.isoformat(),
            "period_end": obligation.period_end.isoformat(),
            "amount_due": summary["amount_due"],
            "verified_amount": summary["verified_amount"],
            "outstanding_amount": summary["outstanding_amount"],
            "due_date": summary["due_date"],
            "status": (
                "overdue" if summary["is_overdue"]
                else summary["status"]
            )
        })

    return jsonify({
        "message": "Rent obligations retrieved successfully.",
        "count": len(results),
        "obligations": results
    }), 200




@rent.route("/payments", methods=["POST"])
@role_required("tenant", "admin")
def record_payment():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON object is required."}), 400

    obligation_id = data.get("rent_obligation_id")

    if isinstance(obligation_id, bool) or not isinstance(obligation_id, int) or obligation_id <= 0:
        return jsonify({"error": "A valid rent_obligation_id is required."}), 400

    raw_amount = data.get("amount")

    if isinstance(raw_amount, bool) or raw_amount is None:
        return jsonify({"error": "A valid payment amount is required."}), 400

    try:
        amount = Decimal(str(raw_amount))
    except (InvalidOperation, ValueError, TypeError):
        return jsonify({"error": "Payment amount must be a valid number."}), 400

    if not amount.is_finite() or amount <= 0 or amount > Decimal("99999999.99"):
        return jsonify({"error": "Payment amount must be greater than zero and within the allowed limit."}), 400

    if amount != amount.quantize(Decimal("0.01")):
        return jsonify({"error": "Payment amount cannot have more than two decimal places."}), 400

    raw_payment_date = data.get("payment_date")

    if not isinstance(raw_payment_date, str):
        return jsonify({"error": "payment_date is required in YYYY-MM-DD format."}), 400

    try:
        payment_date = date.fromisoformat(raw_payment_date)
        if payment_date.isoformat() != raw_payment_date:
            raise ValueError
    except ValueError:
        return jsonify({"error": "payment_date must use YYYY-MM-DD format."}), 400

    payment_method = data.get("payment_method")

    allowed_methods = {"cash", "upi", "bank_transfer", "cheque", "other"}

    if not isinstance(payment_method, str) or payment_method not in allowed_methods:
        return jsonify({"error": "Invalid payment_method."}), 400

    reference_number = data.get("reference_number")
    notes = data.get("notes")

    if reference_number is not None:
        if not isinstance(reference_number, str) or len(reference_number.strip()) > 100:
            return jsonify({"error": "reference_number must be a string of at most 100 characters."}), 400
        reference_number = reference_number.strip() or None

    if notes is not None:
        if not isinstance(notes, str) or len(notes) > 2000:
            return jsonify({"error": "notes must be a string of at most 2000 characters."}), 400

    obligation = (
        RentObligation.query
        .join(Tenancy, RentObligation.tenancy_id == Tenancy.id)
        .filter(RentObligation.id == obligation_id)
        .with_for_update()
        .first()
    )

    if obligation is None:
        return jsonify({"error": "Rent obligation not found."}), 404

    if g.current_user.role == "tenant" and obligation.tenancy.tenant_id != g.current_user.id:
        return jsonify({"error": "Rent obligation not found."}), 404

    reserved_amount = (
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter(
            Payment.rent_obligation_id == obligation.id,
            Payment.status.in_(["recorded", "verified"])
        )
        .scalar()
    )

    reserved_amount = Decimal(str(reserved_amount or 0))
    amount_due = Decimal(str(obligation.amount_due))

    if reserved_amount + amount > amount_due:
        return jsonify({
            "error": "Payment exceeds the remaining amount available for this rent obligation."
        }), 409

    payment = Payment(
        rent_obligation_id=obligation.id,
        recorded_by=g.current_user.id,
        amount=amount,
        payment_date=payment_date,
        payment_method=payment_method,
        reference_number=reference_number,
        notes=notes,
        status="recorded"
    )

    db.session.add(payment)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Payment could not be recorded. Please try again."}), 409

    return jsonify({
        "message": "Payment recorded successfully. It is awaiting verification.",
        "payment": {
            "id": payment.id,
            "rent_obligation_id": payment.rent_obligation_id,
            "amount": str(payment.amount),
            "payment_date": payment.payment_date.isoformat(),
            "payment_method": payment.payment_method,
            "reference_number": payment.reference_number,
            "status": payment.status
        }
    }), 201


@rent.route("/payments/<int:payment_id>/verify", methods=["PATCH"])
@role_required("landlord", "admin")
def verify_payment(payment_id):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "A valid JSON object is required."}), 400

    action = data.get("action")

    if action not in ("verify", "reject"):
        return jsonify({
            "error": "Action must be either verify or reject."
        }), 400

    payment = (
        Payment.query
        .join(RentObligation, Payment.rent_obligation_id == RentObligation.id)
        .join(Tenancy, RentObligation.tenancy_id == Tenancy.id)
        .join(Property, Tenancy.property_id == Property.id)
        .filter(Payment.id == payment_id)
        .with_for_update()
        .first()
    )

    if payment is None:
        return jsonify({"error": "Payment not found."}), 404

    if (
        g.current_user.role == "landlord"
        and payment.rent_obligation.tenancy.property.landlord_id != g.current_user.id
    ):
        return jsonify({"error": "Payment not found."}), 404

    if payment.status != "recorded":
        return jsonify({
            "error": "Only recorded payments can be verified or rejected."
        }), 409

    if action == "verify":

        obligation = (
            RentObligation.query
            .filter_by(id=payment.rent_obligation_id)
            .with_for_update()
            .first()
        )

        verified_amount = (
            db.session.query(
                db.func.coalesce(db.func.sum(Payment.amount), 0)
            )
            .filter(
                Payment.rent_obligation_id == obligation.id,
                Payment.status == "verified"
            )
            .scalar()
        )

        verified_amount = Decimal(str(verified_amount or 0))
        amount_due = Decimal(str(obligation.amount_due))

        if verified_amount + Decimal(str(payment.amount)) > amount_due:
            return jsonify({
                "error": "Verification would exceed the rent amount due."
            }), 409

        payment.status = "verified"

        obligation.status = (
            "paid"
            if verified_amount + Decimal(str(payment.amount)) == amount_due
            else "partially_paid"
        )

    else:
        payment.status = "rejected"

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "Payment review could not be completed."
        }), 409

    return jsonify({
        "message": (
            "Payment verified successfully."
            if action == "verify"
            else "Payment rejected successfully."
        ),
        "payment": {
            "id": payment.id,
            "rent_obligation_id": payment.rent_obligation_id,
            "amount": str(payment.amount),
            "status": payment.status
        }
    }), 200
