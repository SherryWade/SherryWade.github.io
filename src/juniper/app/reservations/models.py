from juniper.app.main.models import Thing
from datetime import datetime
from juniper.app import db


class Reservation(Thing):
    __tablename__ = 'reservation'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    booking_time = db.Column(db.DateTime, default=datetime.now)

    reservation_for_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    reservation_for = db.relationship('Event',
                                      foreign_keys=[reservation_for_id], backref='reservations')

    under_name = db.Column(db.String(256))

    total_price = db.Column(db.Numeric(12, 2))

    transaction_request_id = db.Column(db.Integer, db.ForeignKey('transaction_request.id'))
    transaction_request = db.relationship('TransactionRequest', foreign_keys=[transaction_request_id])

    __mapper_args__ = {
        'polymorphic_identity': 'reservation'
    }


class Ticket(Thing):

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    face_value = db.Column(db.Numeric(12, 2))

    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))
    event = db.relationship('Event', foreign_keys=[event_id])

    reservation_id = db.Column(db.Integer, db.ForeignKey('reservation.id'))
    reservation = db.relationship('Reservation', foreign_keys=[reservation_id], backref='tickets')

    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    offer = db.relationship('Offer', foreign_keys=[offer_id])

    __mapper_args__ = {
        'polymorphic_identity': 'ticket'
    }