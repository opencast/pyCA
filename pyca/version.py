# -*- coding: utf-8 -*-
'''
	pyca.version
	~~~~~~~~~~~~

	:copyright: 2015, Lars Kiesow <lkiesow@uos.de>

	:license: LGPL, see license.* for more details.

'''

# Version of pyCA represented as tuple
VERSION = (1, 0, 0)


# Version of pyCA represented as string
VERSION_STR = '.'.join([str(x) for x in VERSION])

VERSION_MAJOR = VERSION[:1]
VERSION_MINOR = VERSION[:2]
VERSION_FULL = VERSION

VERSION_MAJOR_STR = '.'.join([str(x) for x in VERSION_MAJOR])
VERSION_MINOR_STR = '.'.join([str(x) for x in VERSION_MINOR])
VERSION_FULL_STR = '.'.join([str(x) for x in VERSION_FULL])
