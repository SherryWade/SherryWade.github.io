from flask import render_template, flash, redirect, url_for
from flask_login import login_required
from ..auth.models import User
from ..auth.forms import RegistrationForm
from ..auth.email import send_password_reset_email
from .. import db
from . import bp


@bp.route('/list', methods=['GET'])
@login_required
def list():
    users = db.session.query(User).all()

    return render_template('user/list.html', users=users)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = RegistrationForm()

    if form.validate_on_submit():
        user = User(username=form.username.data,
                    email=form.email.data)
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        if user:
            send_password_reset_email(user)

        flash('User was created successfully! An email has been sent to the user to set the account password.',
              'success')

        return redirect(url_for('user.list'))

    return render_template('/user/add.html', form=form)
