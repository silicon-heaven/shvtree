SHV Tree device
===============

The primary usage for SHV Tree is to describe nodes and its methods of device.
The description is handy but the primary advantage is when it is combined with
:class:`shvtree.device.SHVTreeDevice`. With it you need to provide only
implementations of methods.

The device is foremost a extension of :class:`shv.SimpleClient`. It implements
``ls`` and ``dir`` methods (:meth:`shv.SimpleClient._ls` and
:meth:`shv.SimpleClient._dir` respectively) based on the SHV Tree.

The primary use case for :class:`shvtree.device.SHVTreeDevice` is as a parent
for your own device implementation.


Device's SHV Tree
-----------------

Tree can be specified either at class definition or later down the line. The
tree needs to be instance of :class:`shvtree.SHVTree` and set in attribute
:attr:`shvtree.device.SHVTreeDevice.tree`.

.. code::

   class MyDevice(shvtree.device.SHVTreeDevice):
       tree = shvtree.load(pathlib.Path(__file__).parent / "tree.yaml")

The advantage of setting it immediately at child class declaration has advantage
that there is no time between device creation (that commonly includes connection
to the SHV Broker) and tree assignment. The disadvantage is that you need to
load tree as part of your module load up. In most cases this is preferred way.

.. code::

   dev = await MyDevice.connect(url)
   dev.tree = shvtree.load(pathlib.Path(__file__).parent / "tree.yaml")

The alternative is to just set tree down the line. The advantage is that you can
set a different tree per instance this way. At the same time there is time
between connection to the broker and tree assignment and thus is discouraged.


Implementing methods
--------------------

Every method you define in SHV Tree can and should be implemented in your device
class implementation. This is done by implementing Python method of a specific
name. This name is derived from location of node in the tree and from method
name. The algorithm that deduces takes SHV path and method name, joins them by
``_`` and prefixes one additional ``_``. Such name is then sanitized to be valid
Python name and any invalid characters are replaced by ``_``. The example is
more than thousand words and thus method associated with node on path
``foo/.app/log`` that is called ``getLog`` would be implemented in method
``_foo__app_log_getLog``.

Method implementation can have from zero to all of these parameters:

* ``path`` (:class:`str`) is a full SHV path to the node method is associated
  with.
* ``node_name`` (:class:`str`) is name of the node method is associated with.
* ``node`` (:class:`shvtree.SHVNode`) is SHV Tree node this method is associated
  with.
* ``method_name`` (:class:`str`) is name of the method.
* ``method_path`` (:class:`str`) is full path to the node with method name
  appended after ``:`` (``foo/.app/log:getLog``). This most handy for logging
  purposes.
* ``method`` (:class:`shvtree.SHVMethod`) is SHV Tree method representation.
* ``access_level`` (:class:`shv.RpcMethodAccess`) is maximal access level of the
  user that sent request to call this method. Note that you do not have to check
  method access level because that is already done before method implementation
  call. The access level is provided for information or if you implement method
  that allows some argument combinations only to some access levels (although
  this is discouraged and two method should defined instead for this purpose).
* ``param`` (:data:`shv.SHVType`) are parameters passed to the method by
  caller.
* ``signals`` (:class:`shvtree.device.SHVTreeDevice.Signals`) is class that
  allows simple access to the signals of the node associated with this method.
  You only need to know signal method name (that is commonly ``chng``) and call
  it: ``await signals.chng(param)``.

Method implementations are not required to accept all these methods as Python's
inspect is used to call it only with parameters it expects.

Method implementation needs to return valid :data:`shvSHVType`.

The full typed definition:

.. code::

   def _foo_some(
       self,
       path: str,
       node_name: str,
       node: shvtree.SHVNode,
       method_name: str,
       method_path: str,
       method: shvtree.SHVTree,
       access_level: shv.RpcMethodAccess,
       param: shv.SHVType,
       signals: shvtree.device.SHVTreeDevice.Signals,
   ) -> shv.SHVType:


The method calling can be modified through some of the protected methods that
are documented in :class:`shvtree.device.SHVTreeDevice`. You might want to
inspect :meth:`shvtree.device.SHVTreeDevice._get_method_impl` and
:meth:`shvtree.device.SHVTreeDevice._method_name` if you want to change where
and how method implementations are searched for. The additional checks before
and after method can be implemented in
:meth:`shvtree.device.SHVTreeDevice._pre_call` and
:meth:`shvtree.device.SHVTreeDevice._post_call`.
