
from flask import Blueprint

tenancies = Blueprint(
    "tenancies",
    __name__,
    url_prefix="/api/tenancies"
)

from app.tenancies import routes