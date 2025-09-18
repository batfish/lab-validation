from collections.abc import Sequence
from typing import Any

from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    SkipTo,
    White,
    Word,
    ZeroOrMore,
    alphanums,
)

from ...common.tokens import (
    dec,
    ip,
    prefix,
    printables_and_space,
    route_distinguisher,
    to_eol,
)
from ..models.bgp import IosXrBgpAddressFamily, IosXrBgpRoute, IosXrBgpVrf

"""Status code represents the type of bgp route using below codes combination. For example, '*>' = valid best,
'r>' = RIB failure best etc.

Status codes: s suppressed, d damped, h history, * valid, > best
              i - internal, r RIB-failure, S stale, N Nexthop-discard
"""

# Keep longest match first for the route_status i.e "r>i" should come before "r>"
_STATUS_CODES = [
    "r>i",
    "*>i",
    "s>i",
    "s>",
    "s i",
    "* i",
    "r>",
    "*>",
    "*",
]


def parse_show_bgp_all_all(bgp_output: str) -> Sequence[IosXrBgpAddressFamily]:
    """Parses IOS XR 'show bgp all all' output."""
    # TODO Handle show data for device with no active BGP
    parsed_afs = OneOrMore(_bgp_address_family()).parseString(bgp_output)
    afs = []
    for record in parsed_afs:
        name = record["af"]
        router_id = record.get("router_id")
        local_as = record.get("local_as")
        vrfs = tuple(_convert_vrf(v) for v in record.get("vrfs", []))
        afs.append(
            IosXrBgpAddressFamily(
                name=name, router_id=router_id, local_as=local_as, vrfs=vrfs
            )
        )
    return afs


def _convert_vrf(record: Any) -> IosXrBgpVrf:
    vrf_info = record.get("vrf_info", {})
    name = vrf_info.get("vrf_name", "default")
    route_distinguisher = vrf_info.get("rd")
    return IosXrBgpVrf(
        name=name,
        route_distinguisher=route_distinguisher,
        routes=tuple(_convert_routes(record.get("routes", []))),
    )


def _convert_routes(records: Sequence[Any]) -> Sequence[IosXrBgpRoute]:
    routes = list()
    previous_network = None  # Optional[Text]
    for record in records:
        network = record.get("network", previous_network)
        route_data = parse_route_data(record.get("data"))
        next_hop_ip = route_data["next_hop"]
        best_path = _get_best_path(record.get("status"), network, next_hop_ip)
        as_path_str = _filter_empty(record.get("as_path", ""))
        as_path = tuple(map(int, as_path_str))
        routes.append(
            IosXrBgpRoute(
                network=network,
                next_hop_ip=next_hop_ip,
                # Retain None metrics; it matters whether metric is explicitly displayed
                metric=route_data.get("metric"),
                best_path=best_path,
                local_preference=route_data.get("local_preference", 100),
                weight=route_data["weight"],
                as_path=as_path,
                origin_type=record["origin_type"],
            )
        )
        previous_network = network
    return routes


def _get_best_path(status: str | None, network: str, next_hop_ip: str) -> bool:
    """
    Returns true if a route with the given params is a best path route.
    Only best-path statuses (containing `>`) qualify for RIB entry.
    """
    if status is not None and ">" in status:
        return True
    # special case:  default route being originated locally.
    # TODO This is copied from IOS validator; check that it holds for XR show data
    elif status is None and network == "0.0.0.0/0" and next_hop_ip == "0.0.0.0":
        return True
    else:
        return False


def _filter_empty(as_path_list: Sequence[str]) -> list[str]:
    return list(filter(lambda x: (False if x == " " else True), as_path_list))


def _af_name() -> ParserElement:
    return (
        Literal("IPv4 Multicast")
        | Literal("IPv4 Unicast")
        | Literal("MVPNv4 Unicast")
        | Literal("VPNv4 Unicast")
        | Literal("VPNv4 Multicast")
        | Literal("IPv6 Unicast")
    )


def _af_header() -> ParserElement:
    return (
        Literal("Address Family: ").suppress()
        + _af_name().setResultsName("af")
        + White("\n", exact=1).suppress()
        + OneOrMore(Literal("-")).suppress()
    )


