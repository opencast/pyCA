# -*- coding: utf-8 -*-
'''
Some helper tools for pyCA testing.
'''

import logging

try:
    from importlib import reload  # noqa
except ImportError:
    from imp import reload  # noqa


# Raise log level above maximum to silence logging in tests.
# Then ensure that the log leven cannot be reset
logging.getLogger('').setLevel(logging.CRITICAL * 100)
logging.getLogger('').setLevel = lambda x: True


class ShouldFailException(Exception):
    args = [None, 0]


def should_fail(*args, **kwargs):
    raise ShouldFailException()


def __terminate():
    global _terminate
    _terminate -= 1
    return _terminate < 0


def terminate_fn(num):
    global _terminate
    _terminate = num
    return __terminate
