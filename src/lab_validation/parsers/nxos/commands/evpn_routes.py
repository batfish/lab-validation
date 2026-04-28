import re
from collections.abc import Sequence

from pyparsing import (
    Combine,
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    Regex,
    SkipTo,
    White,
    ZeroOrMore,
    one_of,
)

from lab_validation.parsers.common.tokens import dec, ip, newline
from lab_validation.parsers.nxos.models.routes import NxosEvpnRoute

_EVPN_NETWORK = Regex(r"\[[0-9]\]:\[[^\]]*\](?::\[[^\]]*\])*\/\d+")

_TYPE3_RE = re.compile(r"^\[3\]:\[0\]:\[(\d+)\]:\[([^\]]+)\]/\d+$")
_TYPE5_RE = re.compile(r"^\[5\]:\[0\]:\[0\]:\[(\d+)\]:\[([^\]]+)\]/\d+$")


def _extract_ip_network(evpn_nlri: str) -> str | None:
    """Extract the IP network from an EVPN NLRI string.

    Returns an IP prefix string (e.g., "192.168.10.0/24") for supported
    route types, or None for types Batfish does not model (Type 2).
    """
    m = _TYPE5_RE.match(evpn_nlri)
    if m:
        return f"{m.group(2)}/{m.group(1)}"
    m = _TYPE3_RE.match(evpn_nlri)
    if m:
        return f"{m.group(2)}/{m.group(1)}"
    return None


def parse_show_bgp_l2vpn_evpn(text: str) -> Sequence[NxosEvpnRoute]:
    all_parse_results = OneOrMore(_rd_block()).leave_whitespace().parse_string(text)
    routes: list[NxosEvpnRoute] = []
    for block in all_parse_results:
        rd = block["rd"]
        for record in block.get("routes", []):
            network = _extract_ip_network(record["network"])
            if network is None:
                continue
            as_path_str = _filter_empty(record.get("as_path", ""))
            as_path = tuple(map(int, as_path_str))
            routes.append(
                NxosEvpnRoute(
                    route_distinguisher=rd,
                    network=network,
                    next_hop_ip=record["next_hop"],
                    metric=record.get("metric", None),
                    local_preference=record.get("local_preference", 100),
                    weight=record["weight"],
                    as_path=as_path,
                    best_path=record["status"][1] in (">", "|"),
                    origin_type=record["origin_type"],
                )
            )
    return routes


def _rd_header() -> ParserElement:
    return (
        Literal("Route Distinguisher:").suppress()
        + White(" ").suppress()
        + Combine(ip + Literal(":") + dec).set_results_name("rd")
        + Optional(White(" ").suppress() + Regex(r"\(.*?\)").suppress())
        + newline
    )


def _rd_block() -> ParserElement:
    return Group(
        SkipTo(_rd_header()).suppress()
        + _rd_header()
        + OneOrMore(_get_record()).set_results_name("routes")
    )


def _get_record() -> ParserElement:
    route_status = Combine(
        one_of(["*", "s", " "]) + one_of([">", "|", " "])
    ).set_results_name("status")
    path_type = MatchFirst(
        [Literal("e"), Literal("l"), Literal("i"), Literal("a"), Literal("r")]
    )
    origin_type = Regex(r"(e|i|\?)")
    as_path = ZeroOrMore(dec + White(" ")).set_results_name("as_path")
    record = Group(
        route_status
        + Optional(White(" ", max=1))
        + path_type.set_results_name("path_type")
        + _EVPN_NETWORK.set_results_name("network")
        + newline
        + White(" ", min=1)
        + ip.set_results_name("next_hop")
        + White(" ", min=1, max=18)
        + Optional(dec).set_results_name("metric")
        + White(" ", min=1, max=9)
        + Optional(dec).set_results_name("local_preference")
        + White(" ", min=1)
        + dec.set_results_name("weight")
        + White(" ", min=1)
        + as_path
        + origin_type.set_results_name("origin_type")
        + Optional(newline)
    ).leave_whitespace()
    return record


def _filter_empty(as_path_list: Sequence[str]) -> list[str]:
    return list(filter(lambda x: (False if x == " " else True), as_path_list))
