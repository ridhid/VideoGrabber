#coding: utf-8
__author__ = 'root'

import logging
import sys

def logg(call):
    def call_logg(*args, **kwargs):
        to_log = "".join([call.__name__, call.args])
        logging.debug(u'start' + to_log)
        call(*args, **kwargs)
        logging.debug(u'end ' + call.__name__)

    return call_logg


def catch_exception(call):
    def try_call(*args, **kwargs):
        try:
            call(*args, **kwargs)
        except:
            logging.error(u'in ' + call.__name__)
    return try_call