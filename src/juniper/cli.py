import argparse
from luigi import build
from juniper.data.tasks import EventXWalk, LoadShowData, RawTransactionData, InHouseTickets, InHouseReservationsXWalk
from juniper.data.tasks import LoadInHouseTickets, LoadWebPurchases


def version(args=None):
    from juniper import __version__

    print('Version: {}'.format(__version__))


def db_commands(args=None):

    if args.init:
        print("Database Init")


def webserver(args=None):
    from juniper.app import create_app

    return create_app().run()


def data_pipeline(args=None):

    build([
        EventXWalk(),
        LoadShowData(),
        RawTransactionData(),
        InHouseTickets(),
        InHouseReservationsXWalk(), LoadInHouseTickets(), LoadWebPurchases()
    ], local_scheduler=True)


parser = argparse.ArgumentParser(description='Command description.')
subparsers = parser.add_subparsers()

# create the parser for the "a" command
parser_db = subparsers.add_parser('db', help='db help')
parser_db.add_argument('--init', action='store_true', help='Initialize Database')
parser_db.set_defaults(func=db_commands)

parser_version = subparsers.add_parser('version', help='Version help')
parser_version.set_defaults(func=version)

parser_webserver = subparsers.add_parser('webserver', help='Web Server')
parser_webserver.set_defaults(func=webserver)

parser_webserver = subparsers.add_parser('data_pipeline', help='Data Pipeline')
parser_webserver.set_defaults(func=data_pipeline)


def main(args=None):
    args = parser.parse_args(args=args)
    args.func(args)
