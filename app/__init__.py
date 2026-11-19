
import os

from flask import Flask
from dotenv import load_dotenv
from sqlalchemy import URL

from app.extensions import db, migrate


def create_app():

    load_dotenv()

    app = Flask(__name__)
    
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is missing from environment variables.")

    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB")
    )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Import models so SQLAlchemy can detect their tables.
    from app import models

    # Connect Flask-Migrate to Flask and SQLAlchemy.
    migrate.init_app(app, db)

    from app.routes import main
    from app.auth.routes import auth
    from app.rbac_test_routes import rbac_test

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(rbac_test)
    
    return app
