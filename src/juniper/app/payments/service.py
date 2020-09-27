from juniper.app.payments.models import TransactionRequest, CustomerAddress, CreditCard, CustomerData
from juniper.app.payments.models import Payment, LineItem, TransactionResponse
from juniper.app import db
from juniper.app.product.models import Offer
from juniper.app import get_session_id
from flask import request, current_app
import pandas as pd
import numpy as np
import requests
import json
import os


class AuthorizeNet:

    def __init__(self, transaction_request):
        self.transaction_request = transaction_request

    def process_transaction(self):
        pass


class EProcessingNetwork:

    def __init__(self, transaction_request, epn_account=None, restrict_key=None):
        self.url = 'https://www.eprocessingnetwork.com/cgi-bin/epn/secure/tdbe/transact.pl'
        self.transaction_request = transaction_request
        self.epn_account = epn_account if epn_account else os.environ.get('EPN_ACCOUNT')
        self.restrict_key = restrict_key if restrict_key else os.environ.get('EPN_RESTRICT_KEY')
        self.payload = None
        self.transaction_response = None

    def _create_request_body(self):
        total = self.transaction_request.amount
        address = self.transaction_request.bill_to.address
        zip = self.transaction_request.bill_to.zip
        cc_num = self.transaction_request.payment.credit_card.number
        cvv2 = self.transaction_request.payment.credit_card.card_code

        date = self.transaction_request.payment.credit_card.expiration_date.split('/')
        exp_month = date[0]
        exp_year = date[1]

        payload = {
            "ePNAccount": self.epn_account,
            "RestrictKey": self.restrict_key,
            "RequestType": "transaction",
            "Total": str(total),
            "Address": address,
            "Zip": zip,
            "CardNo": cc_num,
            "ExpMonth": exp_month,
            "ExpYear": exp_year,
            "CVV2Type": "1",
            "CVV2": cvv2
        }

        self.payload = payload

        return payload

    def _process_response(self, r):
        r_json = r.json()

        response = TransactionResponse()
        response.approved = r_json['Success'] == 'Y'

        if response.approved:
            response.response_code = r_json['AuthCode']
        else:
            response.response_code = r_json['RespText']

        response.response_body = json.dumps(r_json)

        return response

    def process_transaction(self):
        payload = self._create_request_body()
        r = requests.post(self.url, json=payload)

        response = self._process_response(r)

        self.transaction_response = response

        return response


def mask_cc_number(num):
    msk = ''.join(['x' for _ in num[:-4]])
    msked_num = '{}{}'.format(msk, num[-4:])

    return msked_num
