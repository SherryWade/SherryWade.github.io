from flask import render_template, url_for, jsonify, redirect, flash, request, current_app
from juniper.app.blackfedora import bp
from juniper.app.events.models import Event
from juniper.app import db
from sqlalchemy.sql.expression import true
from juniper.app.payments.forms import PaymentForm
from juniper.app.payments.service import EProcessingNetwork, mask_cc_number
from juniper.app.blackfedora.forms import EventForm
from juniper.app import save_session, get_session
from datetime import datetime
import juniper.app.blackfedora.forms
from juniper.app.dashboard.service import ShoppingCart
from juniper.app.reservations.models import Reservation
from ..dashboard.email import send_ticket_confirmation_email
from .email import send_groups_and_events_email
from .forms import get_ticket_selection_form
import pytz
import importlib


@bp.route('/')
def index():

    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/index.html', shows=shows)


@bp.route('/our-shows/<slug>')
def our_shows(slug):
    performance_id = request.args.get("performance_id", None)

    if performance_id is not None:
        return performance(performance_id=performance_id)

    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    show = db.session.query(Event).filter_by(slug=slug).first()

    return render_template('blackfedora/show.html', show=show, shows=shows)


def performance(performance_id):
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    p = db.session.query(Event).filter_by(id=performance_id).first()
    # importlib.reload(juniper.app.blackfedora.forms)
    # ticket_selection_form = juniper.app.blackfedora.forms.TicketSelectionForm.load_form(p)

    ticket_selection_form = get_ticket_selection_form(event=p)

    return render_template('blackfedora/performance.html',
                           performance=p, shows=shows,
                           ticket_selection_form=ticket_selection_form)


@bp.route('/about')
def about():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/about.html', title='About', shows=shows)


@bp.route('/what-to-expect')
def what_to_expect():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/what-to-expect.html', title='What to Expect', shows=shows)


@bp.route('/parking-and-directions')
def parking_and_directions():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/parking_and_directions.html', title='Parking and Directions', shows=shows)


@bp.route('/cast')
def cast():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/cast.html', title='Cast', shows=shows)


@bp.route('/auditions')
def auditions():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/auditions.html', title='Auditions', shows=shows)


@bp.route('/press')
def press():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/press.html', title='Press', shows=shows)


@bp.route('/accessibility')
def accessibility():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/accessibility.html', title='Accessibility', shows=shows)


@bp.route('/contact')
def contact():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/contact.html', title='Contact', shows=shows)


@bp.route('/shows')
def shows():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/shows.html', title='Our Shows', shows=shows)


@bp.route('/groups-and-events', methods=['GET', 'POST'])
def groups():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()
    form = EventForm()

    if form.validate_on_submit():
        send_groups_and_events_email(form)

        flash('Your email has been sent!', 'success')

        return redirect(url_for('blackfedora.groups'))

    return render_template('blackfedora/groups.html', title='Groups and Packages',
                           form=form, shows=shows)


@bp.route('/buytickets')
def buy_tickets():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()

    return render_template('blackfedora/buy-tickets.html',
                           title='Buy Tickets', shows=shows)


@bp.route('/purchase-tickets', methods=['GET', 'POST'])
def purchase_tickets():
    shows = db.session.query(Event).filter_by(parent_id=None).filter_by(is_active=true()).all()
    session = get_session()
    cart = session['cart']
    event_id = cart.get('event_id', None)

    event = db.session.query(Event).filter_by(id=event_id).first()

    if event.start_time < datetime.now().replace(tzinfo=pytz.UTC):
        flash("Tickets for the selected show are no longer available.", 'primary')
        return redirect(url_for('blackfedora.buy_tickets'))

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

            send_ticket_confirmation_email(transaction_request.customer.email, reservation, event)

            flash('Thank you! Your reservation was made successfully!', 'success')

            return redirect(url_for('blackfedora.purchase_confirmation', reservation_id=reservation.uuid))

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

            return redirect(url_for('blackfedora.buy_tickets'))

    return render_template('blackfedora/purchase-tickets.html',
                           form=payment_form, event=event, shows=shows, cart=cart,
                           title='Purchase Tickets')


@bp.route('/purchase-confirmation', methods=['GET', 'POST'])
def purchase_confirmation():
    uuid = request.args.get('reservation_id', None)

    if uuid is None:
        return redirect(url_for('blackfedora.index'))

    reservation = db.session.query(Reservation).filter_by(uuid=uuid).first()

    if reservation is None:
        return redirect(url_for('blackfedora.index'))

    return render_template('blackfedora/receipt/confirm_payment.html', reservation=reservation)


@bp.route('/json', methods=['GET'])
# TODO: Version the api url
def json():
    from dateutil import parser

    start = parser.parse(request.args.get('start'))
    end = parser.parse(request.args.get('end'))

    events = db.session.query(Event).filter(Event.parent_id.isnot(None)) #.all()
    events = events.filter(Event.start_time >= start)
    events = events.filter(Event.start_time <= end)

    events = events.filter(Event.is_active)

    events = events.all()

    event_list = []
    for event in events:
        if event.name:
            name = event.name
        elif event.parent:
            name = event.parent.name
        else:
            name = 'Unnamed Event'

        e = {'id': event.id,
             'title': name,
             'start': str(event.start_time),
             'end': str(event.end_time),
             'url': url_for('blackfedora.news')}
             #'url': url_for('blackfedora.our_shows',
             #               slug=event.parent.slug,
             #               performance_id=event.id)}

        if not event.is_active:
            e['color'] = '#6c757d'

        event_list.append(e)

    return jsonify(event_list)


@bp.route('/proceed_to_checkout/<event_id>', methods=['POST'])
def proceed_to_checkout(event_id):
    event = db.session.query(Event).filter_by(id=event_id).first()

    # ticket_selection_form = juniper.app.blackfedora.forms.TicketSelectionForm().load_form(event)
    ticket_selection_form = get_ticket_selection_form(event=event)

    if ticket_selection_form.validate_on_submit():

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

        return redirect(url_for('blackfedora.purchase_tickets'))

    flash("There was an error processing your request", 'warning')

    return redirect(url_for('blackfedora.our_shows', slug=event.parent.slug, performance_id=event.id))


@bp.route('/news', methods=['GET'])
def news():

    return render_template('blackfedora/news.html')
