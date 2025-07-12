import ipaddress
from typing import Any, List
from typing import Optional as OptionalTyping
from typing import Sequence, Text

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
    printables,
)

from ...common.tokens import dec, ip, prefix, route_distinguisher, to_eol
from ..models.bgp import IosBgpAddressFamily, IosBgpRoute, IosBgpVrf

"""Status code represents the type of bgp route using below codes combination. For example, '*>' = valid best,
'r>' = RIB failure best etc.

Status codes:
s suppressed, d damped, h history, * valid, > best, i - internal(ibgp),
r RIB-failure, S Stale, m multipath, b backup-path, f RT-Filter, x best-external, a additional-path,
c RIB-compressed, """

# Keep longest match first for the route_status i.e "r>i" should come before "r>"
_STATUS_CODES = [
    "*  a",
    "* ia",
    "*m a",
    "s ia",
    "r>i",
    "*>i",
    "*m",
    "s>i",
    "* i",
    "r>",
    "*>",
    "*",
]
DEFAULT_ROUTE = ipaddress.ip_address("0.0.0.0")
CLASS_A = ipaddress.ip_network("0.0.0.0/1")
CLASS_B = ipaddress.ip_network("128.0.0.0/2")
CLASS_C = ipaddress.ip_network("192.0.0.0/3")


def parse_show_bgp_all(bgp_output: Text) -> Sequence[IosBgpAddressFamily]:
    """Parses IOS/XE 'show bgp all' output."""
    if bgp_output.strip() == "% BGP not active":
        return []
    parsed_afs = OneOrMore(_bgp_address_family()).parseString(bgp_output)
    afs = []
    for record in parsed_afs:
        name = record["af"]
        router_id = record.get("router_id")
        vrfs = tuple(_convert_vrf(v) for v in record.get("vrfs", []))
        afs.append(IosBgpAddressFamily(name=name, router_id=router_id, vrfs=vrfs))
    return afs


def _convert_vrf(record: Any) -> IosBgpVrf:
    vrf_info = record.get("vrf_info", {})
    name = vrf_info.get("vrf_name", "default")
    rd = vrf_info.get("rd")
    routes = []
    network = ""
    for r in record.get("routes", []):
        if r.get("network") is not None:
            network = r["network"]
        assert network
        routes.append(_convert_route(r, network))
    return IosBgpVrf(name=name, route_distinguisher=rd, routes=tuple(routes))


def _convert_route(record: Any, network: Any) -> IosBgpRoute:
    network = _classful_network(str(network).strip())
    next_hop_ip = str(record["next_hop"]).strip()
    metric = record["metric"].strip()
    if metric == "":
        # default metric
        metric = 0
    else:
        metric = int(metric)
    best_path = _get_best_path(str(record.get("status")).strip())
    local_preference = record["local_preference"].strip()
    if local_preference == "":
        # default local_preference
        local_preference = 100
    else:
        local_preference = int(local_preference)
    as_path_str = _filter_empty(record.get("as_path", ""))
    as_path = tuple(map(int, as_path_str))

    return IosBgpRoute(
        network=network,
        next_hop_ip=next_hop_ip,
        metric=metric,
        best_path=best_path,
        local_preference=local_preference,
        weight=record["weight"],
        as_path=as_path,
        origin_type=record["origin_type"],
    )


def _get_best_path(status: OptionalTyping[Text]) -> bool:
    """
    Todo: Have a better logic to handle valid bgp route that can make entry to RIB.
    Statuses containing "*" are valid routes (">" indicates best path, "m" indicates multipath).
    Statuses with "r" indicate RIB failure (i.e., the main RIB contains a better route for the
    prefix), so such routes should still be in Batfish's BGP RIBs (but not main RIBs).
    Statuses with "s" indicate the route is a suppressed contributor to a BGP aggregate; these
    routes will also appear in Batfish's BGP RIBs.
    """
    # TODO Confirm that "r>" and "s>" are possible (have only seen "r>i", "s>i")
    if status in ["*>", "*m", "*>i", "*m a", "r>", "s>", "r>i", "s>i"]:
        return True
    else:
        return False


def _filter_empty(as_path_list: Sequence[Text]) -> List[Text]:
    return list(filter(lambda x: (False if x == " " else True), as_path_list))


