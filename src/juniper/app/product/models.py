from juniper.app import db
from juniper.app.main.models import Thing
from datetime import datetime as dt


class Product(Thing):
    __tablename__ = 'product'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    # A category for the item.
    category = db.Column(db.String(256))

    # An associated logo
    logo = db.Column(db.String(256))

    # The model of the product.
    model = db.Column(db.String(256))

    price_specification_id = db.Column(db.Integer, db.ForeignKey('price_specification.id'))
    price_specification = db.relationship('PriceSpecification',
                                          foreign_keys=[price_specification_id])

    def __repr__(self):
        return '<Product {}>'.format(self.name)

    __mapper_args__ = {
        'polymorphic_identity': 'product',
    }


class Offer(Thing):
    __tablename__ = 'offer'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    # The availability of this item—for example In stock, Out of stock, Pre-order, etc.
    availability = db.Column(db.String(128))

    # The availability of the product or service included in the offer.
    availability_starts = db.Column(db.DateTime, index=True, default=dt.utcnow)
    availability_ends = db.Column(db.DateTime, index=True, default=dt.utcnow)

    # A category for the item
    category = db.Column(db.String(128))

    # A code to allow someone to purchase this offer
    offer_code = db.Column(db.String(16))

    # The current approximate inventory level for the item or items
    inventory_level = db.Column(db.Integer)

    # The price of the product being offered
    price = db.Column(db.Numeric(12, 2))

    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref='offers', foreign_keys=[product_id])

    __mapper_args__ = {
        'polymorphic_identity': 'offer',
    }


class PriceSpecification(Thing):
    __tablename__ = 'price_specification'

    id = db.Column(db.Integer, db.ForeignKey('thing.id'), primary_key=True)

    # The price of the product being offered
    price = db.Column(db.Numeric(12, 2))

    # The flat fee to add to each item
    flat_fee = db.Column(db.Numeric(12, 2), default=0.00)

    # The fee to add to each item based on the items cost
    cost_fee = db.Column(db.Numeric(4, 3), default=0.00)

    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'))
    offer = db.relationship('Offer', foreign_keys=[offer_id])

    __mapper_args__ = {
        'polymorphic_identity': 'price_specification',
    }
