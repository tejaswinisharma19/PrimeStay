
import os

import pytest
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db


# Load testing environment variables.
load_dotenv(".env.testing", override=True)


@pytest.fixture()
def app():

    # Read the testing database URL.
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL is missing."
        )

    # Parse and validate the database URL.
    parsed_url = make_url(database_url)

    if parsed_url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "Only PostgreSQL with psycopg is permitted."
        )

    if parsed_url.database != "primestay_test_db":
        raise RuntimeError(
            "Unsafe database! Tests must use primestay_test_db."
        )

    # Create the Flask application.
    application = create_app({
      "SQLALCHEMY_DATABASE_URI": database_url,
    "TESTING": True
   })

    with application.app_context():

        # Remove old test tables and create a clean database schema.
        db.drop_all()
        db.create_all()

        yield application

        # Remove database session and test tables after this test.
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
