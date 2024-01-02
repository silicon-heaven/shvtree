SHV Tree format description
===========================

The format tree is intended to be written is YAML but it is not essential
requirement. JSON and other such formats can be used as well.

The tree is in core split to custom types (key ``types``) and tree (key
``nodes``) itself. Types are defined separately to allow easy reuse and also to
have less cluttered tree representation.


Tree description
----------------

The tree is formed by nodes where every node can have multiple children. This
forms tree. The description language as defined here does not support multiple
direct parents for a node. In other words one node can have only one direct
parent. This is done for tree clarity and it is highly suggested to not design
SHV tree in such a way some nodes are accessible with different paths.

The tree starts with top level node that is implied and can't be modified. You
need to define its children in the ``nodes`` field.

Nodes
`````

Nodes are defined either in top level ``nodes`` mapping or in any lower one.
The name of the method is given by key in that mapping and needs to be unique
between its siblings (which is given by limitations of mapping anyway).

The supported values describing a node are:

nodes
  Children nodes. That is mapping of node name to the node description.

methods
  Methods associated with this node. That is mapping of the method name to the
  method description. For the method description see the next section.

property
  Sets this node to serve as property. The value needs to be a valid data type.
  The property is node that implements at minimum ``get`` method with optional
  addition of ``set`` and/or ``chng``. These methods can't be listed in
  ``methods`` when ``property`` is used.

readonly
  Makes property read only if set to ``true``. The default is ``false``. This is
  valid only when ``property`` is also used. This controls if ``set`` method
  should exist.

signal
  Makes property change signaled with signal ``chng`` when set to ``true``. The
  default depends on ``readonly``, when ``readonly`` is ``true`` then default is
  ``false`` otherwise ``true``. That is because it is more common that read only
  property are not signaled. This is valid only when ``property`` is also used.
  Instead of boolean you can also use string which is then used as signal's
  name. That is allowed to support different signals over ``chng``.

description
  The brief description of the node.


Methods
```````

Methods have to be associated with some node in the tree and thus defined in
``methods`` field of that node.

The supported values describing a method are:

param
  Data type that is expected to be passed to the method when called. The default
  one, if not specified, is ``shvNull`` which is in SHV alias for no arguments.
result
  Data type that is expected to be returned by this method when called. The
  default, if not specified, is ``shvNull``.
access
  Specifies the minimal access level required to trigger method. Levels are in
  ascending order: ``bws``, ``rd``, ``wr``, ``cmd``, ``cfg``, ``srv``, ``ssrv``,
  ``dev`` and ``su``. The more detailed description of access levels can be
  found in `pySHV documentation
  <https://elektroline-predator.gitlab.io/pyshv/master/concepts.html#access-control>`__.
flags
  Optional list of flags. The supported flags are: ``signal``, ``getter``,
  ``setter``, and ``large_result_hint``.
description
  The brief description of the method.



Types
-----

Methods in tree declare data type for their parameters and return. This is done
for type validation and tools implementing SHV tree can thanks to that simplify
parsing and validation to users a lot.

There are three sources of types. One set comes directly from SHV and are core
types. Then there are some builtin types known in SHV tree that are not core
types. The last group are custom types defined in for a specific tree.

Core SHV types
``````````````

These are absolute basic types that all other types are converted to. They come
from SHV itself but due to our naming convention they might be interpreted also
as some special case of custom types. In reality all SHV tree types are just
less restrictive than these are.

* ``Bool`` is boolean value (only true and false are valid values)
* ``Int`` can be used for any integer number
* ``UInt`` can be used for any unsigned integer number
* ``Double`` can be used for floating point number (with double precision)
* ``Decimal`` is number in form :math:`mantisa*10^{exponent}` where both mantisa
  and exponent are integer numbers.
* ``String`` is string of any length.
* ``Blob`` is binary blob of any length.
* ``DateTime`` is date and time including the timezone offset.
* ``List`` a list of any vales of any length.
* ``Null`` is most often used as no value and thus it makes more sense to just
  not specify field at all rather than saying that it has ``Null`` type. It is
  available for some edge cases nonetheless.
* ``Any`` stands for any valid SHV value and can be used when just anything
  goes.


