from pyparsing import (
    Group,
    Literal,
    OneOrMore,
    Optional,
    ParserElement,
    Word,
    printables,
)

from lab_validation.parsers.junos.grammar.utils import (
    as_path,
    origin_type,
    rib_meta_info,
)

from ...common.tokens import dec, ip, newline, prefix, uptime


def show_route() -> ParserElement:
    """Grammar for parsing output of 'show route tblae'"""
    return OneOrMore(
        Group(
            rib_meta_info() + OneOrMore(Group(_route_block())).setResultsName("routes")
        )
    )


def _route_block() -> ParserElement:
    return prefix.setResultsName("network") + _route_info_block().setResultsName("info")


def _route_info_block() -> ParserElement:
    return OneOrMore(Group(_status_route_info_block()))


def _status_route_info_block() -> ParserElement:
    return Optional(Literal("+") | Literal("-") | Literal("*")).setResultsName(
        "status"
    ) + (
        _direct_route_info_block()
        | _bgp_route_info_block()
        | _local_route_info_block()
        | _static_route_info_block()
        | _static_discard_route_info_block()
        | _isis_route_info_block()
        | _ospf_route_info_block()
    )


def _local_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Local").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + newline
        + "Local"
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )


def _direct_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Direct").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + newline
        + ">"
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )


def _static_discard_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Static").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + newline
        + "Discard"
        + newline
    )


def _static_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Static").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + newline
        + ">"
        + "to"
        + ip.setResultsName("nh_ip")
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )


def _isis_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("IS-IS").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + ","
        + "metric"
        + dec.setResultsName("metric")
        + newline
        + ">"
        + "to"
        + ip.setResultsName("nh_ip")
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )


def _bgp_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("BGP").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + ","
        + Optional("MED" + dec.setResultsName("metric") + ",")
        + "localpref"
        + dec.setResultsName("localpref")
        + newline
        + "AS path:"
        + as_path.setResultsName("as_path")
        + origin_type.setResultsName("origin_type")
        + ","
        + "validation-state:"
        + (Literal("unverified") | Literal("valid"))
        + newline
        + "> to"
        + ip.setResultsName("nh_ip")
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )


def _ospf_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("OSPF").setResultsName("protocol")
        + "/"
        + dec.setResultsName("admin")
        + "]"
        + uptime
        + ","
        + "metric"
        + dec.setResultsName("metric")
        + newline
        + ">"
        + "to"
        + ip.setResultsName("nh_ip")
        + "via"
        + Word(printables).setResultsName("nh_iface")
        + newline
    )
