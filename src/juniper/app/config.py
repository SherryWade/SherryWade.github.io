import os
from decimal import Decimal
from juniper.config import JUNIPER_HOME

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret-key-for-app'

    # Payment Information
    FLAT_FEE = Decimal(0.0)
    COST_FEE = Decimal(0.000)
    TAX_RATE = Decimal(0.05)

    # Location of database. Check environment variable first, and if it's not there
    # then create a database in the base directory.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(JUNIPER_HOME, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'brandon@bsethwalker.com'
    FROM_EMAIL = os.environ.get('FROM_EMAIL') or 'no_reply@charleston.ai'
    ADMINS = ['brandon@bsethwalker.com']
