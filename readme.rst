PyCA – Opencast Capture Agent
=============================

.. image:: https://travis-ci.org/opencast/pyCA.svg?branch=master
    :target: https://travis-ci.org/opencast/pyCA

.. image:: https://coveralls.io/repos/github/opencast/pyCA/badge.svg?branch=master
    :target: https://coveralls.io/github/opencast/pyCA?branch=master


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
***************

PyCA supports both Python 2 and Python 3. For Python 2, we only support
version 2.7, while for Python 3 we test against all recent versions. For a
detailed list of supported versions, have a look at the `Travis
configuration`_.

While we will continue to support Python 2 until the end of 2019, we recommend using
Python 3 if possible.

Installation
************

Note that, by default, pyCA is configured to use FFmpeg_ for recording and you
will need to have it installed as well if you do not change the configuration.

For **Debian based OS**, like Ubuntu or Raspbian, we maintain an APT repository.
Here is a short summary how to use it.

.. code-block:: shell

  # Install prerequisites
  apt-get install apt-transport-https

  # Include PyCA's Signing Key
  apt-key adv --fetch https://pyca.deb.opencast.org/gpg.key

  # Add the Repository
  echo "deb [arch=all] https://pyca.deb.opencast.org/opencast-pyca buster main" > /etc/apt/sources.list.d/opencast-pyca.list

  # Update your cache and install PyCA
  apt-get update
  apt-get install opencast-pyca

Once installed, you can use your regular update mechanisms to keep PyCA up to date.
The configuration can be found unter `/etc/pyca.conf` and contains reasonable defaults.
All PyCA components will be started automatically and you can reach the UI under http://localhost:8000.

On Fedora ≥ 31 or CentOS 8::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  dnf install gcc python3-devel libcurl-devel openssl-devel
  python3 -m venv venv
  . ./venv/bin/activate
  export PYCURL_SSL_LIBRARY=openssl
  pip install -r requirements.txt
  npm ci
  vim etc/pyca.conf <-- Edit the configuration
  ./start.sh

To restart pyCA later, reactivate the virtual environment by re-running
``. ./venv/bin/activate`` again. You can also include this in the start
script.

On Arch Linux::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  sudo pacman -S python-pycurl python-dateutil \
    python-configobj python-sqlalchemy
  npm ci
  vim etc/pyca.conf  <-- Edit the configuration
  ./start.sh

…or use the available AUR_ package.


Starting pyCA
*************

You can start pyCA by running

  ./start.sh

This start script will take an optional command allowing you to separately launch
pyCA services and run them as separate processes. By default (or using the
`run` command) all services except the UI are launced as a single process.

Available commands are:

 - `run`: Start all pyCA components except ui (default)
 - `capture`: Start pyCA capture service
 - `ingest`: Start pyCA ingest service
 - `schedule`: Start pyCA schedule service
 - `agentstate`: Start pyCA agentstate service
 - `ui`: Start web based user interface

As a service
------------

Example systemd unit files, corresponding to the commands above, are available
in ``init/systemd``. These unit files start and manage all pyCA services
separately to ensures that a problem in one of the services does not effect
other parts of pyCA.

Remember to increase the ``WatchdogSec`` parameter in the
``pyca-schedule.service`` unit file if you modify the ``update_frequency``
setting in pyCA, it's recommended to set it at least twice as long as the
update_frequency.

User Interface
**************

PyCA comes with a web interface to check the status of capture agent and
recordings. It is built as WSGI application and can be run using many
different WSGI servers (Apache httpd + mod_wsgi, Gunicorn, …).

For testing, it also comes with a minimal built-in server. Note that it is
meant for testing only and should not be used in production. It will also
listen to localhost only. To start the server, run (additional to pyCA)::

  ./start.sh ui

To production deployment, use a WSGI server instead. A very simple example,
using Gunicorn, would be to run::

  gunicorn pyca.ui:app

For more information, have a look at the help option of gunicorn or go to the
`Gunicorn online documentation`_.

In addition to the WSGI server, you should use a reverse proxy,
if you want the ui to listen to anything but `localhost`.
Some example configuration files for Nginx_ can be found under `reverse-proxy <reverse-proxy>`_.

JSON API
********

The pyCA web interface comes with a JSON API to programatically modify and
retrieve information about the capture agent. For more information, take a
look at the API documentation:

    `API Documentation <apidocs.rst>`_


Backup Mode
***********

By setting ``backup_mode = True`` in the configuration file, the PyCA will go
into a backup mode. This means that capture agent will neither register itself
at the Opencast core, nor try to ingest any of the recorded media or set the
capture state. This is useful if the CA shall be used as backup in case a
regular capture agent fails to record (for whatever reasons). Just match the
name of the pyCA to that of the regular capture agent.


Preview
*******

The web interface can show preview images for running capture processes. To
enable this, the capture process must generate these still images and write
them to a pre-defined location. An simple example configuration using FFmpeg
could look like this::

    command          = '''ffmpeg -nostats -re
                          -f lavfi -r 25 -i testsrc
                          -f lavfi -i sine
                          -t {{time}} -map 0:v -map 1:a {{dir}}/{{name}}.webm
                          -t {{time}} -map 0:v -r 1 -update 1 {{previewdir}}/preview.jpg'''

    preview = '{{previewdir}}/preview.jpg'

Of ourse, you can build more complex pipelines. For example, you could include
a volume meter like this::

    command          = '''ffmpeg -nostats -re
                          -f lavfi -r 25 -i testsrc
                          -f lavfi -i sine
                          -t {{time}} -map 0:v -map 1:a {{dir}}/{{name}}.webm
                          -t {{time}} -filter_complex '
                            [1:a] showvolume=w=640:p=0.8 [vol];
                            [0:v] scale=640:-2 [img];
                            [img][vol] overlay=0:0 [preview]'
                          -map '[preview]' -r 1 -update 1 {{previewdir}}/preview.jpg'''

    preview = '{{previewdir}}/preview.jpg'

This command will record audio and video from a test source and write a WebM
file while simultaneously updating a still image every second.

.. _Opencast: https://opencast.org
.. _GNU Lesser General Public License: https://raw.githubusercontent.com/opencast/pyCA/master/license.lgpl
.. _Raspberry Pi: https://raspberrypi.org
.. _Nginx: https://www.nginx.com
.. _AUR: https://aur.archlinux.org/packages/pyca
.. _Gunicorn online documentation: https://gunicorn.org
.. _Travis configuration: https://raw.githubusercontent.com/opencast/pyCA/master/.travis.yml
.. _FFmpeg: https://ffmpeg.org
