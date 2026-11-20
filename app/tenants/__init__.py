
from flask import Blueprint

tenants = Blueprint(
    "tenants",
    __name__,
    url_prefix="/api/tenants"
)

from app.tenants import routes
