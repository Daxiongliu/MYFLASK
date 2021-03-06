from flask import render_template, redirect, request, url_for, flash
from . import auth
from .. import db
from flask_login import login_user, logout_user, login_required, current_user
from ..models import User
from .forms import LoginForm, RegistrationForm, Change_password, need_reset_password, reset_the_password, Change_email
from ..email import send_email

@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account','auth/email/confirm', user=user, token=token)
        flash('You can now login.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and request.endpoint[:5] != 'auth.':
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('/changepassword', methods=['GET', 'POST'])
@login_required
def change_password():
    form = Change_password()
    if form.validate_on_submit():
        if not current_user.verify_password(form.oldpassword.data):
            flash('oldpassword is worong!')
            return redirect(url_for('auth.change_password'))
        current_user.password = form.newpassword.data
        db.session.add(current_user)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('auth/change_password.html', form=form)

@auth.route('/resetpassword', methods=['GET', 'POST'])
def reset_password():
    form =  need_reset_password()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/reset_password', user=user, token=token)
        flash('A new confirmation email has been sent to you by email.')
    return render_template('auth/reset_password.html', form=form)

@auth.route('/resetpassword/<token>', methods=['GET', 'POST'])
def password_reset(token):
    form = reset_the_password()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.reset_password(token):
            user.password = form.newpassword.data
            db.session.add(user)
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            flash('email error!')
            return redirect(url_for('auth.reset_password'))
    return render_template('auth/password_reset.html', form=form)

@auth.route('/resetemail', methods=['GET', 'POST'])
@login_required
def change_email():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/change_email', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('auth.login'))

@auth.route('/resetemail/<token>', methods=['GET', 'POST'])
@login_required
def changetheemail(token):
    form = Change_email()
    if form.validate_on_submit():
        if current_user.changeemail(token):
            current_user.email = form.newemail.data
            db.session.add(current_user)
            flash('You have change your email.')
    return render_template('auth.change_email.html', form=form)








