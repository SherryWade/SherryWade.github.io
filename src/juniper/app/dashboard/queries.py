from juniper.app.events.models import Event
from datetime import datetime
from juniper.app import db
from sqlalchemy import func


def sales_cnts_by_week():
    curr_year = datetime.now().year

    cnts = db.session.query(func.week(Event.start_time),
                            func.count(func.week(Event.start_time)))\
        .group_by(func.week(Event.start_time))\
        .filter(func.year(Event.start_time) == curr_year).all()

    return cnts
