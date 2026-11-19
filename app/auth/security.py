
import re

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


def validate_password(password):
    """
    Validate the password against PrimeStay's password policy.

    Rules:
    - Minimum 10 characters
    - Maximum 128 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """

    if not isinstance(password, str):
        return "Password must be text."

    if len(password) < 10:
        return "Password must contain at least 10 characters."

    if len(password) > 128:
        return "Password cannot exceed 128 characters."

    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."

    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return "Password must contain at least one special character."

    return None


def hash_password(password):
    """
    Convert a plain-text password into a secure hash.
    """

    if not isinstance(password, str) or not password:
        raise ValueError("Password cannot be empty.")

    return generate_password_hash(password)


def verify_password(stored_hash, entered_password):
    """
    Verify an entered password against its stored hash.
    """

    if not stored_hash or not entered_password:
        return False

    return check_password_hash(
        stored_hash,
        entered_password
    )
