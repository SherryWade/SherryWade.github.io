from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, HiddenField
from juniper.app.events.models import Event
from juniper.app import db
from juniper.app.payments.models import PaymentType


class TicketSelectionForm(FlaskForm):
    payment_method = SelectField('Payment Method', choices=[(PaymentType().CREDIT_CARD, 'Credit Card'),
                                                            (PaymentType().EXTERNAL, 'External Payment')])

    submit = SubmitField('Proceed to Checkout')

    @classmethod
    def load_form(cls, event):
        # If an event is passed, then use that, else assume it's an event id
        # and look up the event from the database.
        event = event if type(event) is Event else db.session.query(Event).filter_by(id=event).first()

        choices = [(i, i) for i in range(11)]

        for offer in event.parent.offers:
            field_name = '{} (${})'.format(offer.product.name, offer.product.price_specification.price)

            offer_field = SelectField(field_name, coerce=int,
                                      choices=choices, render_kw={'offer_id': offer.id},
                                      validators=[])

            setattr(cls, 'offer_{}'.format(offer.id), offer_field)

        event_id_field = HiddenField('event_id', default=event.id)
        setattr(cls, 'event_id', event_id_field)

        return cls()
