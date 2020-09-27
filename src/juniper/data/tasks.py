from luigi import ExternalTask, Task, LocalTarget
from luigi.contrib.s3 import S3Target
from juniper.config import EXTERNAL_DATA_DIR, INTERIM_DATA_DIR
from juniper.app import create_app, db
from juniper.app.events.models import Audience, Event
from juniper.app.reservations.models import Reservation, Ticket
from juniper.app.product.models import Product, PriceSpecification, Offer
from juniper.app.payments.models import (TransactionRequest, CustomerAddress, CustomerData, LineItem,
                                         Payment, PaymentType, CreditCard, TransactionResponse)
from datetime import datetime
from hashlib import sha256
import pandas as pd
import numpy as np
import json
import os


app = create_app()

S3_PATH = 's3://ai.charleston/juniper/blackfedora/data/{}'

"""
--- Helper Functions
"""


def identifier(entity, x):

    return sha256("{}{}".format(entity, int(x)).encode()).hexdigest()


ticket_prices = {'adult': 24, 'child': 15, 'college': 22}
tax_rate = 0.05

product_dict = {'adult': {'name': "Adult Ticket",
                                  'price': ticket_prices['adult']},
                'child': {'name': "Child Ticket",
                                  'price': ticket_prices['child']},
                'college': {'name': 'College Ticket',
                                    'price': ticket_prices['college']}}


def get_total(num_adult, num_child, num_college):
    subtotal = np.sum([num_adult*ticket_prices['adult'],
                       num_child*ticket_prices['child'],
                       num_college*ticket_prices['college']])

    taxes = round(tax_rate*subtotal, 2)

    total = np.sum([subtotal, taxes])

    return float(subtotal), float(taxes), float(total)


def standardize_str(s):
    # Standardize Spaces
    s = " ".join(s.split())
    s = s.strip()
    s = s.upper()

    return s


"""
--- Show Data Tasks
"""


class S3ShowMetaData(ExternalTask):
    PATH = S3_PATH.format('show_meta.csv')

    def output(self):
        return S3Target(self.PATH)


class RawShowMetaData(Task):

    def requires(self):
        return S3ShowMetaData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'show_meta.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class S3ShowData(ExternalTask):
    PATH = S3_PATH.format('shows.csv')

    def output(self):
        return S3Target(self.PATH)


class RawShowData(Task):

    def requires(self):
        return S3ShowData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'show.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class CleanShowData(Task):
    def requires(self):
        return {'show': RawShowData(),
                'meta': RawShowMetaData()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'to_load.shows'))

    def run(self):
        with self.input()['show'].open('r') as f:
            df = pd.read_csv(f)

        with self.input()['meta'].open('r') as f:
            df_meta = pd.read_csv(f)

        """
        Mapping
        -------
        show_id         -> id
        title           -> name
        description     -> description
        rating          -> rating 
        recommended_for -> audience_type
        calendar_code   -> calendar_code
        """

        df.columns = ["id", "name", "description", "rating",
                      "audience_type", "calendar_code"]

        df['maximum_attendee_capacity'] = 60

        df_show = df.merge(df_meta, on='id', how='left')

        # Create a unique identifier for each show, which is the hash value of 'show'
        # concatenated with the show id
        df_show['identifier'] = df_show['id'].apply(lambda x: identifier('show', x))

        with self.output().open('w') as f:
            df_show.to_csv(f, index=False)


"""
--- Event Data Tasks
"""


class S3EventScheduleData(ExternalTask):
    PATH = S3_PATH.format('event_schedule.csv')

    def output(self):
        return S3Target(self.PATH)


class RawEventScheduleData(Task):

    def requires(self):
        return S3EventScheduleData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'event_schedule.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class CleanEventSchedule(Task):

    def requires(self):
        return RawEventScheduleData()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'event_schedule.csv'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        df_events = df[['id', 'show_id', 'timestamp']].copy()

        df_events['start_time'] = df_events['timestamp'].apply(lambda x: datetime.fromtimestamp(int(x)))

        df_events = df_events.drop(['timestamp'], axis=1)

        df_events['event_identifier'] = df_events['id'].apply(lambda x: identifier('event', x))
        df_events['show_identifier'] = df_events['show_id'].apply(lambda x: identifier('show', x))

        with self.output().open('w') as f:
            df_events.to_csv(f, index=False)


