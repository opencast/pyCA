# -*- coding: utf-8 -*-
'''
Some helper tools for pyCA testing.
'''


class ShouldFailException(Exception):
    pass


def should_fail(*args, **kwargs):
    raise ShouldFailException()
