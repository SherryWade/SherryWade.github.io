from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, ValidationError, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Length, Email
from juniper.app import db
from juniper.app.events.models import Event
import numpy as np
from flask import current_app
from juniper.app.payments.models import PaymentType


def matches_event_id(form, field):
    form_event_id = form.event_id.data

    if form_event_id != str(field.render_kw['event_id']):
        raise ValidationError('There was an error processing this field')


def is_valid_offer(form, field):
    event_id = field.render_kw['event_id']

    event = db.session.query(Event).filter_by(id=event_id).first()

    offer_ids = [offer.id for offer in event.parent.offers]

    if field.render_kw['offer_id'] not in offer_ids:
        raise ValidationError('There was an error processing this field')


def at_least_one_ticket(form, field):
    ticket_cnts = []

    for field in form._fields:
        if field.startswith('offer_'):
            ticket_cnts.append(form._fields[field].data)

    ticket_total = np.array(ticket_cnts).sum()

    if ticket_total <= 0:
        raise ValidationError('You must select at least one ticket.')


class PaymentMethod(FlaskForm):

    payment_method = SelectField('Payment Method', choices=[(PaymentType().CREDIT_CARD, 'Credit Card'),
                                                            (PaymentType().EXTERNAL, 'External Payment')])

    submit = SubmitField('Select')


class BasePaymentForm(FlaskForm):
    first_name = StringField('First Name',
                             validators=[DataRequired(),
                                         Length(min=0, max=140)])

    last_name = StringField('Last Name',
                            validators=[DataRequired(),
                                        Length(min=1, max=140)])

    email = StringField('Email Address',
                        validators=[DataRequired(), Email(), Length(min=0, max=140)])

    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=16)])

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

    comment = TextAreaField('Comment', validators=[Length(max=2048)])

    submit = SubmitField('Submit')


class PaymentForm(BasePaymentForm):

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

    def populate_form(self, form_data):
        # Set field values
        self.first_name.data = form_data['first_name'] if 'first_name' in form_data else ''
        self.last_name.data = form_data['last_name'] if 'last_name' in form_data else ''
        self.email.data = form_data['email'] if 'email' in form_data else ''
        self.phone.data = form_data['phone'] if 'phone' in form_data else ''
        self.expiration_month.data = form_data['expiration_month'] if 'expiration_month' in form_data else ''
        self.expiration_year.data = form_data['expiration_year'] if 'expiration_year' in form_data else ''
        self.address1.data = form_data['address1'] if 'address1' in form_data else ''
        self.address2.data = form_data['address2'] if 'address2' in form_data else ''
        self.city.data = form_data['city'] if 'city' in form_data else ''
        self.state.data = form_data['state'] if 'state' in form_data else ''
        self.zip.data = form_data['zip'] if 'zip' in form_data else ''
        self.event_id.data = form_data['event_id'] if 'event_id' in form_data else ''

        for i in form_data:
            if i.startswith('offer_'):
                attr = getattr(self, i)
                attr.data = form_data[i]


class ConfirmPaymentForm(FlaskForm):

    first_name = HiddenField('First Name')

    last_name = HiddenField('Last Name')

    email = HiddenField('Email Address')

    phone = HiddenField('Phone Number')

    cc_number = HiddenField('Credit Card Number')

    cvv = HiddenField('CVV')

    expiration_month = HiddenField('Expiration Month')
    expiration_year = HiddenField('Expiration Year')

    address1 = HiddenField('Address Line 1')

    address2 = HiddenField('Address Line 2')

    city = HiddenField('City')

    state = HiddenField('State')

    zip = HiddenField('Zip')

    event_id = HiddenField('Event ID')

    total_price = HiddenField('Total')

    taxes = HiddenField('Taxes')
    fees = HiddenField('Ticket Fee')

    submit = SubmitField('Purchase Tickets')

    @classmethod
    def load_form(cls, form_data, event):
        available_offers = []

        # Add hidden offer fields
        for offer in event.parent.offers:
            available_offers.append((offer.id, offer.product.price_specification.price))

            field_name = '{} (${})'.format(offer.product.name, offer.product.price_specification.price)

            kwargs = {'event_id': event.id,
                      'offer_id': offer.id,
                      'price': offer.product.price_specification.price}

            offer_field = HiddenField(field_name, render_kw=kwargs)

            setattr(cls, 'offer_{}'.format(offer.id), offer_field)

        if current_app.config.get('ENV') == 'development':
            choices = [(2.02, 'Approved'), (2.01, 'Declined'), (2.011, 'Unknown')]
            total_price = SelectField('Test Transaction', choices=choices, coerce=float)
            setattr(cls, 'total_price', total_price)

        form = cls()

        # Set field values
        form.first_name.data = form_data['first_name'] if 'first_name' in form_data else ''
        form.last_name.data = form_data['last_name'] if 'last_name' in form_data else ''
        form.email.data = form_data['email'] if 'email' in form_data else ''
        form.phone.data = form_data['phone'] if 'phone' in form_data else ''
        form.cc_number.data = form_data['cc_number'] if 'cc_number' in form_data else ''
        form.cvv.data = form_data['cvv'] if 'cvv' in form_data else ''
        form.expiration_month.data = form_data['expiration_month'] if 'expiration_month' in form_data else ''
        form.expiration_year.data = form_data['expiration_year'] if 'expiration_year' in form_data else ''
        form.address1.data = form_data['address1'] if 'address1' in form_data else ''
        form.address2.data = form_data['address2'] if 'address2' in form_data else ''
        form.city.data = form_data['city'] if 'city' in form_data else ''
        form.state.data = form_data['state'] if 'state' in form_data else ''
        form.zip.data = form_data['zip'] if 'zip' in form_data else ''
        form.event_id.data = form_data['event_id'] if 'event_id' in form_data else ''

        prices = []
        ticket_qty = 0
        for o in available_offers:
            offer_id = o[0]
            offer_price = o[1]

            field_name = 'offer_{}'.format(offer_id)
            qty = form_data[field_name]

            prices.append(qty*offer_price)

            ticket_qty += qty

            attr = getattr(form, field_name)
            attr.data = qty


        subtotal = round(np.sum(prices), 2)

        tax_rate = current_app.config['TAX_RATE']
        taxes = round(subtotal*tax_rate, 2)
        form.taxes.data = taxes

        flat_fee = current_app.config['FLAT_FEE']*ticket_qty
        cost_fee = current_app.config['COST_FEE']*subtotal
        fees = flat_fee + cost_fee
        form.fees.data = round(fees, 2)

        total_price = round(np.sum([subtotal, taxes, fees]), 2)

        if current_app.config.get('ENV') == 'development':
            form.cc_number.data = '4111111111111111'
        else:
            form.total_price.data = total_price

        return form

    def get_offer_information(self):
        offers = []
        for f in self._fields:
            field = self._fields[f]

            if field.render_kw and 'offer_id' in field.render_kw:
                offer_id = field.render_kw['offer_id']
                qty = field.data
                price = field.render_kw['price']

                o = {'offer_id': offer_id, 'qty': int(qty), 'price': price}
                offers.append(o)

        return offers
