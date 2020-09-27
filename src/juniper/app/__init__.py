from logging.handlers import RotatingFileHandler
from botocore.exceptions import ClientError
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_moment import Moment
from .config import Config
from flask import Flask, session, current_app
from datetime import datetime
import hashlib
import logging
import string
import random
import boto3
import os


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = "Please login to view this page."
moment = Moment()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    moment.init_app(app)

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from .blackfedora import bp as blackfedora_bp
    app.register_blueprint(blackfedora_bp)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .events import bp as events_bp
    app.register_blueprint(events_bp, url_prefix='/events')

    from .payments import bp as payments_bp
    app.register_blueprint(payments_bp, url_prefix='/payments')

    from .product import bp as product_bp
    app.register_blueprint(product_bp, url_prefix='/product')

    from .reservations import bp as reservations_bp
    app.register_blueprint(reservations_bp, url_prefix='/reservations')

    from .user import bp as user_bp
    app.register_blueprint(user_bp, url_prefix='/user')

    # Flask uses Python's logging package to write its logs, and this package
    # already has the ability to send logs by email. All I need to do to get
    # emails sent out on errors is to add a SMTPHandler instance to the Flask
    # logger object, which is app.logger:
    if not app.debug and not app.testing:

        # Also add file logging
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log',
                                           maxBytes=10240,
                                           backupCount=10)

        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('App startup')

    return app


def random_string(string_length=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase

    return ''.join(random.choice(letters) for i in range(string_length))


def get_session_id():
    """
    Generate a random-ish ID that can be used as the session ID for
    DynamoDB Lookup
    :return: String
    """

    if 'session_id' in session:
        session_id = session['session_id']
    else:
        secret_key = current_app.config.get('SECRET_KEY')
        current_time = datetime.today()
        random_str = '{}{}{}'.format(secret_key, current_time, random_string(string_length=20))

        session_id = hashlib.sha256(random_str.encode()).hexdigest()
        session['session_id'] = session_id

    return session_id


def get_session():
    session_id = get_session_id()
    dynamodb = boto3.resource("dynamodb", region_name='us-east-1')
    session_data = {}

    table = dynamodb.Table('session')

    try:
        response = table.get_item(
            Key={
                'session_id': session_id,
            }
        )

        item = response.get('Item', {})
        session_data = item.get('session_data', {})
    except ClientError as e:
        print(e.response['Error']['Message'])

    return session_data


def save_session(data):
    session_id = get_session_id()

    session_data = {key: data[key] for key in data if data[key] != ''}
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    table = dynamodb.Table('session')

    table.put_item(
        Item={
            'session_id': session_id,
            'session_data': session_data
        })


def send_email(subject, recipients, text_body, html_body, sender=None, bcc=[]):
    # Check if the app is running in development mode.
    is_development = current_app.config.get('ENV') == 'development'

    # Get emails from application configuration
    admin_email = current_app.config.get('ADMIN_EMAIL')
    admin_email_list = current_app.config.get('ADMINS')
    from_email = current_app.config.get('FROM_EMAIL')

    # Set sending info
    recipients = [admin_email] if is_development else recipients
    sender = from_email if sender is None else sender

    bcc = bcc + admin_email_list  # Add admins to BCC list
    bcc = list(set(bcc) - set(recipients))  # Remove any recipients from BCC list

    _ses_email(subject=subject, sender=sender, recipients=recipients,
               text_body=text_body, html_body=html_body, bcc=bcc)


def _ses_email(subject, sender, recipients, text_body, html_body, bcc):
    client = boto3.client('ses', region_name='us-east-1')

    response = client.send_email(
        Destination={
            'BccAddresses': bcc,
            'CcAddresses': [],
            'ToAddresses': recipients,
        },
        Message={
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': html_body,
                },
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': text_body,
                },
            },
            'Subject': {
                'Charset': 'UTF-8',
                'Data': subject,
            },
        },
        Source=sender
    )

    return response
