from flask import render_template, current_app
from .. import send_email


def send_groups_and_events_email(form):
    name = form.name.data
    email = form.email.data
    phone = form.phone.data
    description = form.description.data

    send_email(subject='Groups and Events Form',

               recipients=['sherry@charlestonmysteries.com'],

               text_body=render_template('blackfedora/email/groups_and_events.txt',
                                         name=name, email=email, phone=phone, description=description),

               html_body=render_template('blackfedora/email/groups_and_events.html',
                                         name=name, email=email, phone=phone, description=description))