class LoadShowData(Task):

    def requires(self):
        return CleanShowData()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.shows'))

    def run(self):

        with self.input().open('r') as f:
            df = pd.read_csv(f)
            df = df.fillna('')
            df['calendar_code'] = ''

        with app.app_context():
            for row in df.iterrows():
                # rating,audience_type, slug, disambiguating_description,active
                s = row[1]

                event = Event()
                event.identifier = s['identifier']
                event.name = s['name']
                event.description = s['description']
                event.calendar_code = s['calendar_code']
                event.maximum_attendee_capacity = s['maximum_attendee_capacity']
                event.primary_image = s['primary_image']
                event.secondary_image = s['secondary_image']
                event.slug = s['slug']
                event.disambiguating_description = s['disambiguating_description']
                event.alternate_name = s['alternate_name']
                event.is_active = int(s['active'])

                audience = Audience()
                audience.name = s['rating']
                audience.audience_type = s['audience_type']

                event.audience = audience

                db.session.add(event)

            db.session.commit()

        with self.output().open('w') as f:
            f.write('')


class LinkedEventData(Task):

    def requires(self):
        return {'data': CleanEventSchedule(),
                'shows_loads': LoadShowData()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'to_load.events'))

    def run(self):

        with self.input()['data'].open('r') as f:
            df = pd.read_csv(f)

        with app.app_context():
            shows = db.session.query(Event).all()
            xwalk = pd.DataFrame([[s.identifier, s.id] for s in shows], columns=['identifier', 'new_show_id'])

            df_linked = df.merge(xwalk, left_on='show_identifier', right_on='identifier')

        with self.output().open('w') as f:
            df_linked.to_csv(f, index=False)


class LoadEventData(Task):

    def requires(self):
        return LinkedEventData()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.events'))

    def run(self):

        with self.input().open('r') as f:
            df = pd.read_csv(f)
            df['start_time'] = pd.to_datetime(df['start_time'])

        with app.app_context():
            for row in df.iterrows():
                # rating,audience_type, slug, disambiguating_description,active
                s = row[1]

                event = Event()
                event.parent_id = s['new_show_id']
                event.identifier = s['event_identifier']
                event.start_time = str(s['start_time'])

                db.session.add(event)

            db.session.commit()

        with self.output().open('w') as f:
            f.write('')


class EventXWalk(Task):
    def requires(self):
        return {'link': LinkedEventData(),
                'loaded': LoadEventData()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'xwalk.event'))

    def run(self):

        with self.input()['link'].open('r') as f:
            xwalk = pd.read_csv(f)
            xwalk = xwalk[['id', 'event_identifier']]
            xwalk.columns = ['old_event_id', 'event_identifier']

        with app.app_context():
            shows = db.session.query(Event).all()
            df_events = pd.DataFrame([[s.identifier, s.id] for s in shows],
                                     columns=['event_identifier', 'new_event_id'])

        xwalk = xwalk.merge(df_events, on='event_identifier')

        with self.output().open('w') as f:
            xwalk.to_csv(f, index=False)



"""
--- Tickets and Transactions
"""


class S3TransactionData(ExternalTask):
    PATH = S3_PATH.format('transactions.csv')

    def output(self):
        return S3Target(self.PATH)


class RawTransactionData(Task):

    def requires(self):
        return S3TransactionData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'transactions.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class S3TicketData(ExternalTask):
    PATH = S3_PATH.format('ticket.csv')

    def output(self):
        return S3Target(self.PATH)


class RawTicketData(Task):

    def requires(self):
        return S3TicketData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'ticket.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class S3PersonData(ExternalTask):
    PATH = S3_PATH.format('person.csv')

    def output(self):
        return S3Target(self.PATH)


