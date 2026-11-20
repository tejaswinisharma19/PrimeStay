
from flask import Blueprint

# Create the rental agreements Blueprint.
agreements = Blueprint(
    "agreements",
    __name__,
    url_prefix="/api/agreements"
)

# Import routes so Flask can register them.
from app.agreements import routes
