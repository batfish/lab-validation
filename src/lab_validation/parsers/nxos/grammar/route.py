# coding: utf-8
from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    QuotedString,
    Regex,
    SkipTo,
    Word,
    ZeroOrMore,
    alphanums,
    hexnums,
    stringEnd,
)

from lab_validation.parsers.common.tokens import dec, ip, prefix, to_eol

_vrf_line = "IP Route Table for VRF" + QuotedString('"').setResultsName("vrf") + to_eol
_vrf_header = (
    Literal("'*' denotes best ucast next-hop")
    + Literal("'**' denotes best mcast next-hop")
    + Literal("'[x/y]' denotes [preference/metric]")
    + Literal("'%<string>' in via output denotes VRF <string>")
)
_via = MatchFirst(
    [
        Literal("*via").setResultsName("best_ucast"),
        Literal("**via").setResultsName("best_mcast"),
        Literal("via").setResultsName("not_best"),
    ]
)
_uptime_hours = Regex(r"\d+:\d+:\d+")
_update_days = Regex(r"\d+d\d+h")
_uptime_weeks = Regex(r"\d+w\d+d")
_uptime_years = Regex(r"\d+y\d+w")
_uptime_zeroes = "0.000000"
_uptime = MatchFirst(
    [_uptime_hours, _update_days, _uptime_weeks, _uptime_years, Literal(_uptime_zeroes)]
)
_admin_and_metric = (
    Literal("[")
    + dec.setResultsName("admin")
    + "/"
    + dec.setResultsName("metric")
    + "]"
)
_bgp = Regex(r"bgp-\d+").setResultsName("process") + Optional(
    ","
    + MatchFirst([Literal("internal"), Literal("external")]).setResultsName("extension")
)
_eigrp = (
    Regex(r"eigrp-\d+").setResultsName("process")
    + ","
    + MatchFirst([Literal("internal"), Literal("external")]).setResultsName("extension")
)
_ospf = (
    Regex(r"ospf-\d+").setResultsName("process")
    + ","
    + MatchFirst(
        [Literal("inter"), Literal("intra"), Literal("type-1"), Literal("type-2")]
    ).setResultsName("extension")
)
_protocol = MatchFirst(
    [
        _bgp.setResultsName("bgp"),
        _eigrp.setResultsName("eigrp"),
        Literal("am").setResultsName("am"),  # adjacency manager
        Literal("direct").setResultsName("direct"),
        Literal("hmm").setResultsName("hmm"),
        Literal("hsrp").setResultsName("hsrp"),
        Literal("local").setResultsName("local"),
        _ospf.setResultsName("ospf"),
        Literal("static").setResultsName("static"),
    ]
)

_evpn = "(evpn)"
_vxlan = (
    Literal("segid:")
    + dec.setResultsName("segid")
    + Literal("tunnelid: 0x")
    + Word(hexnums).setResultsName("tunnelid")
    + Literal("encap: VXLAN")
)


def show_route() -> ParserElement:
    """Parse a single VRF's show route output."""
    return (
        # IP Route Table for VRF "<vrf>"
        _vrf_line
        # The lines about flags ('*', '**', '[x/y]', '%', etc).
        + _vrf_header
        # Routes table may be empty.
        + ZeroOrMore(Group(_v4_route_for_a_prefix())).setResultsName("v4_routes")
        # Next VRF or EOF. Save the skipped text as padding.
        + SkipTo(MatchFirst([_vrf_line, stringEnd])).setResultsName("padding")
    )


def _v4_route_for_a_prefix() -> ParserElement:
    return _prefix_line() + OneOrMore(
        Group(MatchFirst([_next_hop_line(), _null_routed_line()]))
    ).setResultsName("next_hops")


def _prefix_line() -> ParserElement:
    return prefix.setResultsName("network") + "," + to_eol


def _next_hop_line() -> ParserElement:
    return (
        _via
        + ip.setResultsName("nhip")
        + Optional("%" + Word(alphanums + "/" + ".").setResultsName("nhvrf"))
        + ","
        + Optional(Word(alphanums + "/" + ".").setResultsName("nhint") + ",")
        + _admin_and_metric
        + ","
        + _uptime
        + ","
        + _protocol.setResultsName("protocol")
        + Optional(", tag" + dec.setResultsName("tag"))
        # Sometimes, there is a stray comma after the tag
        + Optional(",")
        + Optional(_evpn).setResultsName("evpn")
        + Optional(_vxlan).setResultsName("vxlan")
    )


def _null_routed_line() -> ParserElement:
    return (
        _via
        + Literal("Null0").setResultsName("nhint")
        + ","
        + _admin_and_metric
        + ","
        + _uptime
        + ","
        + _protocol.setResultsName("protocol")
        + ","
        + "discard"
        + Optional(", tag" + dec.setResultsName("tag"))
        # Sometimes, there is a stray comma after the tag
        + Optional(",")
        + Optional(_evpn).setResultsName("evpn")
        + Optional(_vxlan).setResultsName("vxlan")
    )
