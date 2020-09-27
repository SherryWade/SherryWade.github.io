from flask import Blueprint

bp = Blueprint('payments', __name__,
               template_folder='templates',
               static_folder='static',
               static_url_path='/static')

from juniper.app.payments import routes

"""
[
(2.02, 'Approved'), 
(2.01, 'Declined'), 
(2.011, 'Unknown'
]
"""