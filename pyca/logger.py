# -*- coding: utf-8 -*-
'''
    pyca.logger
    ~~~~~~~~~~~

    :copyright: 2020, Sven Haardiek <sven@haardiek.de>
    :license: LGPL – see license.lgpl for more details.
'''
import logging
from datetime import datetime


class DatabaseHandler(logging.Handler):
    '''Logging Handler which logs into the database.'''
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        '''Actually log to the database.
        Overrides the logging.Handler emit function.
        '''
        # delay database import to first call to circumvent circular
        # dependency.
        from pyca import db

        session = db.get_session()
        # format also make record.message available
        formatted = self.format(record)
        try:
            session.add(
                db.Log(
                    name=record.name,
                    levelname=record.levelname,
                    lineno=record.lineno,
                    funcName=record.funcName,
                    created=datetime.fromtimestamp(record.created),
                    message=record.message,
                    formatted=formatted,
                )
            )
            session.commit()
        finally:
            session.close()