def _classful_network(val: Text) -> Text:
    """Returns either val network or the classful network containing val."""
    if "/" in val:
        return val

    ip_addr = ipaddress.ip_address(val)
    if ip_addr == DEFAULT_ROUTE:
        return str(ipaddress.ip_network(str(ip_addr) + "/0", strict=False))
    if ip_addr in CLASS_A:
        return str(ipaddress.ip_network(str(ip_addr) + "/8", strict=False))
    elif ip_addr in CLASS_B:
        return str(ipaddress.ip_network(str(ip_addr) + "/16", strict=False))
    elif ip_addr in CLASS_C:
        return str(ipaddress.ip_network(str(ip_addr) + "/24", strict=False))
    else:
        return str(ipaddress.ip_network(str(ip_addr) + "/32", strict=False))


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
    return Literal("For address family: ").suppress() + _af_name().setResultsName("af")


def _af_table() -> ParserElement:
    return _af_table_header() + _af_table_codes() + _af_table_routes()


def _af_table_header() -> ParserElement:
    return (
        Literal("BGP table version is").suppress()
        + dec.suppress()
        + Literal(", local router ID is").suppress()
        + ip.setResultsName("router_id")
    )


def _af_table_codes() -> ParserElement:
    return (
        Literal("Status codes:") + SkipTo(Literal("RPKI validation codes:")) + to_eol
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
    ).suppress()


def _af_table_routes_default_vrf() -> ParserElement:
    return Group(
        OneOrMore(
            MatchFirst(
                [_af_table_routes_vrf_route(), _af_table_routes_vrf_multi_route()]
            )
        ).setResultsName("routes")
    )


def _af_table_routes_vrf() -> ParserElement:
    return Group(
        _af_table_routes_vrf_rd().setResultsName("vrf_info")
        + ZeroOrMore(_af_table_routes_vrf_route()).setResultsName("routes")
    )


def _af_table_routes_vrf_rd() -> ParserElement:
    return Group(
        Literal("Route Distinguisher:").suppress()
        + route_distinguisher.setResultsName("rd")
        + Literal("(default for vrf ").suppress()
        + Word(alphanums + "-_").setResultsName("vrf_name")
        + MatchFirst(
            [
                Literal(") VRF Router ID").suppress()
                + ip.setResultsName("vrf_router_id"),
                Literal(")").suppress(),
            ]
        )
    )


def _af_table_routes_vrf_route() -> ParserElement:
    """
    parse route entry in bgp rib
    """
    route_status = MatchFirst([Literal(code) for code in _STATUS_CODES]).setResultsName(
        "status"
    )
    as_path = ZeroOrMore(dec + White(" ", exact=1)).setResultsName("as_path")
    origin_type = Literal("e") ^ Literal("i") ^ Literal("?")
    record = Group(
        White(min=1, max=2).suppress()
        + Optional(route_status)
        + Optional(White(" ", min=1).suppress())
        + (ip ^ prefix).setResultsName("network")
        + Optional(White("\n", exact=1).suppress())
        + White(" ", min=1).suppress()
        + Word(printables + " ", exact=15).setResultsName("next_hop")
        + Word(printables + " ", exact=11).setResultsName("metric")
        # exact=7 in local_preference is set as per the current show data examples that we have.
        # It needs to be adjusted if we see the value beyond it. Technically it can go up to 10 char.
        + Word(printables + " ", exact=7).setResultsName("local_preference")
        + White(" ", min=1).suppress()
        + dec.setResultsName("weight")
        + White(" ", min=1).suppress()
        + as_path
        + origin_type.setResultsName("origin_type")
    ).leaveWhitespace()
    return record


def _af_table_routes_vrf_multi_route() -> ParserElement:
    """
    parse multi route entry in bgp rib. It may or may not be ecmp("*m") in bgp rib
    """
    route_status = MatchFirst([Literal(code) for code in _STATUS_CODES]).setResultsName(
        "status"
    )
    as_path = ZeroOrMore(dec + White(" ")).setResultsName("as_path")
    origin_type = Literal("e") ^ Literal("i") ^ Literal("?")
    record = Group(
        White(min=1, max=2).suppress()
        + route_status
        + White(" ", min=1).suppress()
        + Word(printables + " ", exact=15).setResultsName("next_hop")
        + Word(printables + " ", exact=11).setResultsName("metric")
        # exact=7 in local_preference is set as per the current show data examples that we have.
        # It needs to be adjusted if we see the value beyond it. Technically it can go up to 10 char.
        + Word(printables + " ", exact=7).setResultsName("local_preference")
        + White(" ", min=1).suppress()
        + dec.setResultsName("weight")
        + White(" ", min=1).suppress()
        + as_path
        + origin_type.setResultsName("origin_type")
    ).leaveWhitespace()
    return record


def _bgp_address_family() -> ParserElement:
    return Group(_af_header() + Optional(_af_table()))
