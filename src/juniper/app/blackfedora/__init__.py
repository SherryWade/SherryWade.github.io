from flask import Blueprint

bp = Blueprint('blackfedora', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static/blackfedora')

from juniper.app.blackfedora import routes