class RawPersonData(Task):

    def requires(self):
        return S3PersonData()

    def output(self):
        return LocalTarget(os.path.join(EXTERNAL_DATA_DIR, 'person.csv'))

    def run(self):
        with self.output().open('w') as f:
            with self.input().open('r') as s3_file:
                f.write(s3_file.read())


class InHouseReservations(Task):

    def requires(self):
        return {'person': RawPersonData(),
                'ticket': RawTicketData()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'reservations.in_house.csv'))

    def run(self):
        with self.input()['person'].open('r') as f:
            df_person = pd.read_csv(f)

        with self.input()['ticket'].open('r') as f:
            df_ticket = pd.read_csv(f)

        df_ticket = df_ticket[['ticket_id', 'num_adults', 'num_child',
                               'num_college', 'personKey', 'event_id', 'timestamp']]
        df_person = df_person[['key', 'firstname', 'lastname', 'email']]

        reservations = df_ticket.merge(df_person, left_on='personKey', right_on='key')

        # For some reason there is an row with NaN Event ID, so we will drop it.
        reservations = reservations[~reservations.event_id.isna()]
        reservations['created'] = reservations['timestamp'].apply(lambda x: datetime.fromtimestamp(int(x)))
        reservations = reservations.drop(['timestamp', 'personKey', 'key'], axis=1)

        reservations['reservation_identifier'] = reservations['ticket_id'].apply(lambda x: identifier('reservation', x))
        reservations['event_identifier'] = reservations['event_id'].apply(lambda x: identifier('event', x))

        reservations['firstname'] = reservations['firstname'].fillna('')
        reservations['lastname'] = reservations['lastname'].fillna('')

        reservations['num_adults'] = reservations['num_adults'].fillna(0)
        reservations['num_child'] = reservations['num_child'].fillna(0)
        reservations['num_college'] = reservations['num_college'].fillna(0)

        with self.output().open('w') as f:
            reservations.to_csv(f, index=False)


class InHouseTickets(Task):

    def requires(self):
        return InHouseReservations()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'tickets.in_house.csv'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        reservations = df[['num_adults', 'num_child', 'num_college', 'reservation_identifier', 'event_identifier']]
        reservations = reservations.fillna(0)

        tickets = []
        for res in reservations.values:
            for adult_cnt in range(int(res[0])):
                tickets.append([res[3], res[4], 'adult', ticket_prices['adult']])

            for child_cnt in range(int(res[1])):
                tickets.append([res[3], res[4], 'child', ticket_prices['child']])

            for college_cnt in range(int(res[2])):
                tickets.append([res[3], res[4], 'college', ticket_prices['college']])

        tickets = pd.DataFrame(tickets, columns=['reservation_identifier', 'event_identifier', 'type', 'price'])

        with self.output().open('w') as f:
            tickets.to_csv(f, index=False)


