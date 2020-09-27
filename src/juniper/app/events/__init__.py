from flask import Blueprint

bp = Blueprint('events', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.events import models
from juniper.app.events import routes
