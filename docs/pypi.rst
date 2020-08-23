Upload to PyPI_
===============

The ``Makefile`` includes a ``pypi`` target which builds a clean PyCA package.

So you can simply call

.. code-block:: bash

    % make pypi

to build a clean package.

The built package should be found under ``dist`` and can be uploaded to PyPI_, e.g. with Twine_.

For a more detailed explanation about the whole process, take e.g. a look at `Packaging Python Projects`_

.. _PyPI: https://pypi.org
.. _Twine: https://pypi.org/project/twine/
.. _Packaging Python Projects: https://packaging.python.org/tutorials/packaging-projects/
