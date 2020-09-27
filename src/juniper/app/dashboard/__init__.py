from flask import Blueprint

bp = Blueprint('dashboard', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.dashboard import routes
