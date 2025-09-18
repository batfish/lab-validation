import re
from typing import List, Text

from pyparsing import (
    Combine,
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    ParseResults,
    SkipTo,
    Word,
    ZeroOrMore,
    printables,
    stringEnd,
)

from ...common.exceptions import UnrecognizedLinesError
from ...common.tokens import dec, ip, prefix, to_eol
from ..models.routes import A10MainRibRoute

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


def parse_show_ip_route_acos(text: Text) -> List[A10MainRibRoute]:
    """Parses the output of `show ip route acos`."""
    parsed = show_ip_route_acos().parseString(text)
    routes: List[A10MainRibRoute] = []
    if "v4_routes" in parsed:
        for r in parsed["v4_routes"]:
            routes.append(_deserialize_show_ip_route_acos_route(r))
    if _IPv4_PATTERN.search(parsed.padding):
        # An IP address appears in the padding, likely indicating a parsing problem
        raise UnrecognizedLinesError(
            "Unexpected IP address in what is being parsed as padding: "
            + parsed.padding
        )
    return routes


def _deserialize_show_ip_route_acos_route(r: ParseResults) -> A10MainRibRoute:
    """Deserializes one parsed route."""
    return A10MainRibRoute(
        network=r.network,
        protocol=r.protocol,
        next_hop_ip=None,
        next_hop_int=None,
        admin=0,
        metric=0,
    )


def parse_show_ip_route_all(text: Text) -> List[A10MainRibRoute]:
    """Parses the output of `show ip route all`."""
    parsed = show_ip_route_all().parseString(text)
    routes: List[A10MainRibRoute] = []
    for r in parsed["v4_routes"]:
        routes.append(_deserialize_show_ip_route_all_route(r))
    if _IPv4_PATTERN.search(parsed.padding):
        # An IP address appears in the padding, likely indicating a parsing problem
        raise UnrecognizedLinesError(
            "Unexpected IP address in what is being parsed as padding: "
            + parsed.padding
        )
    return routes


def parse_one_show_ip_route_all_route(text: Text) -> A10MainRibRoute:
    """Parses one route line of show ip route all, for testing."""
    parsed = _show_ip_route_all_ip_v4_route_line().parseString(text)
    return _deserialize_show_ip_route_all_route(parsed)


def _deserialize_show_ip_route_all_route(r: ParseResults) -> A10MainRibRoute:
    """Deserializes one parsed route."""
    return A10MainRibRoute(
        network=r.network,
        protocol=r.protocol,
        next_hop_ip=r.get("nh_ip"),
        next_hop_int=r["nh_iface"],
        admin=r.get("admin", 0),
        metric=r.get("metric", 0),
    )


_time_hours = dec + ":" + dec + ":" + dec
_time_days = dec + "d" + dec + "h" + dec + "m"
_time_weeks = dec + "w" + dec + "d" + dec + "h"
_time = MatchFirst([_time_hours, _time_days, _time_weeks])


def show_ip_route_acos() -> ParserElement:
    """Grammar for parsing output of 'show ip route acos'"""
    return (
        _show_route_acos_codes()
        + _show_route_acos_routes_block()
        + SkipTo(stringEnd).setResultsName("padding")
    )


def _show_route_acos_codes() -> ParserElement:
    return Group(Literal("Codes:") + SkipTo("NAT Map") + to_eol).setResultsName(
        "skipped"
    )


def _show_route_acos_routes_block() -> ParserElement:
    return ZeroOrMore(_show_ip_route_acos_ip_v4_route_line()).setResultsName(
        "v4_routes"
    )


_show_route_acos_protocol_codes = [
    "VF",  # VIP Flagged
    "V",  # VIP,
    "NR",  # IP NAT Range List
    "N",  # IP NAT
    "F",  # Floating IP
    "SN",  # Static NAT
    "N64",  # NAT64
    "LW",  # LW4o6
    "NM",  # NAT Map
]


def _show_ip_route_acos_ip_v4_route_line() -> ParserElement:
    """Parses a single route on a single line."""
    return Group(
        MatchFirst(
            [Literal(code) for code in _show_route_acos_protocol_codes]
        ).setResultsName("protocol")
        + prefix.setResultsName("network")
    )


def show_ip_route_all() -> ParserElement:
    """Grammar for parsing output of 'show ip route all'"""
    return (
        _show_ip_route_all_codes()
        + _show_ip_route_all_routes_block()
        + SkipTo(stringEnd).setResultsName("padding")
    )


def _show_ip_route_all_codes() -> ParserElement:
    return Group(
        Literal("Codes:") + SkipTo("Gateway of last resort is") + to_eol
    ).setResultsName("skipped")


def _show_ip_route_all_routes_block() -> ParserElement:
    return OneOrMore(_show_ip_route_all_ip_v4_route_line()).setResultsName("v4_routes")


_show_route_all_protocol_codes = [
    "K",  # kernel,
    "C",  # connected
    "S",  # static
    "R",  # RIP
    "B",  # BGP
    "O",  # OSPF
    "IA",  # OSPF inter area
    "N1",  # OSPF NSSA external type 1,
    "N2",  # OSPF NSSA external type 2
    "E1",  # OSPF external type 1
    "E2",  # OSPF external type 2
    "i",  # IS-IS
    "L1",  # IS-IS level-1
    "L2",  # IS-IS level-2
    "ia",  # IS-IS inter area
]


def _interface_name() -> ParserElement:
    """Parses an A10 interface name like trunk 1 or ve 55."""
    return Combine(Word(printables) + Literal(" ").suppress() + dec)


def _show_ip_route_all_ip_v4_route_line() -> ParserElement:
    """Parses a single route on a single line."""
    return Group(
        MatchFirst(
            [Literal(code) for code in _show_route_all_protocol_codes]
        ).setResultsName("protocol")
        + Optional("*").setResultsName("candidate_default")
        + prefix.setResultsName("network")
        + MatchFirst([_directly_connected(), _admin_via_nhip()])
        + _interface_name().setResultsName("nh_iface")
        + Literal(",").suppress()
        + _time.setResultsName("time")
    )


def _directly_connected() -> ParserElement:
    """For connected routes, there is no admin, metric, or next-hop IP."""
    return Literal("is directly connected,").suppress()


def _admin_via_nhip() -> ParserElement:
    """Expect admin, metric, and next-hop IP."""
    return (
        "["
        + dec.setResultsName("admin")
        + "/"
        + dec.setResultsName("metric")
        + "]"
        + "via"
        + ip.setResultsName("nh_ip")
        + ","
    )
