
from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions import db

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def home():
    return jsonify({
        "application": "PrimeStay",
        "message": "Welcome to PrimeStay!",
        "status": "running"
    })


@main.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "application": "PrimeStay"
    })


@main.route("/health/db", methods=["GET"])
def database_health():
    result = db.session.execute(
        text("SELECT current_database(), current_user")
    ).one()

    return jsonify({
        "status": "connected",
        "database": result[0],
        "user": result[1]
    })
