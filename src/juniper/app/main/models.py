from datetime import datetime
from juniper.app import db, random_string
from flask import current_app
import hashlib


def get_uuid():
    """
    Generate a random-ish UUID for Thing Objects
    :return: String
    """

    secret_key = current_app.config.get('SECRET_KEY')
    current_time = datetime.today()
    random_str = '{}{}{}'.format(secret_key, current_time, random_string(string_length=50))

    uuid = hashlib.sha256(random_str.encode()).hexdigest()

    return uuid


class Thing(db.Model):
    __tablename__ = 'thing'

    id = db.Column(db.Integer, primary_key=True)

    # The type of the item
    type = db.Column(db.String(50))

    # UUID of item
    uuid = db.Column(db.String(64), default=get_uuid)

    # An alias for the item
    alternate_name = db.Column(db.String(256))

    # A description of the item
    description = db.Column(db.String(1024))

    # A sub property of description. A short description of the
    # item used to disambiguate from other, similar items. Information
    # from other properties (in particular, name) may be necessary for
    # the description to be useful for disambiguation.
    disambiguating_description = db.Column(db.String(1024))

    # The identifier property represents any kind of identifier for any
    # kind of Thing, such as ISBNs, GTIN codes, UUIDs etc.
    identifier = db.Column(db.String(256))

    # An image of the item
    image = db.Column(db.String(256))

    # Indicates a page for which this thing is the main entity being described.
    main_entity_of_page = db.Column(db.String(256))

    # The name of the item.
    name = db.Column(db.String(256))

    # URL of the item.
    url = db.Column(db.String(256))

    # IP Address
    ip_address = db.Column(db.String(32))

    created = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(64))

    modified = db.Column(db.DateTime, default=datetime.now)
    modified_by = db.Column(db.String(64))

    is_default = db.Column(db.Boolean)

    comments = db.relationship('Post')

    __mapper_args__ = {
        'polymorphic_identity': 'thing',
        'polymorphic_on': type
    }


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    body = db.Column(db.Text)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', foreign_keys=[user_id])

    thing_id = db.Column(db.Integer, db.ForeignKey('thing.id'))
    thing = db.relationship('Thing', foreign_keys=[thing_id])

    def __repr__(self):
        return '<Post {}>'.format(self.body)
