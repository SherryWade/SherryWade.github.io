from juniper.app.reservations.models import Reservation
from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, flash, current_app, g
from juniper.app.reservations import bp
from juniper.app import db
from juniper.app.payments.forms import PaymentMethod, PaymentForm
from .forms import ReservationPaymentForm
from juniper.app.payments.models import PaymentType
from .service import get_event
from datetime import datetime
from juniper.app.reservations.service import create_transaction_request, make_reservation
from juniper.app.payments.service import EProcessingNetwork, mask_cc_number
from juniper.app.main.forms import PostForm
from juniper.app.main.models import Post
from ..dashboard.email import send_ticket_confirmation_email


@bp.route('/list')
@login_required
def list():

    r = db.session.query(Reservation).all()

    return str([x.id for x in r])


@bp.route('/reservation/<reservation_id>', methods=['GET', 'POST'])
@login_required
def reservation(reservation_id):

    r = db.session.query(Reservation).filter_by(id=reservation_id).first()

    comment_form = PostForm()

    if comment_form.validate_on_submit():
        comment = Post()

        comment.body = comment_form.comment.data
        comment.user_id = current_user.get_id()
        comment.thing_id = r.id

        db.session.add(comment)
        db.session.commit()

        flash('Your comment was added sucessfully!', 'success')

        return redirect(url_for('reservations.reservation', reservation_id=reservation_id))

    return render_template('reservations/reservation.html',
                           reservation=r, form=comment_form)


@bp.route('/select_payment_type/<event_id>', methods=['GET', 'POST'])
@login_required
def select_payment_type(event_id):

    payment_method_form = PaymentMethod()

    if payment_method_form.validate_on_submit():
        payment_method = payment_method_form.payment_method.data

        if payment_method == PaymentType().CREDIT_CARD:
            return redirect(url_for('reservations.credit_card_payment', event_id=event_id))
        elif payment_method == PaymentType().EXTERNAL:
            return redirect(url_for('reservations.external_payment', event_id=event_id))

    return render_template('reservations/payment/select.html',
                           payment_method_form=payment_method_form)


@bp.route('/credit_card/<event_id>', methods=['GET', 'POST'])
@login_required
def credit_card_payment(event_id):

    event = get_event(event_id)

    if event.start_time < datetime.now():
        flash("Tickets for the selected show are no longer available.", 'primary')
        return redirect(url_for('dashboard.index'))

    form = ReservationPaymentForm.load_form()

    if form.validate_on_submit():
        transaction_request, res = form.populate_obj()

        payment_processing = EProcessingNetwork(transaction_request)
        response = payment_processing.process_transaction()

        transaction_request.transaction_response = response
        transaction_request.payment.credit_card.number = mask_cc_number(transaction_request.payment.credit_card.number)

        if transaction_request.transaction_response.approved:
            res.transaction_request = transaction_request

            db.session.add(reservation)
            db.session.commit()
            db.session.refresh(reservation)

            if transaction_request.customer.email:
                send_ticket_confirmation_email(transaction_request.customer_data.email, reservation, event)

            flash('Your reservations were made successfully', 'success')

            return redirect(url_for('blackfedora.buy_tickets'))

        elif transaction_request.transaction_response.response_code == 'DECLINED':
            flash('The payment was declined. Please check your information and try again.', 'danger')

            db.session.add(transaction_request)
            db.session.commit()

            return redirect(url_for('blackfedora.purchase_tickets', event_id=event_id))
        else:
            msg = """There was an error processing your payment. Please try again. 
                    If the problem persists, please contact the theater directly to process your payment."""
            flash(msg, 'danger')

            db.session.add(transaction_request)
            db.session.commit()

            return redirect(url_for('blackfedora.purchase_tickets', event_id=event_id))

    return render_template('reservations/payment/credit_card_payment.html',
                           event=event, form=form)


@bp.route('/create/<event_id>')
@login_required
def external_payment(event_id):
    return render_template('reservations/payment/create.html')