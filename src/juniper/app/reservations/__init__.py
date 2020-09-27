from flask import Blueprint, current_app, g

bp = Blueprint('reservations', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.reservations import models
from juniper.app.reservations import routes