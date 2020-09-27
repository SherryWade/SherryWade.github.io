from wtforms import StringField, SubmitField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Email
from flask_wtf import FlaskForm
from juniper.app.events.models import Event
from juniper.app import db


class EventForm(FlaskForm):

    name = StringField('Name', validators=[Length(max=256), DataRequired()])

    email = StringField('Email', validators=[DataRequired(), Email()])

    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])

    description = TextAreaField('Description',
                                validators=[Length(max=512)])

    submit = SubmitField('Submit')


def get_ticket_selection_form(event, **kwargs):
    """Dynamically creates a Ticket Selection Form form"""

    # First we create the base form
    class TicketSelectionForm(FlaskForm):
        submit = SubmitField('Proceed to Checkout')

    # If an event is passed, then use that, else assume it's an event id
    # and look up the event from the database.
    event = event if type(event) is Event else db.session.query(Event).filter_by(id=event).first()

    choices = [(i, i) for i in range(11)]

    for offer in event.parent.offers:
        label = '{} (${})'.format(offer.product.name, offer.product.price_specification.price)

        field = SelectField(label, coerce=int,
                            choices=choices, render_kw={'offer_id': offer.id},
                            validators=[])

        setattr(TicketSelectionForm, 'offer_{}'.format(offer.id), field)

    event_id_field = HiddenField('event_id', default=event.id)
    setattr(TicketSelectionForm, 'event_id', event_id_field)

    # Finally, we return the *instance* of the class
    # We could also use a dictionary comprehension and then use
    # `type` instead, if that seemed clearer.  That is:
    # type('DriverTemplateScheduleForm', Form, our_fields)(**kwargs)
    return TicketSelectionForm(**kwargs)
