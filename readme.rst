PyCA – Matterhorn Capture Agent
===============================

.. image:: https://travis-ci.org/lkiesow/pyCA.svg?branch=master
    :target: https://travis-ci.org/lkiesow/pyCA

**PyCA** is a fully functional Opencast Matterhorn [MH]_ capture agent written
in Python. It is free software licenced under the terms of the GNU Lesser
General Public License [LGPL]_.

The goals of pyCA are to be…

 - flexible for any kind of capture device
 - simplistic and minimalistic in code and functionality
 - unrestrictive in terms of choosing capture software

PyCA can be run on almost any kind of devices: A regular PC equipped with
capture cards, a server to capture network streams, small boards or embedded
devices like Raspberry Pi [RPi]_, Beagleboard, Cubieboard, …

Backup Mode
***********

By setting ``backup_mode = False`` in the configuration file, the PyCA will go
into a backup mode. This means that capture agent will neither register itself
at the matterhorn core, nor try to ingest any of the recorded media or set the
capture state. This is useful if the CA shall be used as backup in case a
regular capture agent fails to record (for whatever reasons). Just match the
name of the pyCA to that of the regular capture agent.

Installation
************

Here is a short summary for Debian based OS like Raspian::

  git clone https://github.com/lkiesow/pyCA.git
  cd pyCA
  sudo apt-get install python-virtualenv python-dev libcurl4-gnutls-dev gnutls-dev
  virtualenv venv
  . ./venv/bin/activate
  pip install icalendar python-dateutil pycurl configobj
  vim etc/pyca.conf  <-- Edit the configuration
  ./start.sh

For RedHat bases systems like Fedora it's almost the same::

  git clone https://github.com/lkiesow/pyCA.git
  cd pyCA
  sudo yum install python-virtualenv
  virtualenv venv
  . ./venv/bin/activate
  pip install icalendar python-dateutil pycurl configobj
  vim etc/pyca.conf  <-- Edit the configuration
  ./start.sh


.. [MH] http://opencast.org/matterhorn
.. [LGPL] https://raw.githubusercontent.com/lkiesow/pyCA/master/license.lgpl
.. [RPi] http://www.raspberrypi.org/
