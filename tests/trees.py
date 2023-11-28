"""The parsed representations of yaml trees."""
from shv import RpcMethodFlags

from shvtree import (
    SHVMethod,
    SHVNode,
    SHVTree,
    SHVTypeBase,
    SHVTypeBitfield,
    SHVTypeConstant,
    SHVTypeEnum,
    SHVTypeIMap,
    SHVTypeMap,
    SHVTypeOneOf,
    SHVTypeTuple,
    shvAny,
    shvBool,
    shvDateTime,
    shvInt,
    shvNull,
    shvString,
    shvUInt,
)
from shvtree.namedset import NamedSet

_tree1_types_args_since_const_last = SHVTypeConstant("constStringLast", "last")
_tree1_types_args_since = SHVTypeOneOf(
    "getLogArgsSince", shvDateTime, shvNull, _tree1_types_args_since_const_last
)
_tree1_types_args_until = SHVTypeOneOf("getLogArgsUntil", shvDateTime, shvNull)
_tree1_types_propEnum = SHVTypeEnum(
    "propEnum", "boolean", "integer", "uinteger", "string", "dateTime"
)
tree1_types: NamedSet[SHVTypeBase] = NamedSet(
    _tree1_types_args_since,
    _tree1_types_args_since_const_last,
    _tree1_types_args_until,
    SHVTypeMap(
        "getLogArgs",
        since=_tree1_types_args_since,
        until=_tree1_types_args_until,
        withSnapshot=shvBool,
        withPathsDict=shvBool,
        recordCountLimit=shvInt,
    ),
    SHVTypeEnum("status", "ok", "warning", "error"),
    SHVTypeBitfield("errors", "outOfRange", "lowPower"),
    SHVTypeMap(
        "timeZone", offset=shvInt, dtoffset=shvInt, dtstart=shvInt, dtend=shvInt
    ),
    SHVTypeMap(
        "version",
        major=shvInt,
        minor=shvInt,
        fixup=shvInt,
        hash=shvString,
        dev=shvBool,
        dirty=shvBool,
    ),
    _tree1_types_propEnum,
    SHVTypeTuple(
        "propTuple",
        shvBool,
        shvInt,
        shvUInt,
        shvString,
        shvDateTime,
        enum=_tree1_types_propEnum,
    ),
    SHVTypeMap(
        "propMap",
        boolean=shvBool,
        integer=shvInt,
        uinteger=shvUInt,
        string=shvString,
        dateTime=shvDateTime,
    ),
    SHVTypeIMap(
        "propIMap",
        shvBool,
        shvInt,
        shvUInt,
        shvString,
        shvDateTime,
        enum=_tree1_types_propEnum,
    ),
)

shvtree1_nodes: NamedSet[SHVNode] = NamedSet(
    SHVNode(
        ".app",
        nodes=NamedSet(
            SHVNode(
                "shvjournal",
                methods=NamedSet(
                    SHVMethod(
                        "getLog",
                        flags=RpcMethodFlags.LARGE_RESULT_HINT,
                        param=tree1_types["getLogArgs"],
                        result=shvAny,
                    )
                ),
            )
        ),
    ),
    SHVNode.new_property(
        "serialNumber", shvInt, readonly=True, description="Serial number of the board"
    ),
    SHVNode.new_property("hwVersion", shvString, readonly=True),
    SHVNode.new_property(
        "status", tree1_types["status"], readonly=True, signal="fchng"
    ),
    SHVNode.new_property("errors", tree1_types["errors"]),
    SHVNode.new_property("utcTime", shvDateTime),
    SHVNode.new_property("localTime", shvDateTime, readonly=True),
    SHVNode.new_property("timeZone", tree1_types["timeZone"]),
    SHVNode.new_property("version", tree1_types["version"], readonly=True),
    SHVNode(
        "properties",
        nodes=NamedSet(
            SHVNode.new_property("boolean", shvBool),
            SHVNode.new_property("integer", shvInt),
            SHVNode.new_property("uinteger", shvUInt),
            SHVNode.new_property("string", shvString),
            SHVNode.new_property("dateTime", shvDateTime),
            SHVNode.new_property("tuple", tree1_types["propTuple"]),
            SHVNode.new_property("map", tree1_types["propMap"]),
            SHVNode.new_property("imap", tree1_types["propIMap"]),
        ),
        methods=NamedSet(SHVMethod("reset")),
    ),
    SHVNode.new_property("counter", shvInt, readonly=True, signal=True),
)

tree1 = SHVTree(types=tree1_types, nodes=shvtree1_nodes)


shvtree2_nodes: NamedSet[SHVNode] = NamedSet(
    SHVNode("one", nodes=NamedSet(SHVNode("subone"))),
    SHVNode("two"),
)

tree2 = SHVTree(nodes=shvtree2_nodes)
