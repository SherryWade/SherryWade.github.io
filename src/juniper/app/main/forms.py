from flask_wtf import FlaskForm
from wtforms import SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class PostForm(FlaskForm):

    comment = TextAreaField('Comment', validators=[Length(max=2048), DataRequired()])

    submit = SubmitField('Post Comment')
