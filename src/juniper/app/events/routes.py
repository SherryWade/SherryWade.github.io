from flask import render_template, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from juniper.app.events import bp
from juniper.app.events.forms import EventForm, EventTimeForm, CreateBasicEventForm, \
    CreateMultiEventForm, EventOfferForm, PerformanceForm
from juniper.app.events.models import Event
from juniper.app.events.models import Audience
from juniper.app.product.models import Offer
from juniper.app import db
from datetime import datetime
from sqlalchemy.sql.expression import false
from juniper.app.dashboard.forms import TicketSelectionForm


@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():

    events = db.session.query(Event)

    next_event = db.session.query(Event).filter(Event.start_time >= datetime.now()).first()

    return render_template('events/index.html',
                           next_event=next_event,
                           events=events)


@bp.route('/list', methods=['GET'])
@login_required
def list():
    events = db.session.query(Event).all()

    return render_template('events/list.html', events=events)


@bp.route('/json', methods=['GET'])
# TODO: Version the api url
def json():
    from dateutil import parser

    start = parser.parse(request.args.get('start'))
    end = parser.parse(request.args.get('end'))

    # Timezone definition
    event_id = request.args.get("event_id")

    if event_id is None:
        events = db.session.query(Event).filter(Event.parent_id.isnot(None))  # .all()
        events = events.filter(Event.start_time >= start)
        events = events.filter(Event.start_time <= end)

        events = events.all()
    else:
        event = db.session.query(Event).filter_by(id=event_id).first()
        events = event.child_events

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
             'url': url_for('events.event', event_id=event.id)}

        if not event.is_active:
            e['color'] = '#6c757d'

        event_list.append(e)

    return jsonify(event_list)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():

    form = CreateMultiEventForm.load_form()

    if form.validate_on_submit():
        event = Event()

        audience = db.session.query(Audience).filter_by(id=form.audience.data).first()

        event.audience = audience

        event.name = form.name.data

        event.door_time = form.door_time.data
        event.start_time = form.start_time.data
        event.end_time = form.end_time.data

        event.description = form.description.data

        event.image = form.image.data
        event.maximum_attendee_capacity = form.max_capacity.data

        event.is_active = form.active.data

        event.created_by = current_user.username

        db.session.add(event)
        db.session.commit()
        db.session.refresh(event)

        flash('Event Created Successfully', 'success')

        return redirect(url_for('events.event', event_id=event.id))

    return render_template('events/create.html', form=form)


@bp.route('/event/<event_id>')
@login_required
def event(event_id):

    e = db.session.query(Event).filter_by(id=event_id).first()

    ticket_selection_form = TicketSelectionForm().load_form(e)

    if not e or not e.start_time:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('dashboard.index'))

    event_time_form = EventTimeForm()

    return render_template('events/event.html', event=e,
                           ticket_selection_form=ticket_selection_form,
                           event_time_form=event_time_form)


@bp.route('/performance/edit/<event_id>', methods=['GET', 'POST'])
@login_required
def edit_performance(event_id):
    e = db.session.query(Event).filter_by(id=event_id).first()

    form = PerformanceForm()

    if not e:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('dashboard.index', event_id=event_id))

    elif form.validate_on_submit():
        e.is_active = form.active.data

        e.modified_by = current_user.username
        e.modified = datetime.now()

        db.session.commit()

        flash('Show updated successfully', 'success')

        return redirect(url_for('events.event', event_id=e.id))

    elif request.method == 'GET':
        form.active.data = e.is_active

    return render_template('events/performance/edit.html', form=form)


@bp.route('/show/<event_id>')
@login_required
def show(event_id):

    e = db.session.query(Event).filter_by(id=event_id).first()

    if not e or e.parent_id:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('dashboard.index'))

    event_time_form = EventTimeForm()
    event_offer_form = EventOfferForm().load_form(e)

    event_offer_form = None if len(event_offer_form.product.choices) == 0 else event_offer_form

    return render_template('events/show/show.html', event=e,
                           event_time_form=event_time_form,
                           event_offer_form=event_offer_form,
                           title=e.name)


