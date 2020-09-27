from flask import render_template
from .. import send_email


def send_ticket_confirmation_email(recipient, reservation, event):

    html_body = render_template('blackfedora/email/ticket_confirmation.html',
                                reservation=reservation,
                                event=event)

    txt_body = render_template('blackfedora/email/ticket_confirmation.txt',
                               reservation=reservation,
                               event=event)

    send_email(subject='Your Black Fedora Confirmation',
               recipients=[recipient],
               text_body=txt_body, html_body=html_body, bcc=['sherry@charlestonmysteries.com'])
