from flask import Blueprint


bp = Blueprint('main', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static/main')

from juniper.app.main import routes
from juniper.app.main import models