@bp.route('/edit/<event_id>', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    form = EventForm().load_form()

    form.audience.choices = [(-1, '')] + [(a.id, a.name) for a in db.session.query(Audience).all()]

    event = db.session.query(Event).filter_by(id=event_id).first()

    if not event:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('events.event', event_id=event_id))

    elif form.validate_on_submit():
        # Update Event Values
        event.name = form.name.data

        event.door_time = form.door_time.data
        event.start_time = form.start_time.data
        event.end_time = form.end_time.data

        event.description = form.description.data

        event.image = form.image.data
        event.maximum_attendee_capacity = form.max_capacity.data

        event.is_active = form.active.data

        event.audience_id = form.audience.data

        event.modified_by = current_user.username
        event.modified = datetime.now()

        # Empty the list of offers and then re-add the selected offers
        # event.offers = []
        # for offer_id in form.offer.data:
        #    o = db.session.query(Offer).filter_by(id=offer_id).first()

        #    event.offers.append(o)

        db.session.commit()

        flash('Event updated successfully', 'success')

        return redirect(url_for('events.edit', event_id=event_id))

    elif request.method == 'GET':
        form.name.data = event.name
        form.door_time.data = event.door_time
        form.start_time.data = event.start_time
        form.end_time.data = event.end_time
        form.description.data = event.description

        form.image.data = event.image
        form.max_capacity.data = event.maximum_attendee_capacity

        form.audience.data = event.audience_id if event.audience_id else -1

        form.offer.data =[o.id for o in event.offers]

        form.active.data = event.is_active

    return render_template('events/edit.html', form=form)


@bp.route('/basic/create', methods=['GET', 'POST'])
@login_required
def basic_create():

    form = CreateBasicEventForm().load_form()

    if form.validate_on_submit():
        event = Event()
        form.populate_obj(event)
        event.is_basic = True

        db.session.add(event)
        db.session.commit()
        db.session.refresh(event)

        flash('Event Created Successfully', 'success')

        return redirect(url_for('events.event', event_id=event.id))

    return render_template('events/basic/create.html', form=form)


@bp.route('/show/create', methods=['GET', 'POST'])
@login_required
def create_show():

    form = CreateMultiEventForm().load_form()

    if form.validate_on_submit():
        event = Event()
        form.populate_obj(event)

        db.session.add(event)
        db.session.commit()
        db.session.refresh(event)

        flash('Event Created Successfully', 'success')

        return redirect(url_for('events.event', event_id=event.id))

    return render_template('events/show/create.html', form=form)


@bp.route('/show/edit/<event_id>', methods=['GET', 'POST'])
@login_required
def edit_show(event_id):
    form = CreateMultiEventForm().load_form()

    show = db.session.query(Event).filter_by(id=event_id).first()

    if not show:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('dashboard.index', event_id=event_id))

    elif form.validate_on_submit():
        form.populate_obj(show)

        show.modified_by = current_user.username
        show.modified = datetime.now()

        db.session.commit()

        flash('Show updated successfully', 'success')

        return redirect(url_for('events.show', event_id=show.id))

    elif request.method == 'GET':
        form.populate_form(show)

    return render_template('events/show/edit.html', form=form)


@bp.route('/shows/list')
@login_required
def list_shows():
    # Inactive Shows
    shows = db.session.query(Event).filter_by(parent_id=None).all()

    return render_template('events/show/list_shows.html', shows=shows, title="Show List")


@bp.route('/show/add_show_time/<event_id>', methods=['POST'])
@login_required
def add_show_time(event_id):
    event = db.session.query(Event).filter_by(id=event_id).first()

    if not event:
        flash('There was an error while processing your request', 'warning')

        return redirect(url_for('dashboard.index'))

    form = EventTimeForm()

    if form.validate_on_submit():
        e = Event()
        form.populate_object(e)
        e.parent_id = event_id

        db.session.add(e)
        db.session.commit()

        flash('Event Time Added', 'success')

        return redirect(url_for('events.event', event_id=event.id))


@bp.route('/add_pricing_option/<event_id>', methods=['POST'])
@login_required
def add_pricing_option(event_id):
    event = db.session.query(Event).filter_by(id=event_id).first()

    if not event:
        flash('There was an error processing your request', 'warning')

        return redirect(url_for('events.index'))

    form = EventOfferForm.load_form(event)

    if form.validate_on_submit():
        o = Offer()
        form.populate_obj(o)

        # Add pricing option to event
        event.offers.append(o)

        db.session.commit()

        flash('Pricing Option Added Successfully', 'success')

        return redirect(url_for('events.show', event_id=event_id))

    flash('There was an error processing your request', 'warning')

    return redirect(url_for('events.index'))