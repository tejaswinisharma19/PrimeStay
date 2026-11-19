
import os

from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import URL

from app.extensions import db, migrate


def create_app(test_config=None):

    # Load environment variables from the .env file.
    load_dotenv()

    # Create the Flask application.
    app = Flask(__name__)

    # Configure application security.
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

    # Ensure that the secret key is configured.
    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY is missing from environment variables."
        )

    # Create the PostgreSQL database connection URL.
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB")
    )

    # Configure SQLAlchemy.
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Apply custom configuration before initializing extensions.
    if test_config:
        app.config.update(test_config)

    # Initialize Flask-SQLAlchemy with the application.
    db.init_app(app)

    # Import models so SQLAlchemy can detect all database tables.
    from app import models

    # Initialize Flask-Migrate.
    migrate.init_app(app, db)

    # Import application routes.
    from app.routes import main
    from app.auth.routes import auth

    # Register application blueprints.
    app.register_blueprint(main)
    app.register_blueprint(auth)

    # Register temporary RBAC routes only during automated testing.
    if app.config.get("TESTING"):
        from app.rbac_test_routes import rbac_test
        app.register_blueprint(rbac_test)

    return app
