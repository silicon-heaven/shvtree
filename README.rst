Silicon Heaven Tree
===================
.. image:: docs/_static/logo.svg
   :align: right
   :height: 128px
   :alt: SHVTree logo [*]_

This provides common parser and validator for Silicon Heaven tree
representation. It is formed of nodes forming path and methods associated with
those paths as defined in `Silicon Heaven RPC
<https://github.com/silicon-heaven/libshv/wiki/ChainPack-RPC#rpc>`__.

The SHV Tree simplifies and implements common operations such as `ls` and `dir`
methods and basic type description. The core of this project is definition of
format describing the tree but it also provides SHV device implementation based
on the provided tree.

* `📃 Sources <https://gitlab.com/silicon-heaven/shvtree>`__
* `⁉️ Issue tracker <https://gitlab.com/silicon-heaven/shvtree/-/issues>`__
* `📕 Documentation <https://silicon-heaven.gitlab.io/shvtree/>`__


Installation
------------

The installation can be done with package manager ``pip``.

.. code-block:: console

   $ pip install pyshvtree


Running tests
-------------

This project contains basic tests in directory ``tests``; see the dependencies
in the `pyproject.toml` file.

To run tests you have to use **pytest**. To run all tests just run it in the
top level directory of the project::

    pytest

See the `pytest documentation <https://docs.pytest.org/>`__ for more info.


Documentation
-------------

The documentation is available in ``docs`` directory. You can build it using::

    sphinx-build -b html docs docs-html


.. [*] Project logo is assembled from images by Freepik
