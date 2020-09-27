from flask import Blueprint

bp = Blueprint('products', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.product import models
from juniper.app.product import routes
