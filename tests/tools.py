# -*- coding: utf-8 -*-
'''
Some helper tools for pyCA testing.
'''


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
