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


class CurlMock():
    CAINFO = 0
    HTTPAUTH = 1
    HTTPAUTH_DIGEST = 2
    HTTPHEADER = 3
    HTTPPOST = 4
    HTTP_CODE = 5
    SSL_VERIFYHOST = 6
    SSL_VERIFYPEER = 7
    URL = 8
    USERPWD = 9
    WRITEFUNCTION = 10

    def setopt(self, *args):
        pass

    def perform(self):
        pass

    def getinfo(self, *args):
        return 200

    def close(self):
        pass
