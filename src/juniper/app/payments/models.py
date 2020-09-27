from juniper.app.main.models import Thing
from juniper.app import db


class PaymentType:
    CREDIT_CARD = 'CREDIT_CARD'
    EXTERNAL = 'EXTERNAL'


class CreditCard(Thing):
    __tablename__ = 'credit_card'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    number = db.Column(db.String(32))

    card_code = db.Column(db.String(8))

    expiration_date = db.Column(db.String(8))

    __mapper_args__ = {
        'polymorphic_identity': 'credit_card',
    }


class Payment(Thing):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    payment_type = db.Column(db.String(32))

    credit_card_id = db.Column(db.Integer, db.ForeignKey('credit_card.id'))
    credit_card = db.relationship('CreditCard', backref='payment', foreign_keys=[credit_card_id])

    __mapper_args__ = {
        'polymorphic_identity': 'payment',
    }


class Order(Thing):
    __tablename__ = 'order'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'order',
    }


class CustomerAddress(Thing):
    __tablename__ = 'customer_address'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    first_name = db.Column(db.String(256))

    last_name = db.Column(db.String(256))

    company = db.Column(db.String(256))

    address = db.Column(db.String(256))

    city = db.Column(db.String(256))

    state = db.Column(db.String(256))

    zip = db.Column(db.String(256))

    __mapper_args__ = {
        'polymorphic_identity': 'customer_address',
    }


class CustomerData(Thing):
    __tablename__ = 'customer_data'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    email = db.Column(db.String(128))

    phone = db.Column(db.String(32))

    __mapper_args__ = {
        'polymorphic_identity': 'customer_data',
    }


class LineItem(Thing):
    __tablename__ = 'line_item'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    transaction_request_id = db.Column(db.Integer, db.ForeignKey('transaction_request.id'))
    transaction_request = db.relationship('TransactionRequest',
                                          foreign_keys=[transaction_request_id],
                                          backref='line_items')

    unit_price = db.Column(db.Numeric(12, 2))

    fee = db.Column(db.Numeric(12, 2))

    quantity = db.Column(db.Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'line_item',
    }


class TransactionResponse(Thing):
    __tablename__ = 'transaction_response'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    response_code = db.Column(db.String(16))

    approved = db.Column(db.Boolean)

    response_body = db.Column(db.Text)

    __mapper_args__ = {
        'polymorphic_identity': 'transaction_response',
    }


class TransactionRequest(Thing):
    __tablename__ = 'transaction_request'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    # The amount of the transaction request
    amount = db.Column(db.Numeric(12, 2))
    taxes = db.Column(db.Numeric(12, 2))
    fees = db.Column(db.Numeric(12, 2))

    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'))
    payment = db.relationship('Payment', backref='transaction_request', foreign_keys=[payment_id])

    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship('Order', backref='transaction_request', foreign_keys=[order_id])

    customer_address_id = db.Column(db.Integer, db.ForeignKey('customer_address.id'))
    bill_to = db.relationship('CustomerAddress', backref='transaction_request', foreign_keys=[customer_address_id])

    customer_data_id = db.Column(db.Integer, db.ForeignKey('customer_data.id'))
    customer = db.relationship('CustomerData', backref='transaction_request', foreign_keys=[customer_data_id])

    transaction_response_id = db.Column(db.Integer, db.ForeignKey('transaction_response.id'))
    transaction_response = db.relationship('TransactionResponse',
                                           backref='transaction_request', foreign_keys=[transaction_response_id])

    __mapper_args__ = {
        'polymorphic_identity': 'transaction_request',
    }
