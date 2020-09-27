from flask import Blueprint

bp = Blueprint('auth', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.auth import models
from juniper.app.auth import routes
