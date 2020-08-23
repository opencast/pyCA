Install PyCA on Debian-based System
===================================

This installation guide describes how to install pyCA on:

- Debian
- Ubuntu
- Raspberry Pi OS


Install PyCA
------------

For Debian based systems, we can use pre-built packages for installing pyCA.

First, enable the repository and make sure that HTTPS connections can be used by executing:

.. code-block:: bash

    % apt install apt-transport-https
    % apt-key adv --fetch https://pyca.deb.opencast.org/gpg.key
    % echo "deb [arch=all] https://pyca.deb.opencast.org/opencast-pyca buster main" > \
        /etc/apt/sources.list.d/opencast-pyca.list

After adding the repository, we can install pyCA via package manager:

.. code-block:: bash

    % apt update
    % apt install opencast-pyca

By default, pyCA is disabled.
The default configuration allows you to run pyCA against the official Opencast test server.
If you do not want you installation to show up on the test server take a look at the sections `Configuration`_ first.
If you do not mind, continue.

To start pyCA and make sure it is automatically started after a reboot, run::

    % systemctl start pyca-agentstate.service pyca-capture.service pyca-ingest.service pyca-schedule.service pyca-ui.service pyca.service
    % systemctl enable pyca-agentstate.service pyca-capture.service pyca-ingest.service pyca-schedule.service pyca-ui.service pyca.service

That's it. We already have pyCA up and running.
You can test if it's up by querying the status of the Systemd units which will list several services::

    % systemctl status 'pyca*'
    ● pyca-agentstate.service - Python Capture Agent agentstate service
       Loaded: loaded (/lib/systemd/system/pyca-agentstate.service; enabled; vendor preset: enabled)
       Active: active (running)
       ...


Configuration
-------------

By default, pyCA will connect to `develop.opencast.org <https://develop.opencast.org>`_ and record using an FFmpeg test command.
You can adjust these settings by editing ``/etc/pyca/pyca.conf``.

You probably want to adjust at least the following settings:

.. code-block:: ini

    [agent]
    name      = 'pyca'

    [capture]
    command   = 'ffmpeg -nostats -re -f lavfi -r 25 -i testsrc -f lavfi -i sine -t {{time}} {{dir}}/{{name}}.webm'

    [server]
    url       = 'https://develop.opencast.org'
    username  = 'opencast_system_account'
    password  = 'CHANGE_ME'

    [ui]
    username  = 'admin'
    password  = 'opencast'

All configuration keys are documented in the configuration file itself.


Install Nginx
-------------

The pyCA user interface is enabled by default but is only available from localhost.
You can test this by querying the webserver from the command line::

    % curl http://127.0.0.1:8000
    pyCA

But trying to access this interface from another dervice will fail.
To allow external access, it's recommended to set up Nginx.

For this, first, install Nginx by  running::

    % apt install nginx

Then, edit the configuration in ``/etc/nginx/sites-enabled/default`` and set it to::


    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        location / {
            proxy_pass http://127.0.0.1:8000;
        }
    }

Finally, reload the Nginx service::

    % systemctl reload nginx.service

The user interface should now be available when you try to access your system from an external device via HTTP on port 80.
If the connection still fails, make sure no `Firewall`_ is blocking HTTP.


HTTPS
~~~~~

Regardless of the set-up, it is highly recommended to configure HTTPS and redirect all HTTP traffic immediately.
PyCA uses authentication which would otherwise be sent over the network as plain text.

Configuring HTTPS in Nginx is only marginally more complex than plain HTTP.
For that, obtain a valid TLS certificate (e.g. use `Let's Encrypt <https://letsencrypt.org>`_)
and modify the configuration above to look like this::

    server {
        listen 80;
        listen [::]:80;
        server_name _;

        # Enforce HTTPS by redirecting requests
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen      443 ssl http2;
        listen [::]:443 ssl http2;
        server_name _;

        # Path to the TLS certificate and private key.
        ssl_certificate_key /path/to/example.opencast.org.key;
        ssl_certificate     /path/to/example.opencast.org.crt;

        location / {
            proxy_pass http://127.0.0.1:8000;
        }
    }

This will immediately redirect all traffic to HTTPS to ensure all your data is
encrypted.


Firewall
--------

If you configured a firewall, and want to use the web interface,
make sure to allow inbound HTTP and HTTPS connectios:

- Port 80 (HTTP)
- Port 443 (HTTPS)


UFW
~~~

A popular choice for a firewall is UFW.
Run the follwing commands to allow HTTP and HTTPS::

    % ufw allow http
    % ufw allow https
