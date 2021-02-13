Install PyCA via Container
==========================

PyCA containers will automatically be built for each release and commit.
This can be used to easily deploy pyCA e.g. for capturing network streams.
The containers can be found at `quay.io/repository/opencast/pyca <https://quay.io/repository/opencast/pyca>`_.


Compose Files
-------------

Compose files to easily run pyCA containers can be found in ``init/container/``.
For a simple example, run::

    cp etc/pyca.conf init/container/pyca.conf
    sed -i "s|#name .*|name = pyca-container|g" init/container/pyca.conf
    docker-compose -f init/container/docker-compose.sqlite.yml up

More details can be found in the `container readme file <../../init/container/README.rst>`_.
