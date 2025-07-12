from pyparsing import Group, Literal, MatchFirst, OneOrMore, Optional, ParserElement

from lab_validation.parsers.junos.grammar.utils import (
    as_path,
    origin_type,
    rib_meta_info,
)

from ...common.tokens import dec, ip, prefix

protocol_abbr = {
    "A": "Aggregate",
    "B": "BGP",
    "C": "CCC",
    "D": "Direct",
    "G": "GMPLS",
    "I": "IS-IS",
    "L": "L2CKT, L2VPN, LDP, Local",
    "K": "Kernel",
    "M": "MPLS, MSDP",
    "O": "OSPF",
    "P": "PIM",
    "R": "RIP, RIPng",
    "S": "Static",
    "T": "Tunnel",
}


def show_bgp_route() -> ParserElement:
    """Grammar for parsing output of 'show route protocol bgp terse'
    See https://www.juniper.net/documentation/en_US/junos/topics/reference/command-summary/show-route-terse.html
    for the semantics of the output of the command
    """
    return OneOrMore(
        Group(rib_meta_info() + _route_block().setResultsName("route_tables"))
    )


def _route_block() -> ParserElement:
    return _table_schema() + OneOrMore(Group(_bgp_route())).setResultsName("routes")


def _table_schema() -> ParserElement:
    return (
        Literal("A")
        + "V"
        + "Destination"
        + "P"
        + "Prf"
        + "Metric 1"
        + "Metric 2"
        + "Next hop"
        + "AS path"
    )


def _bgp_route() -> ParserElement:
    return _bgp_route_line1() + _bgp_route_line2()


def _bgp_route_line1() -> ParserElement:
    return (
        Optional(MatchFirst([Literal("+"), Literal("-"), Literal("*")])).setResultsName(
            "status"
        )
        + MatchFirst([Literal("V"), Literal("?")])
        + prefix.setResultsName("network")
        + MatchFirst([Literal(k) for k in protocol_abbr.keys()]).setResultsName(
            "learn_from"
        )
        + dec.setResultsName("pref")
        + dec.setResultsName("metric_1")
        + Optional(dec).setResultsName("metric_2")
        + as_path.setResultsName("as_path")
        + origin_type.setResultsName("origin_type")
    )


def _bgp_route_line2() -> ParserElement:
    return (
        MatchFirst([Literal("valid"), Literal("unverified")]).setResultsName("is_valid")
        + Optional(">").setResultsName("is_selected")
        + ip.setResultsName("next_hop")
    )
