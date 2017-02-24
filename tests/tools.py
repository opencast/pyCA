# -*- coding: utf-8 -*-
'''
Some helper tools for pyCA testing.
'''


class ShouldFailException(Exception):
    args = [None, 0]


def should_fail(*args, **kwargs):
    raise ShouldFailException()