class LoadInHouseReservations(Task):

    def requires(self):
        return {'reservations': InHouseReservations(),
                'xwalk': EventXWalk()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.in_house_reservations'))

    def run(self):

        with self.input()['reservations'].open('r') as f:
            df = pd.read_csv(f)

        with self.input()['xwalk'].open('r') as f:
            xwalk = pd.read_csv(f)

        df_res = df.merge(xwalk, on='event_identifier')
        df_res['created'] = pd.to_datetime(df_res['created'])
        df_res = df_res.fillna('')

        with app.app_context():
            for row in df_res.iterrows():
                r = row[1]

                subtotal, taxes, total = get_total(r.num_adults, r.num_child, r.num_college)

                res = Reservation()
                res.booking_time = str(r.created)
                res.reservation_for_id = r.new_event_id
                res.under_name = standardize_str('{} {}'.format(r.firstname, r.lastname))
                res.total_price = total
                res.identifier = r.reservation_identifier

                # Transaction Information
                trans_request = TransactionRequest()
                trans_request.amount = total
                trans_request.taxes = taxes
                trans_request.fees = 0

                bill_to = CustomerAddress()
                bill_to.first_name = standardize_str('{}'.format(r.firstname))
                bill_to.last_name = standardize_str('{}'.format(r.lastname))

                cust = CustomerData()
                cust.email = r.email

                # TODO: Add line items
                # Line Items
                line_items = []
                if r.num_adults > 0:
                    a_li = LineItem()
                    a_li.name = product_dict['adult']['name']
                    a_li.unit_price = product_dict['adult']['price']
                    a_li.fee = 0
                    a_li.quantity = int(r.num_adults)
                    line_items.append(a_li)

                if r.num_child > 0:
                    c_li = LineItem()
                    c_li.name = product_dict['child']['name']
                    c_li.unit_price = product_dict['child']['price']
                    c_li.fee = 0
                    c_li.quantity = int(r.num_child)
                    line_items.append(c_li)

                if r.num_college > 0:
                    col_li = LineItem()
                    col_li.name = product_dict['college']['name']
                    col_li.unit_price = product_dict['college']['price']
                    col_li.fee = 0
                    col_li.quantity = int(r.num_college)
                    line_items.append(col_li)

                payment = Payment()
                payment.payment_type = PaymentType().EXTERNAL

                # Setup Objects
                trans_request.bill_to = bill_to
                trans_request.customer = cust
                trans_request.line_items = line_items
                trans_request.payment = payment

                res.transaction_request = trans_request

                db.session.add(res)

            db.session.commit()

        with self.output().open('w') as f:
            f.write('')


class InHouseReservationsXWalk(Task):
    def requires(self):
        return {'link': InHouseReservations(),
                'loaded': LoadInHouseReservations()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'xwalk.in_house_reservations'))

    def run(self):

        with self.input()['link'].open('r') as f:
            xwalk = pd.read_csv(f)
            xwalk = xwalk[['ticket_id', 'reservation_identifier']]
            xwalk.columns = ['old_res_id', 'identifier']

        with app.app_context():
            res = db.session.query(Reservation).all()
            df_events = pd.DataFrame([[r.identifier, r.id] for r in res],
                                     columns=['identifier', 'new_reservation_id'])

        xwalk = xwalk.merge(df_events, on='identifier')

        with self.output().open('w') as f:
            xwalk.to_csv(f, index=False)


class InHouseTicketsForLoad(Task):

    def requires(self):
        return {'tickets': InHouseTickets(),
                'r_xwalk': InHouseReservationsXWalk(),
                'e_xwalk': EventXWalk()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'to_load.in_house_tickets'))

    def run(self):
        with self.input()['tickets'].open('r') as f:
            df_tickets = pd.read_csv(f)

        with self.input()['r_xwalk'].open('r') as f:
            df_r_xwalk = pd.read_csv(f)

        with self.input()['e_xwalk'].open('r') as f:
            df_e_xwalk = pd.read_csv(f)

        tickets = df_tickets.merge(df_r_xwalk, left_on='reservation_identifier', right_on='identifier')
        tickets = tickets.merge(df_e_xwalk, on='event_identifier')

        tickets = tickets[['type', 'price', 'new_reservation_id', 'new_event_id']]

        with self.output().open('w') as f:
            tickets.to_csv(f, index=False)


class CreatePricingOptions(Task):

    def requires(self):
        return InHouseTicketsForLoad()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.pricing_options'))

    def run(self):

        with app.app_context():
            for type in product_dict:
                p = product_dict[type]

                ps = PriceSpecification()
                ps.price = p['price']

                product = Product()
                product.name = p['name']
                product.category = 'TICKET'
                product.price_specification = ps

                offer = Offer()
                offer.product = product
                offer.identifier = type

                db.session.add(offer)

            db.session.commit()

        with self.output().open('w') as f:
            f.write('')


