PyCA – Opencast Capture Agent
=============================

.. image:: https://travis-ci.org/opencast/pyCA.svg?branch=master
    :target: https://travis-ci.org/opencast/pyCA

**PyCA** is a fully functional Opencast [OC]_ capture agent written in Python.
It is free software licenced under the terms of the GNU Lesser General Public
License [LGPL]_.

The goals of pyCA are to be…

 - flexible for any kind of capture device
 - simplistic and minimalistic in code and functionality
 - unrestrictive in terms of choosing capture software

PyCA can be run on almost any kind of devices: A regular PC equipped with
capture cards, a server to capture network streams, small boards or embedded
devices like Raspberry Pi [RPi]_, Beagleboard, Cubieboard, …

Backup Mode
***********

By setting ``backup_mode = True`` in the configuration file, the PyCA will go
into a backup mode. This means that capture agent will neither register itself
at the Opencast core, nor try to ingest any of the recorded media or set the
capture state. This is useful if the CA shall be used as backup in case a
regular capture agent fails to record (for whatever reasons). Just match the
name of the pyCA to that of the regular capture agent.

Installation
************

Here is a short summary for Debian based OS like Raspian::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  apt-get install python-configobj python-dateutil python-pycurl \
    python-flask python-sqlalchemy
  vim etc/pyca.conf <-- Edit the configuration
  ./start.sh

On Fedora::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  dnf install python-pycurl python-dateutil python-configobj \
    python-flask python-sqlalchemy
  vim etc/pyca.conf <-- Edit the configuration
  ./start.sh

On RHEL/CentOS 7::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  yum install python-pycurl python-dateutil python-configobj \
    python-flask python-sqlalchemy
  vim etc/pyca.conf  <-- Edit the configuration
  ./start.sh

On Arch Linux::

  git clone https://github.com/opencast/pyCA.git
  cd pyCA
  sudo pacman -S python-pycurl python-dateutil \
    python-configobj python-sqlalchemy
  vim etc/pyca.conf  <-- Edit the configuration
  ./start.sh

…or use the available [AUR]_ package. Note that Arch Linux uses Python 3.5
by default, so this method will use Python 3.5 for pyCA as well.

.. [OC] http://opencast.org/
.. [LGPL] https://raw.githubusercontent.com/lkiesow/pyCA/master/license.lgpl
.. [RPi] http://www.raspberrypi.org/
.. [AUR] https://aur.archlinux.org/packages/pyca