def _af_table() -> ParserElement:
    return (
        _af_table_header()
        + _af_table_state_and_codes()
        + _af_table_routes()
        + _af_table_footer()
    )


def _af_table_header() -> ParserElement:
    return (
        Literal("BGP router identifier ").suppress()
        + ip.setResultsName("router_id")
        + Literal(", local AS number ").suppress()
        + dec.setResultsName("local_as")
    )


def _af_table_state_and_codes() -> ParserElement:
    return (
        Literal("BGP generic scan interval") + SkipTo(Literal("Origin codes:")) + to_eol
    ).suppress()


def _af_table_routes() -> ParserElement:
    return _af_table_routes_header() + ZeroOrMore(
        MatchFirst([_af_table_routes_default_vrf(), _af_table_routes_vrf()])
    ).setResultsName("vrfs")


def _af_table_routes_header() -> ParserElement:
    return (
        Literal("Network")
        + Literal("Next Hop")
        + Literal("Metric")
        + Literal("LocPrf")
        + Literal("Weight")
        + Literal("Path")
        + White("\n", exact=1).suppress()
    ).suppress()


def parse_route_data(route_data: str) -> dict[str, Any]:
    """Return the parsed route data. Includes next hop IP and (if present) metric, local pref, and weight."""
    ip_parser = ip.setResultsName("next_hop") + to_eol
    nhip = ip_parser.parseString(route_data)["next_hop"]
    route_obj = {"next_hop": nhip}
    metric_str = route_data[len(nhip) + 1 : 26].strip()
    loc_prf_str = route_data[27:33].strip()
    weight_str = route_data[34:].strip()
    if metric_str:
        route_obj["metric"] = int(metric_str)
    if loc_prf_str:
        route_obj["local_preference"] = int(loc_prf_str)
    if weight_str:
        route_obj["weight"] = int(weight_str)
    return route_obj


def _af_table_routes_default_vrf() -> ParserElement:
    return Group(OneOrMore(_af_table_routes_vrf_route()).setResultsName("routes"))


def _af_table_routes_vrf() -> ParserElement:
    return Group(
        _af_table_routes_vrf_rd().setResultsName("vrf_info")
        + ZeroOrMore(_af_table_routes_vrf_route()).setResultsName("routes")
    )


def _af_table_routes_vrf_rd() -> ParserElement:
    return Group(
        Literal("Route Distinguisher: ").suppress()
        + route_distinguisher.setResultsName("rd")
        + Literal("(default for vrf ").suppress()
        + Word(alphanums + "-_").setResultsName("vrf_name")
        + Literal(")").suppress()
        + White("\n", exact=1).suppress()
    )


def _af_table_routes_vrf_route() -> ParserElement:
    """
    parse route entry in bgp rib
    """
    route_status = MatchFirst([Literal(code) for code in _STATUS_CODES]).setResultsName(
        "status"
    )
    # Parse nhip, metric, locprf, weight as one big block to parse later.
    # Can't parse now because whitespace expectations aren't consistent:
    # if a route has no listed metric, there may be less whitespace between
    # nhip and locprf than another route has between nhip and metric,
    # depending on the length of the nhip.
    route_data = printables_and_space(40).setResultsName("data")
    as_path = ZeroOrMore(dec + White(" ")).setResultsName("as_path")
    origin_type = Literal("e") ^ Literal("i") ^ Literal("?")
    record = Group(
        Optional(White(" ", max=1)).suppress()
        + Optional(route_status)
        + Optional(White(" ", max=1).suppress())
        + Optional(prefix.setResultsName("network"))
        + White(" ", min=1).suppress()
        + route_data
        + White(" ", min=1).suppress()
        + as_path
        + origin_type.setResultsName("origin_type")
        + White("\n", exact=1).suppress()
    )
    record.leaveWhitespace()
    return record


def _af_table_footer() -> ParserElement:
    return Group(
        Literal("Processed") + dec + Literal("prefixes,") + dec + Literal("paths")
    ).suppress()


def _bgp_address_family() -> ParserElement:
    return Group(_af_header() + Optional(_af_table()))