class LoadInHouseTickets(Task):

    def requires(self):
        return {'po': CreatePricingOptions(),
                'tickets': InHouseTicketsForLoad()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.in_house_tickets'))

    def run(self):
        with self.input()['tickets'].open('r') as f:
            tickets = pd.read_csv(f)

        with app.app_context():
            offers = db.session.query(Offer).all()
            offer_id = {offer.identifier: offer.id for offer in offers}

            for t in tickets.iterrows():
                item = t[1]

                ticket = Ticket()
                ticket.face_value = item.price
                ticket.event_id = item.new_event_id
                ticket.reservation_id = item.new_reservation_id
                ticket.offer_id = offer_id[item.type]

                db.session.add(ticket)

            db.session.commit()

        with self.output().open('w') as f:
            f.write('')


class WebPurchases(Task):

    def requires(self):
        return {'xwalk': EventXWalk(),
                'tickets': RawTicketData(),
                'transactions': RawTransactionData()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'web_purchases.csv'))

    def run(self):
        with self.input()['xwalk'].open('r') as f:
            xwalk = pd.read_csv(f)

        with self.input()['tickets'].open('r') as f:
            tickets = pd.read_csv(f)

            drop_cols = ['personKey', 'rand_id', 'seat_with', 'comments', 'marketing', 'timestamp']

            tickets = tickets.drop(drop_cols, axis=1)

        with self.input()['transactions'].open('r') as f:
            transactions = pd.read_csv(f)

            drop_cols = ['marketing', 'seat_with']

            transactions = transactions.drop(drop_cols, axis=1)
            transactions = transactions[~transactions['authorized'].isna()]

        web_purchases = transactions.merge(tickets, on='ticket_id')
        web_purchases = web_purchases.merge(xwalk, left_on='event_id', right_on='old_event_id')

        drop_cols = ['event_identifier', 'event_id', 'old_event_id']

        web_purchases = web_purchases.drop(drop_cols, axis=1)
        web_purchases['num_college'] = web_purchases['num_college'].fillna(0)
        web_purchases['num_adults'] = web_purchases['num_adults'].fillna(0)
        web_purchases['zip'] = web_purchases['zip'].fillna('')
        web_purchases['auth_code'] = web_purchases['auth_code'].fillna('')
        web_purchases['timestamp'] = web_purchases['timestamp'].apply(lambda x: datetime.fromtimestamp(int(x)))

        with self.output().open('w') as f:
            web_purchases.to_csv(f, index=False)


