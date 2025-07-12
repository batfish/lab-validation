from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    SkipTo,
    Word,
    printables,
)

from ...common.tokens import dec, ip, prefix, to_eol

_time = dec + ":" + dec + ":" + dec


def show_ip_route_vrf_all() -> ParserElement:
    """Grammar for parsing output of 'show ip route vrf all'"""
    return OneOrMore(Group(_vrf_header() + _middle() + _routes_block_within_subnet()))


def _vrf_header() -> ParserElement:
    return Literal("VRF:") + Word(printables).setResultsName("vrf")


def _middle() -> ParserElement:
    to_skip = (
        Literal("Codes:") + SkipTo("Gateway of last resort is") + to_eol
    ).setResultsName("skipped")
    return Group(to_skip)


def _routes_block_within_subnet() -> ParserElement:
    return OneOrMore(Group(_ip_v4_route_line())).setResultsName("v4_routes")


_protocol_codes = [
    "C",  # connected
    "S",  # static
    "K",  # kernel,
    "O",  # OSPF
    "IA",  # OSPF inter area
    "E1",  # OSPF external type 1
    "E2",  # OSPF external type 2
    "N1",  # OSPF NSSA external type 1,
    "N2",  # OSPF NSSA external type2
    "B I",  # iBGP
    "B E",  # eBGP,
    "R",  # RIP
    "I L1",  # IS-IS level 1
    "I L2",  # IS-IS level 2,
    "O3",  # OSPFv3
    "A B",  # BGP Aggregate
    "A O",  # OSPF Summary,
    "NG",  # Nexthop Group Static Route
    "V",  # VXLAN Control Service,
    "DH",  # DHCP client installed default route
    "M",  # Martian,
    "DP",  # Dynamic Policy Route
]


def _ip_v4_route_line() -> ParserElement:
    return (
        MatchFirst([Literal(code) for code in _protocol_codes]).setResultsName(
            "protocol"
        )
        + prefix.setResultsName("network")
        + MatchFirst([_directly_connected_line(), _prefix_via_nhip_line()])
    )


def _directly_connected_line() -> ParserElement:
    return "is directly connected," + Word(printables).setResultsName("nh_iface")


def _prefix_via_nhip_line() -> ParserElement:
    return (
        "["
        + dec.setResultsName("admin")
        + "/"
        + dec.setResultsName("metric")
        + "]"
        + "via"
        + ip.setResultsName("nh_ip")
        + ", "
        + Word(printables).setResultsName("nh_iface")
    )
