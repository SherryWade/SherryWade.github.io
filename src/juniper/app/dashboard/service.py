from juniper.app.reservations.models import Reservation, Ticket
from juniper.app.payments.models import TransactionRequest, CustomerAddress, CreditCard, Payment, LineItem, CustomerData
from juniper.app.payments.models import PaymentType
from flask import request
from datetime import datetime
from juniper.app import get_session_id
from juniper.app.payments.forms import PaymentForm, BasePaymentForm
from juniper.app.main.models import Post
from flask_login import current_user


class ShoppingCart:

    def __init__(self, payment_form, cart, event):
        self.payment_form = payment_form
        self.cart = cart
        self.event = event

    def get_transaction_request(self):

        if type(self.payment_form) == PaymentForm:
            return self._get_cc_transaction_request()
        elif type(self.payment_form) == BasePaymentForm:
            return self._get_external_transaction_request()

    def _get_customer_address(self):
        customer_address = CustomerAddress()
        customer_address.first_name = self.payment_form.first_name.data
        customer_address.last_name = self.payment_form.last_name.data
        customer_address.address = self.payment_form.address1.data + ', ' + self.payment_form.address2.data
        customer_address.city = self.payment_form.city.data
        customer_address.state = self.payment_form.state.data
        customer_address.zip = self.payment_form.zip.data

        return customer_address

    def _get_line_items(self):
        line_items = []
        for offer in self.event.parent.offers:
            cart_offer = self.cart['items'].get(str(offer.id), None)

            if cart_offer is not None and cart_offer['quantity'] > 0:
                line_item = LineItem()
                line_item.name = offer.product.name
                line_item.unit_price = offer.product.price_specification.price
                # This needs to be cast to an integer since DynamoDB saves
                # numeric values as Decimals.
                line_item.quantity = int(cart_offer['quantity'])

                line_items.append(line_item)

        return line_items

    def _get_customer_data(self):
        customer_data = CustomerData()
        customer_data.email = self.payment_form.email.data
        customer_data.phone = self.payment_form.phone.data

        return customer_data

    def _get_transaction_request(self):
        transaction_request = TransactionRequest()

        transaction_request.amount = self.cart['pricing']['total']
        transaction_request.fees = self.cart['pricing']['fees']
        transaction_request.taxes = self.cart['pricing']['taxes']

        transaction_request.ip_address = request.remote_addr
        transaction_request.identifier = get_session_id()

        return transaction_request

    @staticmethod
    def _get_external_payment():
        payment = Payment()

        payment.payment_type = PaymentType.EXTERNAL

        return payment

    def _get_credit_card_payment(self):
        payment = Payment()

        payment.payment_type = PaymentType.CREDIT_CARD

        credit_card = CreditCard()
        credit_card.number = self.payment_form.cc_number.data
        credit_card.card_code = self.payment_form.cvv.data
        credit_card.expiration_date = '{}/{}'.format(self.payment_form.expiration_month.data,
                                                     self.payment_form.expiration_year.data)

        payment.credit_card = credit_card

        return payment

    def _get_external_transaction_request(self):
        transaction_request = self._get_transaction_request()
        transaction_request.payment = self._get_external_payment()
        transaction_request.bill_to = self._get_customer_address()
        transaction_request.customer = self._get_customer_data()
        transaction_request.line_items = self._get_line_items()

        return transaction_request

    def _get_cc_transaction_request(self):
        transaction_request = self._get_transaction_request()
        transaction_request.payment = self._get_credit_card_payment()
        transaction_request.bill_to = self._get_customer_address()
        transaction_request.customer = self._get_customer_data()
        transaction_request.line_items = self._get_line_items()

        return transaction_request

    def get_reservation(self):
        tickets = []

        for offer in self.event.parent.offers:
            cart_offer = self.cart['items'].get(str(offer.id), {})
            # This needs to be cast as an integer since DynamoDB saves numeric
            # values as decimals
            qty = int(cart_offer.get('quantity', 0))

            for _ in range(qty):
                ticket = Ticket()
                ticket.face_value = offer.product.price_specification.price
                ticket.event_id = self.event.id
                ticket.offer_id = offer.id
                tickets.append(ticket)

        # Create Reservation Information
        reservation = Reservation()

        reservation.booking_time = datetime.now()
        reservation.reservation_for_id = self.event.id
        reservation.under_name = '{} {}'.format(self.payment_form.first_name.data, self.payment_form.last_name.data)
        reservation.total_price = self.cart['pricing']['total']
        reservation.tickets = tickets if len(tickets) > 0 else None
        reservation.disambiguating_description = self.payment_form.comment.data

        return reservation
