#!/bin/env python
# -*- coding: utf-8 -*-

# Set default encoding to UTF-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import getopt
import os

if __name__ == '__main__':
	if sys.argv[1:] == ['run']:
		print('daemon…')
	elif sys.argv[1:] == ['daemon']:
		print('daemon…')
	elif sys.argv[1:] == ['test']:
		from pyca import ca
		ca.test()
	elif sys.argv[1:] == ['run']:
		from pyca import ca
		ca.run()
	elif sys.argv[1:] == ['ui']:
		from pyca import ui
		ui.app.run(host='0.0.0.0')
	else:
		print('Usage: %s run | daemon | test | ui' % sys.argv[0])
