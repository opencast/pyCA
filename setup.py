#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Setup file for pyCA module
'''

from setuptools import setup, find_packages
import pyca.version

setup(name='pyca',
      packages=find_packages(),
      version=pyca.version.VERSION_FULL_STR,
      description='Python Matterhorn Capture Agents',
      author='Lars Kiesow',
      author_email='lkiesow@uos.de',
      url='http://lkiesow.github.io/pyCA',
      keywords=['capture', 'lecture recordings', 'opencast', 'capture agent'],
      license='LGPLv3+',
      install_requires=['icalendar', 'pycurl', 'python-dateutil', 'configobj'],
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Education',
          'Intended Audience :: Information Technology',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU Lesser General Public License v3'
          ' or later (LGPLv3+)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 3',
          'Topic :: Education',
          'Topic :: Multimedia :: Sound/Audio :: Capture/Recording',
          'Topic :: Multimedia :: Video :: Capture'],
      long_description='''\
PyCA is a fully functional Opencast Matterhorn capture agent written in Python.
It is free software licenced under the terms of the GNU Lesser General Public
License.
''')
