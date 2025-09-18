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
    Word,
    ZeroOrMore,
    alphanums,
    oneOf,
    stringEnd,
)

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.common.tokens import dec, ip, newline, prefix
from lab_validation.parsers.nxos.models.routes import NxosBgpRoute

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


def parse_show_ip_bgp_all(text: str) -> Sequence[NxosBgpRoute]:
    all_parse_results = OneOrMore(_vrf_af_routes()).parseString(text)
    routes: list[NxosBgpRoute] = []
    network = ""
    for table in all_parse_results:
        vrf = table["vrf"]
        af = table["af"]
        assert af == "IPv4 Unicast"  # TODO: handle more
        for record in table.get("routes", []):
            # network `None` means the least-cost(not valid best) route; hence will use network from previous record
            if record.get("network") is not None:
                network = record["network"]
            as_path_str = _filter_empty(record.get("as_path", ""))
            as_path = tuple(map(int, as_path_str))
            routes.append(
                NxosBgpRoute(
                    network=network,
                    protocol=_get_protocol(record["path_type"]),
                    next_hop_ip=record["next_hop"],
                    metric=record.get("metric", 0),
                    vrf=vrf,
                    as_path=as_path,
                    best_path=record["status"][1] in (">", "|"),
                    local_preference=record.get("local_preference", 100),
                    origin_type=record["origin_type"],
                    weight=record["weight"],
                )
            )
        if "padding" in table and _IPv4_PATTERN.search(table.padding):
            # An IP address appears in the padding, likely indicating a parsing problem
            raise UnrecognizedLinesError(
                "Unexpected IP address in what is being parsed as padding: "
                + table.padding
            )
    return routes


def _af_name() -> ParserElement:
    """A valid BGP address family"""
    return (
        # TODO: there are more
        Literal("IPv4 Unicast")
    )


def _vrf_af_header() -> ParserElement:
    """The header for a BGP table for one VRF, one AF."""
    return (
        Literal("BGP routing table information for VRF ").suppress()
        + Word(alphanums + "-_").setResultsName("vrf")
        + Literal(", address family ").suppress()
        + _af_name().setResultsName("af")
    )


def _af_table_routes_header() -> ParserElement:
    return (
        Literal("Network")
        + Literal("Next Hop")
        + Literal("Metric")
        + Literal("LocPrf")
        + Literal("Weight")
        + Literal("Path")
        + newline
    ).suppress()


def _vrf_af_routes() -> ParserElement:
    return Group(
        _vrf_af_header()
        + SkipTo(_af_table_routes_header())
        + _af_table_routes_header().suppress()
        + OneOrMore(_get_record()).setResultsName("routes")
        # Next VRF or EOF. Save the skipped text as padding.
        + SkipTo(MatchFirst([_vrf_af_header(), stringEnd])).setResultsName("padding")
    )


def _get_record() -> ParserElement:
    route_status = Combine(
        oneOf(["*", "s", " "]) + oneOf([">", "|", " "])
    ).setResultsName("status")
    path_type = MatchFirst(
        [Literal("e"), Literal("l"), Literal("i"), Literal("a"), Literal("r")]
    )
    origin_type = Regex(r"(e|i|\?)")
    as_path = ZeroOrMore(dec + White(" ")).setResultsName("as_path")
    record = Group(
        route_status
        + Optional(White(" ", max=1))
        + path_type.setResultsName("path_type")
        + Optional(prefix.setResultsName("network"))
        + White(" ", min=1)
        + ip.setResultsName("next_hop")
        + White(" ", min=1, max=18)
        + Optional(dec).setResultsName("metric")
        + White(" ", min=1, max=9)
        + Optional(dec).setResultsName("local_preference")
        + White(" ", min=1)
        + dec.setResultsName("weight")
        + White(" ", min=1)
        + as_path
        + origin_type.setResultsName("origin_type")
        + Optional(newline)
    ).leaveWhitespace()
    return record


def _get_protocol(path_type: str) -> str:
    if path_type == "i":
        return "ibgp"
    if path_type == "a":
        return "bgp_aggregate"
    return "bgp"


def _filter_empty(as_path_list: Sequence[str]) -> list[str]:
    return list(filter(lambda x: (False if x == " " else True), as_path_list))
