fork with following changes:

- capture.py will not start capturing if connection to opencast endpoint is not possible. The original function service() will endless stay in a while-loop with 5sec sleep until endpoint is connected. Events in the database will not start recording. To change this, the already installed flag 'force_update' is used. The while-loop will only wait and loop if force_update=True and return immediately if force_update=False. force_update is passed through the calling functions register_ca(), recording_state(), set_service_status_immediate(), update_agent_state()
- Inputs are now possible. The Definition in pyca.conf is extended with an item inputs
- register_ca() is extended by the registration of the input configuration
- Ingest only uploads the selected tracks from schedule events





.. image:: https://github.com/opencast/pyCA/actions/workflows/test.yml/badge.svg
    :target: https://github.com/opencast/pyCA/actions/workflows/test.yml
    :alt: Test pyCA GitHub Workflow Status
.. image:: https://img.shields.io/github/license/opencast/pyCA
    :target: https://github.com/opencast/pyCA/blob/master/license.lgpl
    :alt: LGPL-3 license

PyCA – Opencast Capture Agent
=============================
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
