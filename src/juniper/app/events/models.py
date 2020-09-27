from juniper.app.main.models import Thing
from juniper.app import db
from sqlalchemy.orm import synonym
from pytz import timezone
import pytz

event_offer = db.Table('event_offer',
                       db.Column('event_id', db.Integer, db.ForeignKey('event.id')),
                       db.Column('offer_id', db.Integer, db.ForeignKey('offer.id')))


class Event(Thing):
    __tablename__ = 'event'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    parent_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    parent = db.relationship('Event', remote_side=[id], foreign_keys=[parent_id])

    door_time = db.Column(db.DateTime, index=True)

    start_time_ = db.Column('start_time', db.DateTime, index=True)
    end_time = db.Column(db.DateTime, index=True)

    @property
    def start_time(self):
        eastern = timezone('US/Eastern')

        return self.start_time_.replace(tzinfo=pytz.UTC).astimezone(eastern)

    @start_time.setter
    def start_time(self, value):
        self.start_time_ = value

    start_time = synonym('start_time_', descriptor=start_time)

    maximum_attendee_capacity = db.Column(db.Integer)

    child_events = db.relationship('Event', foreign_keys=[parent_id])

    audience_id = db.Column(db.Integer, db.ForeignKey('audience.id'))
    audience = db.relationship("Audience", foreign_keys=[audience_id])

    # Slug for site url
    slug = db.Column(db.String(256))

    # Shorthand code that will show up on the calendar
    calendar_code = db.Column(db.String(16))

    # Two images per show/event
    primary_image = db.Column(db.String(128))
    secondary_image = db.Column(db.String(128))

    offers = db.relationship('Offer', secondary=event_offer)

    #tickets = db.relationship('Ticket', back_populates='event')

    is_active = db.Column(db.Boolean, default=True)

    is_basic = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return '<Event {}: {}>'.format(self.name, self.start_time)

    __mapper_args__ = {
        'polymorphic_identity': 'event',
    }


class Audience(Thing):
    __tablename__ = 'audience'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    # The target group associated with a given audience
    # (e.g. veterans, car owners, musicians, etc.)
    audience_type = db.Column(db.String(256))

    # events = db.relationship('Event', backref='audience', lazy='dynamic')

    __mapper_args__ = {
        'polymorphic_identity': 'audience',
    }