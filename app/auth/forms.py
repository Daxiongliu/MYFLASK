from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('log In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9.]*$', 0,
                                          'Usernames must have only letters,'
                                          'numbers, dots or underscores')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')
    ])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

class Change_password(FlaskForm):
    oldpassword = PasswordField('oldPassword', validators=[DataRequired()])
    newpassword = PasswordField('newPassword', validators=[DataRequired(), EqualTo('newpassword2', message='Passwords must match.')])
    newpassword2 = PasswordField('newpassword', validators=[DataRequired()])
    submit = SubmitField('Change Password')

class Change_email(FlaskForm):
    newemail = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()])
    submit = SubmitField('Change email')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

class need_reset_password(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),Email()])
    submit = SubmitField('Send email')

    def validate_email(self, field):
        if not User.query.filter_by(email=field.data).first():
            raise ValidationError("Email didn't registe.")

class reset_the_password(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    newpassword = PasswordField('newPassword',
                                validators=[DataRequired(), EqualTo('newpassword2', message='Passwords must match.')])
    newpassword2 = PasswordField('newpassword', validators=[DataRequired()])
    submit = SubmitField('Reset Password')