SHV tree built in types
```````````````````````

There are some types that are such a common modification of the types that it
makes sense to define them or because they are core part of the SHV device
design. These types are some modification on core types.

* ``Int8`` is integer number with at most 8 bits.
* ``Int16`` is integer number with at most 16 bits.
* ``Int32`` is integer number with at most 32 bits.
* ``Int64`` is integer number with at most 64 bits.
* ``UInt8`` is unsigned integer number with at most 8 bits.
* ``UInt16`` is unsigned integer number with at most 16 bits.
* ``UInt32`` is unsigned integer number with at most 32 bits.
* ``UInt64`` is unsigned integer number with at most 64 bits.

Custom types
````````````

New custom types can be defined in the top level section ``types``. Every type
needs its own unique name to be identified. The redefinition of core and built
in types is not allowed. The type description and limitations are inspired by
JSON Schema.

You can create alias by simply referring to some other type in the ``types``
mapping value (for example ``small: Int8``).

It is also possible to define type that matches more than one other type
(without matching all types). This is done by defining it as list in ``types``
mapping value (for example ``small: [Int8, UInt8]``).

Other custom types are described by mapping where the most important and in most
cases only mandatory field is ``type``. It can be one of the followings:

Int
  This allows you to define integer number with custom limitations. The
  supported additional fields are:

  * ``minimum`` specifies lower boundary to the integer value.
  * ``maximum`` specifies upper boundary to the integer value.
  * ``multipleOf`` that can be used when integer needs to be multiple of some
    specific number (commonly used for ``2`` for powers of two).
  * ``unsigned`` is expected to be boolean that specifies if new type should be
    interpreted as SHV's signed or unsigned integer type. The default behavior,
    if not specifies, is to inspect ``minimum`` and use ``false`` for negative
    value and ``true`` otherwise.

Double
  This allows you to define limitations to the floating point number. The
  supported additional fields are:

  * ``minimum`` specifies lower boundary to the numeric value.
  * ``exclusiveMinimum`` specifies exclusive lower boundary to the numeric
    value.
  * ``maximum`` specifies upper boundary to the numeric value.
  * ``exclusiveMaximum`` specifies exclusive upper boundary to the numeric
    value.
  * ``multipleOf`` that can be used when integer needs to be multiple of some
    specific number.

Decimal
  The decimal number with additional limitations. The supported additional
  fields are:

  * ``minimum`` specifies lower boundary to the number.
  * ``maximum`` specifies upper boundary to the number.

String
  String with limitations. The supported additional fields are:

  * ``minLength`` specifies minimal number of characters.
  * ``maxLength`` specifies maximal number of characters.
  * ``pattern`` is regular expression the string must match. Note that SHV tree
    does not inspect pattern and thus even if it limits length such string type
    won't be considered bounded.

Blob
  Binary blob with limitations. The supported additional fields are:

  * ``minLength`` specifies minimal number of bytes.
  * ``maxLength`` specifies maximal number of bytes.
  * ``length`` is convenient alias for both ``minLength`` and ``maxLength``.

Enum
  The special integer type with defined allowed values. The only additional
  supported field is ``values``. The value of the fields needs to be list of
  allowed values. The integer representations are assigned from zero upward. You
  can also specify custom value by using mapping (``foo: 42``). This type is
  commonly used in combination with other types to provide name aliases to the
  integers.

Bitfield
  This type same as ``Enum`` in its definition. The difference is only in
  ``values`` meaning. The unsigned integers assigned to values are here bit
  indexes.

List
  Allows you to define list that can contain only some of the types instead of
  ``Any``. The supported fields are:

  * ``allowed`` this is list of allowed types that can be included in the list.
  * ``minlen`` minimal length of the list (the default is 0)
  * ``maxlen`` maximal length of the list (the default is unlimited)

Tuple
  This is list with fixed length and fields. The supported additional fields
  are:

  * ``fields`` which is list of types. Ordering in the list is kept and is order
    in the tuple.
  * ``enum`` allows you to reference enum type which assigns name aliases to the
    field indexes. This is handy not only for documentation purposes but also
    for code generation.

Map
  Key-value mapping where key is string. Value-key pair can be left out but only
  existing keys need to be used to match specified type. The supported
  additional fields are:

  * ``fields`` which is mapping of name of the field to the value data type.

IMap
  Key-value mapping where key is integer. Value-key pair can be left out but
  only existing keys need to be used to match this specified type. The supported
  additional fields are:

  * ``fields`` which is the same mapping as for ``Map``
  * ``enum`` that assigns integer to aliases specified in ``fields``. The
    provided enum type needs to map all aliases to some integer, thus this field
    is need to be always specified.



Example tree
------------

.. literalinclude:: ../tests/tree1.yaml
   :language: yaml


Validating the tree
-------------------

There are some cases when you can write valid SHV tree that is not
