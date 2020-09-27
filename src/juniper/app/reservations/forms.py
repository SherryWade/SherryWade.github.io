from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, ValidationError, HiddenField, FieldList
from wtforms.validators import DataRequired, Length, Email
from .service import get_event
from juniper.app.payments.models import TransactionRequest, CustomerAddress, CustomerData, LineItem, CreditCard, Payment
from .models import Reservation, Ticket
from datetime import datetime
from juniper.app.product.service import pricing_service
from juniper.app import get_session_id


class ReservationPaymentForm(FlaskForm):

    first_name = StringField('First Name',
                             validators=[DataRequired(),
                                         Length(min=0, max=140)])

    last_name = StringField('Last Name',
                            validators=[DataRequired(),
                                        Length(min=1, max=140)])

    email = StringField('Email Address',
                        validators=[DataRequired(), Email(), Length(min=0, max=140)])

    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=16)])

    # TODO: Add validation
    cc_number = StringField('Credit Card Number',
                            validators=[DataRequired()])

    cvv = StringField('CVV', validators=[DataRequired(), Length(min=3, max=4)])

    expiration_month = SelectField('Expiration Month',
                                   choices=[(i, i) for i in range(1, 13)],
                                   coerce=int,
                                   validators=[DataRequired()])

    # TODO: Set choices based on current year
    expiration_year = SelectField('Expiration Year',
                                  coerce=int,
                                  choices=[(i, str(i)) for i in range(2020, 2031)],
                                  validators=[DataRequired()])

    address1 = StringField('Address Line 1',
                           validators=[DataRequired(),
                                       Length(min=1, max=140)])

    address2 = StringField('Address Line 2',
                           validators=[Length(min=0, max=140)])

    city = StringField('City',
                       validators=[DataRequired(),
                                   Length(min=1, max=140)])

    state = StringField('State',
                        validators=[DataRequired(),
                                    Length(min=2, max=2)])

    zip = StringField('Zip',
                      validators=[DataRequired(),
                                  Length(min=5, max=5)])

    submit = SubmitField('Next...')

    @classmethod
    def load_form(cls):
        event = get_event()

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

    def get_offer_quantity(self, offer_id):
        """
        Function takes an offer id and returns the quantity
        of tickets selected for that offer
        :return:
        """
        for f in self._fields:
            field = self._fields[f]

            if field.render_kw.get('offer_id', None) == offer_id:
                return field.data

        return 0

    def populate_obj(self):
        event = get_event()

        transaction_request = TransactionRequest()

        customer_address = CustomerAddress()
        customer_address.first_name = self.first_name.data
        customer_address.last_name = self.last_name.data
        customer_address.address = self.address1.data + ', ' + self.address2.data
        customer_address.city = self.city.data
        customer_address.state = self.state.data
        customer_address.zip = self.zip.data

        credit_card = CreditCard()
        credit_card.number = self.cc_number.data
        credit_card.card_code = self.cvv.data
        credit_card.expiration_date = '{}/{}'.format(self.expiration_month.data,
                                                     self.expiration_year.data)

        payment = Payment()
        payment.credit_card = credit_card

        line_items, tickets = [], []
        for offer in event.parent.offers:
            qty = self.get_offer_quantity(offer.id)

            if qty > 0:
                line_item = LineItem()
                line_item.name = offer.product.name
                line_item.unit_price = offer.product.price_specification.price
                line_item.quantity = qty

                line_items.append(line_item)

                ticket = Ticket()
                ticket.face_value = offer.product.price_specification.price
                ticket.event_id = event.id
                ticket.offer_id = offer.id
                tickets.append(ticket)

        total, subtotal, taxes, fees = pricing_service(line_items)

        customer_data = CustomerData()
        customer_data.email = self.email.data
        customer_data.phone = self.phone.data

        transaction_request.amount = total
        transaction_request.fees = fees
        transaction_request.taxes = taxes
        transaction_request.payment = payment

        transaction_request.bill_to = customer_address
        transaction_request.customer = customer_data
        transaction_request.line_items = line_items

        transaction_request.ip_address = request.remote_addr
        transaction_request.identifier = get_session_id()

        # Create Reservation Information
        reservation = Reservation()

        reservation.booking_time = datetime.now()
        reservation.reservation_for_id = event.id
        reservation.under_name = '{} {}'.format(self.first_name.data, self.last_name.data)
        reservation.total_price = self.total_price.data
        reservation.tickets = tickets if len(tickets) > 0 else None

        return transaction_request, reservation
