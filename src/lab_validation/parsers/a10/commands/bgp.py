import re
from typing import List, Sequence, Text

from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    ParseResults,
    SkipTo,
    White,
    Word,
    ZeroOrMore,
    printables,
    stringEnd,
)

from ...common.exceptions import UnrecognizedLinesError
from ...common.tokens import dec, ip, prefix, printables_and_space, to_eol
from ..models.bgp import A10BgpRoute

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


def parse_show_ip_bgp(text: Text) -> List[A10BgpRoute]:
    """Parses the output of `show ip bgp`."""
    if not text.strip():
        return []
    parsed = show_ip_bgp().parseString(text)
    routes: List[A10BgpRoute] = []
    for r in parsed["v4_routes"]:
        routes.append(_deserialize_route(r))
    if _IPv4_PATTERN.search(parsed.padding):
        # An IP address appears in the padding, likely indicating a parsing problem
        raise UnrecognizedLinesError(
            "Unexpected IP address in what is being parsed as padding: "
            + parsed.padding
        )
    return routes


def _filter_empty(as_path_list: Sequence[Text]) -> List[Text]:
    return list(filter(lambda x: (False if x == " " else True), as_path_list))


def _deserialize_route(r: ParseResults) -> A10BgpRoute:
    """Deserializes one parsed route."""
    as_path_str = _filter_empty(r.get("as_path", ""))
    as_path = tuple(map(int, as_path_str))
    type_str: Text = str(r.get("type")).strip()
    rtype = type_str if type_str in _types else None
    return A10BgpRoute(
        valid=bool("valid" in r),
        best=bool("best" in r),
        network=r.network,
        next_hop_ip=r.get("nh_ip"),
        metric=r.get("metric"),
        local_preference=r.get("lp", None),
        weight=r.get("weight"),
        type=rtype,
        as_path=as_path,
        origin_type=r.get("origin"),
    )


def show_ip_bgp() -> ParserElement:
    """Grammar for parsing output of 'show ip bgp'"""
    return _header() + _routes_block() + SkipTo(stringEnd).setResultsName("padding")


def _header() -> ParserElement:
    return (
        Group(
            Literal("BGP Address Family IPv4 Unicast") + SkipTo(" Path") + to_eol + "\n"
        )
        .leaveWhitespace()
        .setResultsName("skipped")
    )


def _routes_block() -> ParserElement:
    return OneOrMore(_ip_v4_route_line()).setResultsName("v4_routes")


_origin_codes = [
    "i",  # IGP
    "?",  # incomplete
    "e",  # EGP
]

_types = {
    "VIP FLAGG",  # VIP flagged
    "VIP",  # VIP unflagged
    "NAT",  # NAT pool subnet
    "FLOATING",  # floating-ip
}


def _ip_v4_route_line() -> ParserElement:
    """Parses a single route on a single line."""
    return Group(
        Optional("*").setResultsName("valid")
        + Optional(">").setResultsName("best")
        + White(" ", min=1, max=3)
        + prefix.setResultsName("network")
        + White(" \n", min=1, max=21)
        + ip.setResultsName("nh_ip")
        + White(" ", min=1, max=19)
        + dec.setResultsName("metric")
        + White(" ", min=1, max=8)
        + Optional(dec.setResultsName("lp"))
        + White(" ", min=1, max=8)
        + dec.setResultsName("weight")
        + printables_and_space(10).setResultsName("type")
        + ZeroOrMore(dec + White(" ")).setResultsName("as_path")
        + MatchFirst([Literal(code) for code in _origin_codes]).setResultsName("origin")
        + to_eol
        + "\n"
    ).leaveWhitespace()
