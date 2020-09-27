from flask_login import login_required
from juniper.app.events.models import Event
from flask import render_template, redirect, url_for, flash, current_app
from datetime import datetime
from juniper.app.dashboard import bp
from juniper.app import db, get_session, save_session
from .forms import TicketSelectionForm
from juniper.app.payments.models import PaymentType
from juniper.app.payments.forms import PaymentForm, BasePaymentForm
from juniper.app.payments.service import EProcessingNetwork, mask_cc_number
from .service import ShoppingCart
from .email import send_ticket_confirmation_email
from ..reservations.models import Reservation


@bp.route('/', methods=['GET'])
@login_required
def index():

    next_event = db.session.query(Event).filter(Event.start_time >= datetime.now()).first()

    latest_reservations = db.session.query(Reservation).order_by(Reservation.created.desc()).limit(5).all()

    ticket_selection_form = TicketSelectionForm().load_form(next_event) if next_event is not None else None

    return render_template('dashboard/index.html',
                           next_event=next_event,
                           ticket_selection_form=ticket_selection_form, latest_reservations=latest_reservations,
                           title="Dashboard")


@bp.route('/proceed_to_checkout/<event_id>', methods=['POST'])
@login_required
def proceed_to_checkout(event_id):
    event = db.session.query(Event).filter_by(id=event_id).first()

    ticket_selection_form = TicketSelectionForm().load_form(event)

    if ticket_selection_form.validate_on_submit():

        payment_method = ticket_selection_form.payment_method.data

        session = get_session()

        cart_items = {}

        subtotal = 0
        item_cnt = 0
        for offer in event.parent.offers:
            attr = getattr(ticket_selection_form, 'offer_{}'.format(offer.id), None)

            if attr is not None and attr.data > 0:
                price = offer.product.price_specification.price
                name = offer.product.name
                qty = attr.data
                item_cnt += qty
                subtotal += price*qty

                cart_items[str(offer.id)] = {'price': price,
                                             'name': name,
                                             'quantity': qty}

        # Calculate pricings
        tax_rate = current_app.config['TAX_RATE']
        flat_fee_price = current_app.config['FLAT_FEE']
        cost_fee_rate = current_app.config['COST_FEE']

        subtotal = round(subtotal, 2)
        taxes = round(subtotal * tax_rate, 2)

        flat_fee = flat_fee_price * item_cnt
        cost_fee = cost_fee_rate * subtotal
        fees = round(flat_fee + cost_fee, 2)

        total = subtotal + taxes + fees
        pricing = {'subtotal': subtotal,
                   'taxes': taxes,
                   'fees': fees,
                   'total': total}

        session['cart'] = {'pricing': pricing, 'items': cart_items, 'event_id': event_id}

        save_session(session)

        if payment_method == PaymentType.CREDIT_CARD:
            return redirect(url_for('dashboard.checkout_credit_card'))
        elif payment_method == PaymentType.EXTERNAL:
            return redirect(url_for('dashboard.checkout_external'))

    flash("There was an error processing your request", 'warning')
    return redirect(url_for('dashboard.index'))


@bp.route('/checkout/credit_card', methods=['GET', 'POST'])
@login_required
def checkout_credit_card():
    msg = None
    session = get_session()
    cart = session['cart']
    event_id = cart.get('event_id', None)

    event = db.session.query(Event).filter_by(id=event_id).first()

    payment_form = PaymentForm()

    if payment_form.validate_on_submit():

        if current_app.config.get('ENV') == 'development':
            payment_form.cc_number.data = '4111111111111111'

        shopping_cart = ShoppingCart(payment_form=payment_form, cart=cart, event=event)

        transaction_request = shopping_cart.get_transaction_request()

        payment_processing = EProcessingNetwork(transaction_request)
        response = payment_processing.process_transaction()

        transaction_request.transaction_response = response
        transaction_request.payment.credit_card.number = mask_cc_number(transaction_request.payment.credit_card.number)

        if transaction_request.transaction_response.approved:
            reservation = shopping_cart.get_reservation()
            reservation.transaction_request = transaction_request

            db.session.add(reservation)
            db.session.commit()
            db.session.refresh(reservation)

            if transaction_request.customer.email:
                send_ticket_confirmation_email(transaction_request.customer.email, reservation, event)

            flash('Your reservations were made successfully', 'success')

            return redirect(url_for('reservations.reservation', reservation_id=reservation.id))

        elif transaction_request.transaction_response.response_code == 'DECLINED':
            msg = ('The payment was declined. Please check your information and try again.', 'danger')

            db.session.add(transaction_request)
            db.session.commit()

        else:
            msg = """There was an error processing your payment. Please try again. 
                    If the problem persists, please contact the theater directly to process your payment."""
            flash(msg, 'danger')

            db.session.add(transaction_request)
            db.session.commit()

            # TODO: Redirect to a transaction page where the user can see the actual error message(s)
            return redirect(url_for('dashboard.index'))

    return render_template('dashboard/checkout.html', cart=cart,
                           form=payment_form, event=event,
                           title="Checkout", msg=msg)


@bp.route('/checkout/external', methods=['GET', 'POST'])
@login_required
def checkout_external():
    session = get_session()
    cart = session['cart']
    event_id = cart.get('event_id', None)

    event = db.session.query(Event).filter_by(id=event_id).first()

    payment_form = BasePaymentForm()

    if payment_form.validate_on_submit():

        shopping_cart = ShoppingCart(payment_form=payment_form, cart=cart, event=event)

        transaction_request = shopping_cart.get_transaction_request()

        reservation = shopping_cart.get_reservation()
        reservation.transaction_request = transaction_request

        db.session.add(reservation)
        db.session.commit()
        db.session.refresh(reservation)

        html_body = render_template('blackfedora/email/ticket_confirmation.html',
                                    reservation=reservation,
                                    event=event)

        response = ses_email('Your Black Fedora Confirmation', html_body)

        flash('Your reservations were made successfully', 'success')

        return redirect(url_for('reservations.reservation', reservation_id=reservation.id))

    return render_template('dashboard/external_checkout.html', cart=cart,
                           form=payment_form, event=event,
                           title="Make Reservation")