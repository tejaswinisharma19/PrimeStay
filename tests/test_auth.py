
from xmlrpc import client


def test_user_can_register(client):

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Landlord",
            "email": "test.landlord@example.com",
            "password": "TestPassword123!",
            "role": "landlord"
        }
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Account created successfully."
    assert data["user"]["full_name"] == "Test Landlord"
    assert data["user"]["email"] == "test.landlord@example.com"
    assert data["user"]["role"] == "landlord"


def test_registered_password_is_hashed(client):

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Hash Test User",
            "email": "hash.test@example.com",
            "password": "TestPassword123!",
            "role": "landlord"
        }
    )

    assert response.status_code == 201

    from app.models import User

    user = User.query.filter_by(
        email="hash.test@example.com"
    ).first()

    assert user is not None
    assert user.password_hash != "TestPassword123!"
    assert user.password_hash.startswith("scrypt:")



def test_duplicate_email_registration_is_rejected(client):

    user_data = {
        "full_name": "Duplicate Test User",
        "email": "duplicate.test@example.com",
        "password": "TestPassword123!",
        "role": "landlord"
    }

    # First registration should succeed.
    first_response = client.post(
        "/auth/register",
        json=user_data
    )

    assert first_response.status_code == 201

    # Second registration uses the same email.
    second_response = client.post(
        "/auth/register",
        json=user_data
    )

    assert second_response.status_code == 409

    data = second_response.get_json()

    assert data["error"] == (
        "An account with this email already exists."
    )

def test_user_can_login(client):

    # First, register a test user.
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "Login Test User",
            "email": "login.test@example.com",
            "password": "LoginPassword123!",
            "role": "landlord"
        }
    )

    assert registration_response.status_code == 201

    # Now log in using the registered credentials.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "login.test@example.com",
            "password": "LoginPassword123!"
        }
    )

    assert login_response.status_code == 200

    data = login_response.get_json()

    assert data["message"] == "Login successful."
    assert data["user"]["email"] == "login.test@example.com"
    assert data["user"]["role"] == "landlord"


def test_login_rejects_incorrect_password(client):

    # Register a test user.
    client.post(
        "/auth/register",
        json={
            "full_name": "Wrong Password User",
            "email": "wrong.password@example.com",
            "password": "CorrectPassword123!",
            "role": "landlord"
        }
    )

    # Attempt login with an incorrect password.
    response = client.post(
        "/auth/login",
        json={
            "email": "wrong.password@example.com",
            "password": "WrongPassword123!"
        }
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Invalid email or password."



def test_logged_in_user_can_access_profile(client):

    # Register a user.
    client.post(
        "/auth/register",
        json={
            "full_name": "Profile Test User",
            "email": "profile.test@example.com",
            "password": "ProfilePassword123!",
            "role": "landlord"
        }
    )

    # Log in.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "profile.test@example.com",
            "password": "ProfilePassword123!"
        }
    )

    assert login_response.status_code == 200

    # Access the current user's profile.
    response = client.get("/auth/me")

    assert response.status_code == 200

    data = response.get_json()

    assert data["authenticated"] is True
    assert data["user"]["email"] == "profile.test@example.com"
    assert data["user"]["role"] == "landlord"



def test_unauthenticated_user_cannot_access_profile(client):

    response = client.get("/auth/me")

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Authentication required."


def test_logout_clears_session(client):

    # Register a user.
    registration_response = client.post(
        "/auth/register",
        json={
            "full_name": "Logout Test User",
            "email": "logout.test@example.com",
            "password": "TestPassword123@",
            "role": "landlord"
      }
    )

    assert registration_response.status_code == 201, (
        f"Registration failed: {registration_response.get_json()}"
    )

    # Log in.
    login_response = client.post(
        "/auth/login",
        json={
            "email": "logout.test@example.com",
            "password": "TestPassword123@"
        }
    )

    assert login_response.status_code == 200, (
        f"Login failed: {login_response.get_json()}"
    )

    # Confirm the user is logged in.
    profile_response = client.get("/auth/me")

    assert profile_response.status_code == 200

    # Log out.
    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 200

    # Confirm the session has been cleared.
    profile_after_logout = client.get("/auth/me")

    assert profile_after_logout.status_code == 401
