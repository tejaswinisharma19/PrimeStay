from flask import Blueprint


properties = Blueprint(
    "properties",
    __name__,
    url_prefix="/api/properties"
)


from app.properties import routes