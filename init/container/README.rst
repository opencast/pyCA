PyCA Container Images
=====================

This directory contains example docker-compose files for various scenarios.

PyCA + SQLite
-------------

.. code-block:: bash

    cp etc/pyca.conf init/container/pyca.conf
    sed -i "s|#name .*|name = pyca-container|g" init/container/pyca.conf
    docker-compose -f init/container/docker-compose.sqlite.yml up

PyCA + PostgreSQL
-------------

.. code-block:: bash

    cp etc/pyca.conf init/container/pyca.conf
    sed -i "s|#name .*|name = pyca-container|g" init/container/pyca.conf
    sed -i "s|#database .*|database = postgresql://pyca:pyca@database/pyca|g" init/container/pyca.conf
    docker-compose -f init/container/docker-compose.postgres.yml up
