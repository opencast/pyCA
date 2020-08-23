Development Installation
========================

This guide describes how to run pyCA for testing and development.
This should work on any Linux system
But it might require some knowledge about your specific distribution.


Get the Code
------------

Clone the git repository::

    % git clone https://github.com/opencast/pyCA.git
    % cd pyCA


Python Dependencies
-------------------

When testing or developing pyCA, make sure to have the following components
installed on your system:

- Python ≥ 3.6
- Node.js and NPM
- git

PyCA also relies on some Python libraries with native C bindings.
To allow them to be installed via ``pip`` make sure
the base libraries are installed using a command like (Fedora, CentOS)::

    % dnf install gcc python3-devel libcurl-devel openssl-devel
    % export PYCURL_SSL_LIBRARY=openssl

or (Debian, Ubuntu)::

    % apt install git python3 python3-venv libcurl4-openssl-dev libssl-dev gcc python3-dev

Next, create and enable a virtual environment and install the Python dependencies::

    % python3 -m venv venv
    % . ./venv/bin/activate
    % pip install -r requirements.txt

Make sure to always enable your virtual environment before starting pyCA.


Instead of using a virtual environment, you might also be able to install all Python dependencies via package manager.
To check which packages need to be installed, take a look at the `requirements.txt <../../requirements.txt>`_.

For example, on Arch Linux, you could install the dependencies using::

    % pacman -S python-pycurl python-dateutil python-configobj python-sqlalchemy

JavaScript Dependencies
-----------------------

PyCA uses Vue.js for the web interface.
To install all necessary JavaScript libraries, run::

    % npm ci

This will allow you to build the JavaScript part of the web interface.


Configuration
-------------

The default configuration should usually work great for testing:

- PyCA connects to `develop.opencast.org <https://develop.opencast.org>`_
- It records a test signal using FFmpeg
- It generates a capture agent identifier based on your system's hostname
- It keeps recordings and the database in the current directory

If you want to modify the configuration (e.g. to use a different Opencast server)::

    % vim etc/pyca.conf


Starting pyCA
-------------

You can start pyCA by running::

    % ./start.sh

This start script will take an optional command allowing you to separately launch pyCA services and run them as separate processes.
By default (or using the ``run`` command) all services except the UI are launched as a single process.

This is not recommended for production since pyCA will not monitor services separately.
That means, if a single service fails, it might not be restarted automatically.

But for development or testing, this should not matter
and ``start.sh`` is a convenient way of building the JavaScript code and running pyCA.

To list all available CLI options, run::

    % ./start.sh -h
