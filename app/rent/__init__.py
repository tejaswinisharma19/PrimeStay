from flask import Blueprint

rent = Blueprint(
    "rent",
    __name__,
    url_prefix="/api/rent"
)

from app.rent import routes