def load_web_purchases_by_year(df, year):
    df['num_adults'] = df['num_adults'].astype(int)
    df['num_college'] = df['num_college'].astype(int)
    df['num_child'] = df['num_child'].astype(int)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.fillna('')

    msk = df.timestamp.dt.year == year

    df = df[msk]

    with app.app_context():
        offers = db.session.query(Offer).all()
        offer_id = {offer.identifier: offer.id for offer in offers}

        for i in df.iterrows():
            item = i[1]

            subtotal, taxes, total = get_total(item.num_adults, item.num_child, item.num_college)

            reservation = Reservation()
            reservation.booking_time = str(item.timestamp)
            reservation.reservation_for_id = item.new_event_id
            reservation.under_name = standardize_str('{} {}'.format(item.firstname, item.lastname))
            reservation.total_price = total

            tickets = []
            line_items = []
            for _ in range(item.num_adults):
                ticket = Ticket()
                ticket.face_value = product_dict['adult']['price']
                ticket.event_id = item.new_event_id
                ticket.offer_id = offer_id['adult']
                ticket.created = str(item.timestamp)
                tickets.append(ticket)

            if item.num_adults > 0:
                li = LineItem()
                li.name = product_dict['adult']['name']
                li.unit_price = product_dict['adult']['price']
                li.fee = 0
                li.quantity = item.num_adults
                line_items.append(li)

            for _ in range(item.num_child):
                ticket = Ticket()
                ticket.face_value = product_dict['child']['price']
                ticket.event_id = item.new_event_id
                ticket.offer_id = offer_id['child']
                ticket.created = str(item.timestamp)
                tickets.append(ticket)

            if item.num_child > 0:
                li = LineItem()
                li.name = product_dict['child']['name']
                li.unit_price = product_dict['child']['price']
                li.fee = 0
                li.quantity = item.num_child
                line_items.append(li)

            for _ in range(item.num_college):
                ticket = Ticket()
                ticket.face_value = product_dict['college']['price']
                ticket.event_id = item.new_event_id
                ticket.offer_id = offer_id['college']
                ticket.created = str(item.timestamp)
                tickets.append(ticket)

            if item.num_college > 0:
                li = LineItem()
                li.name = product_dict['college']['name']
                li.unit_price = product_dict['college']['price']
                li.fee = 0
                li.quantity = item.num_college
                line_items.append(li)

            # Transaction Information
            trans_request = TransactionRequest()
            trans_request.ip_address = item.ip_address
            trans_request.amount = item.amount
            trans_request.taxes = taxes
            trans_request.created = str(item.timestamp)
            trans_request.fees = 0

            bill_to = CustomerAddress()
            bill_to.first_name = standardize_str('{}'.format(item.firstname))
            bill_to.last_name = standardize_str('{}'.format(item.lastname))
            bill_to.address = standardize_str('{}'.format(item.address))
            bill_to.zip = standardize_str('{}'.format(item.zip))
            bill_to.created = str(item.timestamp)

            cust = CustomerData()
            cust.email = item.email
            cust.phone = item.phone
            cust.created = str(item.timestamp)

            payment = Payment()
            payment.payment_type = PaymentType().CREDIT_CARD
            payment.created = str(item.timestamp)

            cc = CreditCard()
            cc.number = item.last_four
            cc.created = str(item.timestamp)
            payment.credit_card = cc

            response = TransactionResponse()
            response.response_code = str(item.auth_code)
            response.approved = item.authorized == 'Y'

            response_body = {'avs_response': item.avs_response, 'cvv2_response': item.cvv2_response}
            response.response_body = json.dumps(response_body)

            # Setup Objects
            trans_request.bill_to = bill_to
            trans_request.customer = cust
            trans_request.line_items = line_items
            trans_request.payment = payment
            trans_request.transaction_response = response

            reservation.transaction_request = trans_request
            reservation.tickets = tickets

            db.session.add(reservation)

        db.session.commit()


class Load2020WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2020.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2020)

        with self.output().open('w') as f:
            f.write('')


class Load2019WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2019.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2019)

        with self.output().open('w') as f:
            f.write('')


class Load2018WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2018.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2018)

        with self.output().open('w') as f:
            f.write('')


class Load2017WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2017.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2017)

        with self.output().open('w') as f:
            f.write('')


class Load2016WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2016.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2016)

        with self.output().open('w') as f:
            f.write('')


class Load2015WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2015.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2015)

        with self.output().open('w') as f:
            f.write('')


class Load2014WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2014.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2014)

        with self.output().open('w') as f:
            f.write('')


class Load2013WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2013.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2013)

        with self.output().open('w') as f:
            f.write('')


class Load2012WebPurchases(Task):

    def requires(self):
        return WebPurchases()

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded2012.web_purchases'))

    def run(self):
        with self.input().open('r') as f:
            df = pd.read_csv(f)

        load_web_purchases_by_year(df, 2012)

        with self.output().open('w') as f:
            f.write('')


class LoadWebPurchases(Task):

    def requires(self):
        return {'2020': Load2020WebPurchases(),
                '2019': Load2019WebPurchases(),
                '2018': Load2018WebPurchases(),
                '2017': Load2017WebPurchases(),
                '2016': Load2016WebPurchases(),
                '2015': Load2015WebPurchases(),
                '2014': Load2016WebPurchases(),
                '2013': Load2013WebPurchases(),
                '2012': Load2012WebPurchases()}

    def output(self):
        return LocalTarget(os.path.join(INTERIM_DATA_DIR, 'loaded.web_purchases'))

    def run(self):
        with self.output().open('w') as f:
            f.write('')
