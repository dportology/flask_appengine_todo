from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, DateTimeField
from wtforms.validators import DataRequired, Length
from wtforms.fields.html5 import DateField

# Form which sits at the bottom of the page and allows users to add new tasks
class NewTaskForm(FlaskForm):
    description = StringField('Description', validators=[DataRequired(), Length(min=1, max=250)])
    due_date = DateField("Due Date", format='%Y-%m-%d',
        validators=[DataRequired()])
    submit = SubmitField('Add New Task')
