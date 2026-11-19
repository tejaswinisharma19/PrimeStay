
import pytest

from app.auth.security import validate_password
from app.auth.service import register_user


@pytest.mark.parametrize(
    "password, expected_error",
    [
        (
            "PrimeStay123!",
            None
        ),
        (
            "Prime123!",
            "Password must contain at least 10 characters."
        ),
        (
            "primestay123!",
            "Password must contain at least one uppercase letter."
        ),
        (
            "PRIMESTAY123!",
            "Password must contain at least one lowercase letter."
        ),
        (
            "PrimeStayABC!",
            "Password must contain at least one number."
        ),
        (
            "PrimeStay1234",
            "Password must contain at least one special character."
        ),
        (
            "A" * 129 + "a1!",
            "Password cannot exceed 128 characters."
        ),
        (
            "A" * 125 + "a1!",
            None
        ),
    ]
)
def test_password_validation(password, expected_error):

    result = validate_password(password)

    assert result == expected_error


@pytest.mark.parametrize(
    "email, expected_error",
    [
        (
            "TestUser@example.com",
            "Email address must contain lowercase letters only."
        ),
        (
            "invalid-email",
            "Invalid email address."
        ),
        (
            "a" * 245 + "@example.com",
            "Email address cannot exceed 255 characters."
        ),
    ]
)
def test_email_validation(app, email, expected_error):

    with app.app_context():

        user, error = register_user(
            full_name="Validation Test User",
            email=email,
            password="PrimeStay123!",
            phone=None,
            role="tenant"
        )

        assert user is None
        assert error == expected_error
