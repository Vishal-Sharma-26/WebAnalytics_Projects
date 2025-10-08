from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, validators
from wtforms.validators import InputRequired, Email, EqualTo, Length, URL

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=3, max=30)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Sign up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Log in')

class ScrapeForm(FlaskForm):
    url = StringField('URL to scrape', validators=[InputRequired(), URL(message='Enter a valid URL (http/https).')])
    submit = SubmitField('Scrape')
