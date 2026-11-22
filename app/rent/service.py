
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.extensions import db
from app.models import RentObligation, Payment


def calculate_period_amount(
    monthly_rent: Decimal,
    period_start: date,
    period_end: date
) -> Decimal:
    """
    Calculate rent for the occupied days in one calendar month.

    Both period_start and period_end are inclusive.
    """

    monthly_rent = Decimal(str(monthly_rent))

    if monthly_rent <= 0:
        raise ValueError("Monthly rent must be greater than zero.")

    if period_start > period_end:
        raise ValueError("Period start cannot be after period end.")

    if (
        period_start.year != period_end.year
        or period_start.month != period_end.month
    ):
        raise ValueError("The rental period must belong to one calendar month.")

    days_in_month = monthrange(
        period_start.year,
        period_start.month
    )[1]

    occupied_days = (period_end - period_start).days + 1

    daily_rent = monthly_rent / Decimal(days_in_month)
    prorated_amount = daily_rent * Decimal(occupied_days)

    return prorated_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_monthly_obligation(tenancy, target_month):
    """
    Generate one rent obligation for a tenancy and calendar month.

    Only active tenancies are eligible.
    Existing obligations are returned instead of duplicated.
    """

    if tenancy.status != "active":
        return None

    if not isinstance(target_month, date):
        raise ValueError("Target month must be a date.")

    month_start = date(target_month.year, target_month.month, 1)

    days_in_month = monthrange(
        target_month.year,
        target_month.month
    )[1]

    month_end = date(
        target_month.year,
        target_month.month,
        days_in_month
    )

    period_start = max(month_start, tenancy.start_date)
    period_end = month_end

    if tenancy.end_date is not None:
        period_end = min(month_end, tenancy.end_date)

    if period_start > period_end:
        return None

    existing = RentObligation.query.filter_by(
        tenancy_id=tenancy.id,
        period_start=period_start
    ).first()

    if existing:
        return existing

    amount_due = calculate_period_amount(
        Decimal(str(tenancy.monthly_rent)),
        period_start,
        period_end
    )

    due_day = min(tenancy.rent_due_day, days_in_month)

    due_date = date(
        target_month.year,
        target_month.month,
        due_day
    )

    due_date = max(period_start, min(due_date, period_end))

    obligation = RentObligation(
        tenancy_id=tenancy.id,
        period_start=period_start,
        period_end=period_end,
        amount_due=amount_due,
        due_date=due_date,
        status="pending"
    )

    db.session.add(obligation)
    db.session.flush()

    return obligation


def calculate_verified_amount(obligation):
    """
    Calculate the total amount of verified payments
    for a rent obligation.
    """

    total = db.session.query(
        db.func.coalesce(db.func.sum(Payment.amount), 0)
    ).filter_by(
        rent_obligation_id=obligation.id,
        status="verified"
    ).scalar()

    return Decimal(str(total or 0)).quantize(Decimal("0.01"))


def calculate_outstanding_amount(obligation):
    """
    Calculate the remaining rent after verified payments.
    """

    verified_amount = calculate_verified_amount(obligation)

    outstanding = Decimal(str(obligation.amount_due)) - verified_amount

    return max(
        outstanding,
        Decimal("0.00")
    ).quantize(Decimal("0.01"))


def update_obligation_status(obligation):
    """
    Update the rent obligation status based on verified payments.

    Allowed statuses:
    pending, partially_paid, paid
    """

    verified_amount = calculate_verified_amount(obligation)

    amount_due = Decimal(str(obligation.amount_due))

    if verified_amount > amount_due:
        raise ValueError(
            "Verified payments cannot exceed the amount due."
        )

    if verified_amount == amount_due:
        obligation.status = "paid"

    elif verified_amount > 0:
        obligation.status = "partially_paid"

    else:
        obligation.status = "pending"

    return obligation.status


def get_obligation_summary(obligation, today=None):
    """
    Return the financial summary of a rent obligation.

    Overdue status is calculated dynamically.
    """

    if today is None:
        today = date.today()

    verified_amount = calculate_verified_amount(obligation)

    outstanding_amount = calculate_outstanding_amount(obligation)

    is_overdue = (
        obligation.due_date < today
        and outstanding_amount > 0
    )

    return {
        "obligation_id": obligation.id,
        "amount_due": str(Decimal(str(obligation.amount_due))),
        "verified_amount": str(verified_amount),
        "outstanding_amount": str(outstanding_amount),
        "status": obligation.status,
        "due_date": obligation.due_date.isoformat(),
        "is_overdue": is_overdue
    }
