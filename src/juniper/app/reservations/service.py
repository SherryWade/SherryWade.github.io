from datetime import datetime
from juniper.app.reservations.models import Reservation, Ticket
from juniper.app.payments.forms import PaymentForm
from juniper.app.payments.models import TransactionRequest, CustomerData, CreditCard, Payment, CustomerAddress, LineItem
from flask import request, g
from juniper.app import db
from juniper.app.product.models import Offer
from juniper.app.events.models import Event


def get_event(event_id=None):
    if 'event' not in g:
        event = db.session.query(Event).filter_by(id=event_id).first()
        g.event = event

    return g.event


def make_reservation(form):
    reservation = Reservation()

    reservation.booking_time = datetime.now()

    reservation.reservation_for_id = form.event_id.data

    reservation.under_name = '{} {}'.format(form.first_name.data, form.last_name.data)

    reservation.total_price = form.total_price.data

    tickets = []

    for f in form._fields:
        if f.startswith('offer_'):
            field = form._fields[f]

            ticket_cnt = int(field.data)
            for i in range(ticket_cnt):
                ticket = Ticket()
                ticket.face_value = field.render_kw['price']
                ticket.event_id = form.event_id.data
                ticket.offer_id = field.render_kw['offer_id']

                tickets.append(ticket)

    reservation.tickets = tickets if len(tickets) > 0 else None

    return reservation


def create_transaction_request(form):

    if type(form) == PaymentForm:
        tr = create_transaction_request_from_payment_form(form)

    return tr


def create_transaction_request_from_payment_form(form):
    transaction_request = TransactionRequest()

    customer_address = CustomerAddress()
    customer_address.first_name = form.first_name.data
    customer_address.last_name = form.last_name.data
    customer_address.address = form.address1.data + ', ' + form.address2.data
    customer_address.city = form.city.data
    customer_address.state = form.state.data
    customer_address.zip = form.zip.data

    credit_card = CreditCard()
    credit_card.number = form.cc_number.data
    credit_card.card_code = form.cvv.data
    credit_card.expiration_date = '{}/{}'.format(form.expiration_month.data,
                                                 form.expiration_year.data)

    payment = Payment()
    payment.credit_card = credit_card

    line_items = []

    offer_info = form.get_offer_information()
    for o in offer_info:
        offer = db.session.query(Offer).filter_by(id=o['offer_id']).first()

        line_item = LineItem()
        line_item.name = offer.product.name
        line_item.unit_price = offer.product.price_specification.price
        line_item.quantity = o['qty']

        line_items.append(line_item)

    customer_data = CustomerData()
    customer_data.email = form.email.data
    customer_data.phone = form.phone.data

    transaction_request.amount = form.total_price.data
    transaction_request.fees = form.fees.data
    transaction_request.taxes = form.taxes.data
    transaction_request.payment = payment

    transaction_request.bill_to = customer_address
    transaction_request.customer = customer_data
    transaction_request.line_items = line_items

    transaction_request.ip_address = request.remote_addr

    return transaction_request
