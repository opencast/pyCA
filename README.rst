PyCA – Opencast Capture Agent
=============================

.. image:: https://github.com/opencast/pyCA/workflows/Test%20pyCA/badge.svg?branch=master
    :target: https://github.com/opencast/pyCA/actions?query=workflow%3A%22Test+pyCA%22+branch%3Amaster
    :alt: Test pyCA GitHub Workflow Status
.. image:: https://coveralls.io/repos/github/opencast/pyCA/badge.svg?branch=master
    :target: https://coveralls.io/github/opencast/pyCA?branch=master
    :alt: Test Coverage
.. image:: https://img.shields.io/github/license/opencast/pyCA
    :target: https://github.com/opencast/pyCA/blob/master/license.lgpl
    :alt: LGPL-3 license

**PyCA** is a fully functional Opencast_ capture agent written in Python.
It is free software licensed under the terms of the `GNU Lesser General Public
License`_.

The goals of pyCA are to be…

- flexible for any kind of capture device
- simplistic in code and functionality
- nonrestrictive in terms of choosing capture software

PyCA can be run on almost any kind of devices: A regular PC equipped with
capture cards, a server to capture network streams, small boards or embedded
devices like the `Raspberry Pi`_.


Python Versions
---------------

PyCA requires Python ≥ 3.6. Older versions of Python will not work.


Documentation
-------------

For a detailed installation guide, take a look at the `PyCA documentation`_.


Quick Install for Experienced Users
-----------------------------------

PyCA is configured to use FFmpeg_ by default.
Make sure to have it installed or adjust the configuration to use something else.

.. code-block:: bash

    git clone https://github.com/opencast/pyCA.git
    cd pyCA
    python3 -m venv venv
    . ./venv/bin/activate
    pip install -r requirements.txt
    npm ci
    vim etc/pyca.conf <-- Edit the configuration
    ./start.sh


.. _Opencast: https://opencast.org
.. _GNU Lesser General Public License: https://raw.githubusercontent.com/opencast/pyCA/master/license.lgpl
.. _Raspberry Pi: https://raspberrypi.org
.. _Travis configuration: https://raw.githubusercontent.com/opencast/pyCA/master/.travis.yml
.. _FFmpeg: https://ffmpeg.org
.. _PyCA documentation: https://github.com/opencast/pyCA/tree/master/docs#welcome-to-the-pyca-documentation
