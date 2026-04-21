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

_vrf_line = (
    "IP Route Table for VRF" + QuotedString('"').set_results_name("vrf") + to_eol
)
_vrf_header = (
    Literal("'*' denotes best ucast next-hop")
    + Literal("'**' denotes best mcast next-hop")
    + Literal("'[x/y]' denotes [preference/metric]")
    + Literal("'%<string>' in via output denotes VRF <string>")
)
_via = MatchFirst(
    [
        Literal("*via").set_results_name("best_ucast"),
        Literal("**via").set_results_name("best_mcast"),
        Literal("via").set_results_name("not_best"),
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
    + dec.set_results_name("admin")
    + "/"
    + dec.set_results_name("metric")
    + "]"
)
_bgp = Regex(r"bgp-\d+").set_results_name("process") + Optional(
    ","
    + MatchFirst([Literal("internal"), Literal("external")]).set_results_name(
        "extension"
    )
)
_eigrp = (
    Regex(r"eigrp-\d+").set_results_name("process")
    + ","
    + MatchFirst([Literal("internal"), Literal("external")]).set_results_name(
        "extension"
    )
)
_ospf = (
    Regex(r"ospf-\d+").set_results_name("process")
    + ","
    + MatchFirst(
        [Literal("inter"), Literal("intra"), Literal("type-1"), Literal("type-2")]
    ).set_results_name("extension")
)
_protocol = MatchFirst(
    [
        _bgp.set_results_name("bgp"),
        _eigrp.set_results_name("eigrp"),
        Literal("am").set_results_name("am"),  # adjacency manager
        Literal("direct").set_results_name("direct"),
        Literal("hmm").set_results_name("hmm"),
        Literal("hsrp").set_results_name("hsrp"),
        Literal("local").set_results_name("local"),
        _ospf.set_results_name("ospf"),
        Literal("static").set_results_name("static"),
    ]
)

_evpn = "(evpn)"
_vxlan = (
    Literal("segid:")
    + dec.set_results_name("segid")
    + Literal("tunnelid: 0x")
    + Word(hexnums).set_results_name("tunnelid")
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
        + ZeroOrMore(Group(_v4_route_for_a_prefix())).set_results_name("v4_routes")
        # Next VRF or EOF. Save the skipped text as padding.
        + SkipTo(MatchFirst([_vrf_line, stringEnd])).set_results_name("padding")
    )


def _v4_route_for_a_prefix() -> ParserElement:
    return _prefix_line() + OneOrMore(
        Group(MatchFirst([_next_hop_line(), _null_routed_line()]))
    ).set_results_name("next_hops")


def _prefix_line() -> ParserElement:
    return prefix.set_results_name("network") + "," + to_eol


def _next_hop_line() -> ParserElement:
    return (
        _via
        + ip.set_results_name("nhip")
        + Optional("%" + Word(alphanums + "/" + ".").set_results_name("nhvrf"))
        + ","
        + Optional(Word(alphanums + "/" + ".").set_results_name("nhint") + ",")
        + _admin_and_metric
        + ","
        + _uptime
        + ","
        + _protocol.set_results_name("protocol")
        + Optional(", tag" + dec.set_results_name("tag"))
        # Sometimes, there is a stray comma after the tag
        + Optional(",")
        + Optional(_evpn).set_results_name("evpn")
        + Optional(_vxlan).set_results_name("vxlan")
    )


def _null_routed_line() -> ParserElement:
    return (
        _via
        + Literal("Null0").set_results_name("nhint")
        + ","
        + _admin_and_metric
        + ","
        + _uptime
        + ","
        + _protocol.set_results_name("protocol")
        + ","
        + "discard"
        + Optional(", tag" + dec.set_results_name("tag"))
        # Sometimes, there is a stray comma after the tag
        + Optional(",")
        + Optional(_evpn).set_results_name("evpn")
        + Optional(_vxlan).set_results_name("vxlan")
    )
