User Interface
==============

PyCA comes with a web interface to check the status of capture agent and recordings.
It is built as WSGI application and can be run using many different WSGI servers
(Apache httpd + mod_wsgi, Gunicorn, …).

For testing, it comes with a minimal built-in server:

- It should not be used in production
- It will listen to localhost only

To start the test server, run (additional to pyCA)::

    % ./start.sh ui

For a production deployment, use a WSGI server instead.
For example, use Gunicorn by running::

    % gunicorn pyca.ui:app

For more information, have a look at the help option of gunicorn or go to the `Gunicorn online documentation`_.

.. _Gunicorn online documentation: https://gunicorn.org
