from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeField, SubmitField, TextAreaField
from wtforms import IntegerField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from datetime import datetime
from juniper.app import db
from juniper.app.events.models import Audience
from flask_login import current_user
from juniper.app.product.models import Product


class PerformanceForm(FlaskForm):

    active = BooleanField('Active')

    submit = SubmitField('Submit')


class EventForm(FlaskForm):

    name = StringField('Event Name', validators=[Length(max=256), DataRequired()])

    door_time = DateTimeField('Door Time',
                              format='%m/%d/%Y %I:%M %p',
                              default=datetime.now,
                              validators=[DataRequired()])

    start_time = DateTimeField('Start Time',
                               format='%m/%d/%Y %I:%M %p',
                               default=datetime.now,
                               validators=[DataRequired()])

    end_time = DateTimeField('End Time',
                             format='%m/%d/%Y %I:%M %p',
                             default=datetime.now,
                             validators=[DataRequired()])

    description = TextAreaField('Description',
                                validators=[Length(max=512)])

    max_capacity = IntegerField('Max Capacity',
                                validators=[NumberRange(min=1, max=100,
                                                        message='Max Capacity must be between 1 and 100.'),
                                            Optional()])

    image = StringField('Image', validators=[Length(max=256)])

    @classmethod
    def load_form(cls):

        audiences = db.session.query(Audience).all()

        audience = SelectField('Audience', coerce=int,
                               choices=[(-1, '')] + [(a.id, a.name) for a in audiences])
        setattr(cls, 'audience', audience)

        # Add the submit button in the factory method so it shows up
        # last in the form when using the render method.
        setattr(cls, 'active', BooleanField('Active'))
        setattr(cls, 'submit', SubmitField('Submit'))

        return cls()


class EventTimeForm(FlaskForm):
    # TODO: Add event id hidden field

    door_time = DateTimeField('Door Time',
                              format='%m/%d/%Y %I:%M %p',
                              default=datetime.now,
                              validators=[DataRequired()])

    start_time = DateTimeField('Start Time',
                               format='%m/%d/%Y %I:%M %p',
                               default=datetime.now,
                               validators=[DataRequired()])

    end_time = DateTimeField('End Time',
                             format='%m/%d/%Y %I:%M %p',
                             default=datetime.now,
                             validators=[DataRequired()])

    submit = SubmitField('Submit')

    def populate_object(self, obj):
        obj.door_time = self.door_time.data
        obj.start_time = self.start_time.data
        obj.end_time = self.end_time.data

        obj.created_by = current_user.username
        obj.created = datetime.now()


class AudienceForm(FlaskForm):

    name = StringField('Name', validators=[DataRequired(), Length(max=256)])

    description = TextAreaField('Description', validators=[Length(max=1024)])

    audience_type = StringField('Audience Type', validators=[Length(max=256)])

    submit = SubmitField('Submit')


class CreateBasicEventForm(FlaskForm):
    """
    This is the form to use when creating a basic event. It also includes fields related
    to the associated product offering, since a basic event is required to have at least
    one offering associated with it.
    """

    name = StringField('Event Name', validators=[Length(max=256),
                                                 DataRequired()])

    door_time = DateTimeField('Door Time',
                              format='%m/%d/%Y %I:%M %p',
                              validators=[DataRequired()])

    start_time = DateTimeField('Start Time',
                               format='%m/%d/%Y %I:%M %p',
                               validators=[DataRequired()])

    end_time = DateTimeField('End Time',
                             format='%m/%d/%Y %I:%M %p',
                             validators=[DataRequired()])

    description = TextAreaField('Description',
                                validators=[Length(max=512)])

    max_capacity = IntegerField('Max Capacity',
                                validators=[NumberRange(min=1, max=100,
                                                        message='Max Capacity must be between 1 and 100.'),
                                            Optional()])

    image = StringField('Image', validators=[Length(max=256)])

    active = BooleanField('Active')

    offer_inventory_level = IntegerField('Inventory Level', validators=[Optional()])

    offer_availability_starts = DateTimeField('Availability Starts',
                                        format='%m/%d/%Y %I:%M %p',
                                        validators=[DataRequired()])

    offer_availability_ends = DateTimeField('Availability Ends',
                                            format='%m/%d/%Y %I:%M %p',
                                            validators=[DataRequired()])

    submit = SubmitField('Submit')

    @classmethod
    def load_form(cls):
        audiences = db.session.query(Audience).all()

        audience = SelectField('Audience', coerce=int,
                               choices=[(-1, '')] + [(a.id, a.name) for a in audiences])

        setattr(cls, 'audience', audience)

        return cls()

    def populate_obj(self, obj):
        obj.name = self.name.data

        obj.door_time = self.door_time.data
        obj.start_time = self.start_time.data
        obj.end_time = self.end_time.data
        obj.description = self.description.data
        obj.image = self.image.data
        obj.maximum_attendee_capacity = self.max_capacity.data
        obj.is_active = self.active.data

        obj.audience_id = self.audience.data

        obj.created = datetime.now()
        obj.created_by = current_user.username
        obj.modified_by = current_user.username
        obj.modified = datetime.now()


