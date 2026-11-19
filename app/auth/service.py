

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User

from app.auth.security import (
    hash_password,
    verify_password,
    validate_password
)


ALLOWED_REGISTRATION_ROLES = {
    "landlord",
    "tenant"
}


def register_user(full_name, email, password, phone, role):

    # 1. Validate required fields.
    if not full_name or not email or not password or not role:
        return None, "All required fields must be provided."

    # 2. Normalize user input.
    full_name = full_name.strip()
    email = email.strip()
    role = role.strip().lower()

    # 3. Validate role.
    if role not in ALLOWED_REGISTRATION_ROLES:
        return None, "Invalid registration role."

    # 4. Validate name and email.
    if not full_name:
        return None, "Full name cannot be empty."

    if len(full_name) > 150:
        return None, "Full name is too long."

    # Email addresses must be lowercase.
    if email != email.lower():
        return None, "Email address must contain lowercase letters only."

    # Email length must not exceed 255 characters.
    if len(email) > 255:
        return None, "Email address cannot exceed 255 characters."

    # Basic email structure validation.
    if (
        email.count("@") != 1
        or email.startswith("@")
        or email.endswith("@")
        or "." not in email.split("@")[1]
    ):
        return None, "Invalid email address."

    # 5. Validate password.
    password_error = validate_password(password)

    if password_error:
      return None, password_error

    # 6. Check whether email already exists.
    existing_user = db.session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    if existing_user:
        return None, "An account with this email already exists."

    # 7. Create the user.
    user = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password),
        phone=phone.strip() if phone else None,
        role=role
    )

    # 8. Save user in PostgreSQL.
    try:
        db.session.add(user)
        db.session.commit()

        return user, None

    except IntegrityError:
        db.session.rollback()

        return None, "Unable to create account. Please check the details."



def authenticate_user(email, password):

    # 1. Validate input.
    if not isinstance(email, str) or not isinstance(password, str):
        return None, "Invalid email or password."

    if not email.strip() or not password:
        return None, "Invalid email or password."

    # 2. Normalize and validate email.
    email = email.strip()

    if email != email.lower():
       return None, "Email address must contain lowercase letters only."

    if len(email) > 255:
       return None, "Email address cannot exceed 255 characters."

    # 3. Find the user in PostgreSQL.
    user = db.session.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()

    # 4. Reject unknown users.
    if user is None:
        return None, "Invalid email or password."

    # 5. Verify the entered password.
    if not verify_password(user.password_hash, password):
        return None, "Invalid email or password."

    # 6. Reject inactive accounts.
    if not user.is_active:
        return None, "This account is inactive."

    # 7. Return authenticated user.
    return user, None
