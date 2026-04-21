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
            rib_meta_info()
            + OneOrMore(Group(_route_block())).set_results_name("routes")
        )
    )


def _route_block() -> ParserElement:
    return prefix.set_results_name("network") + _route_info_block().set_results_name(
        "info"
    )


def _route_info_block() -> ParserElement:
    return OneOrMore(Group(_status_route_info_block()))


def _status_route_info_block() -> ParserElement:
    return Optional(Literal("+") | Literal("-") | Literal("*")).set_results_name(
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
        + Literal("Local").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + newline
        + "Local"
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )


def _direct_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Direct").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + newline
        + ">"
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )


def _static_discard_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Static").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + newline
        + "Discard"
        + newline
    )


def _static_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("Static").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + newline
        + ">"
        + "to"
        + ip.set_results_name("nh_ip")
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )


def _isis_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("IS-IS").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + ","
        + "metric"
        + dec.set_results_name("metric")
        + newline
        + ">"
        + "to"
        + ip.set_results_name("nh_ip")
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )


def _bgp_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("BGP").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + ","
        + Optional("MED" + dec.set_results_name("metric") + ",")
        + "localpref"
        + dec.set_results_name("localpref")
        + newline
        + "AS path:"
        + as_path.set_results_name("as_path")
        + origin_type.set_results_name("origin_type")
        + ","
        + "validation-state:"
        + (Literal("unverified") | Literal("valid"))
        + newline
        + "> to"
        + ip.set_results_name("nh_ip")
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )


def _ospf_route_info_block() -> ParserElement:
    return (
        "["
        + Literal("OSPF").set_results_name("protocol")
        + "/"
        + dec.set_results_name("admin")
        + "]"
        + uptime
        + ","
        + "metric"
        + dec.set_results_name("metric")
        + newline
        + ">"
        + "to"
        + ip.set_results_name("nh_ip")
        + "via"
        + Word(printables).set_results_name("nh_iface")
        + newline
    )
