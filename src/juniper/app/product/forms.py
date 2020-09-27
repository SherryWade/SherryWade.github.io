from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DecimalField
from wtforms.validators import DataRequired, Length


class ProductForm(FlaskForm):

    name = StringField('Name', validators=[DataRequired(), Length(max=256)])

    description = TextAreaField('Description', validators=[Length(max=1024)])

    price = DecimalField('Price', validators=[DataRequired()])

    submit = SubmitField('Submit')