class CreateMultiEventForm(FlaskForm):
    """
    This is the form to use when creating a basic event. It also includes fields related
    to the associated product offering, since a basic event is required to have at least
    one offering associated with it.
    """

    name = StringField('Show Name', validators=[Length(max=256),
                                                DataRequired()])

    alternate_name = StringField('Alternate Name', validators=[Length(max=256), DataRequired()])

    description = TextAreaField('Description',
                                validators=[Length(max=1024)])

    disambiguating_description = StringField('Disambiguating Description',
                                             validators=[Length(max=512)])

    max_capacity = IntegerField('Max Capacity',
                                validators=[NumberRange(min=1, max=100,
                                                        message='Max Capacity must be between 1 and 100.'),
                                            Optional()])

    primary_image = StringField('Primary Image', validators=[Length(max=128)])
    secondary_image = StringField('Secondary Image', validators=[Length(max=128)])

    slug = StringField('Slug', validators=[Length(max=256), DataRequired()])
    calendar_code = StringField('Calendar Code', validators=[Length(max=16), DataRequired()])

    active = BooleanField('Active')

    # These fields map to the Thing object
    audience_name = StringField('Rating', validators=[DataRequired(), Length(max=256)])

    audience_description = TextAreaField('Rating Description',
                                         validators=[Length(max=1024)])

    audience_disambiguating_description = TextAreaField('Rating Disambiguating Description',
                                                        validators=[Length(max=1024)])

    audience_type = StringField('Audience Type', validators=[Length(max=256)])

    submit = SubmitField('Submit')

    @classmethod
    def load_form(cls):

        return cls()

    def populate_obj(self, obj):

        # Event attributes
        obj.name = self.name.data
        obj.description = self.description.data
        obj.maximum_attendee_capacity = self.max_capacity.data
        obj.primary_image = self.primary_image.data
        obj.secondary_image = self.secondary_image.data
        obj.slug = self.slug.data
        obj.calendar_code = self.calendar_code.data
        obj.is_active = self.active.data
        obj.alternate_name = self.alternate_name.data
        obj.disambiguating_description = self.disambiguating_description.data

        # Audience information
        audience = Audience()
        audience.name = self.audience_name.data
        audience.description = self.audience_description.data
        audience.disambiguating_description = self.audience_disambiguating_description.data
        audience.audience_type = self.audience_type.data

        obj.audience = audience

        obj.created = datetime.now()
        obj.created_by = current_user.username
        obj.modified_by = current_user.username
        obj.modified = datetime.now()
        obj.is_basic = False

    def populate_form(self, event):
        # Event attributes
        self.name.data = event.name
        self.description.data = event.description
        self.max_capacity.data = event.maximum_attendee_capacity
        self.primary_image.data = event.primary_image
        self.secondary_image.data = event.secondary_image
        self.slug.data = event.slug
        self.calendar_code.data = event.calendar_code
        self.active.data = event.is_active
        self.alternate_name.data = event.alternate_name
        self.disambiguating_description.data = event.disambiguating_description

        # Audience information
        if event.audience:
            self.audience_name.data = event.audience.name
            self.audience_description.data = event.audience.description
            self.audience_disambiguating_description.data = event.audience.disambiguating_description
            self.audience_type.data = event.audience.audience_type


class EventOfferForm(FlaskForm):

    @classmethod
    def load_form(cls, event):
        """
        Factory Method to create the form and populate the select field
        with the available product offerings.

        :return: EventOfferForm: The form used to add an offering to an event
        """

        curr_prod_ids = [offer.product.id for offer in event.offers]

        products = db.session.query(Product).all()

        p_choices = [(p.id, '{} (${})'.format(p.name, p.price_specification.price)) for p in products if p.id not in curr_prod_ids]

        product = SelectField('Product', coerce=int, choices=p_choices)

        setattr(cls, 'product', product)

        submit = SubmitField('Submit')

        setattr(cls, 'submit', submit)

        return cls()

    def populate_obj(self, obj):

        obj.category = 'TICKET'
        obj.product_id = self.product.data