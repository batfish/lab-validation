from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    Regex,
    SkipTo,
    Word,
    printables,
    stringEnd,
)

from ...common.tokens import dec, ip, prefix, to_eol

_time_hours = Regex(r"\d+:\d+:\d+")
_time_days = Regex(r"\d+d\d+h")
_time_weeks = Regex(r"\d+w\d+d")
_time_years = Regex(r"\d+y\d+w")
_time = MatchFirst([_time_hours, _time_days, _time_weeks, _time_years])


def show_route() -> ParserElement:
    return MatchFirst([routes_body_empty(), routes_body()])


def show_route_vrf() -> ParserElement:
    """Parses a VRF's routing table."""
    return vrf_line() + show_route()


def routes_body() -> ParserElement:
    """Parses a non-empty routes table."""
    return (
        Literal("Codes:")
        + SkipTo(single_route()).setResultsName("preamble")
        + OneOrMore(single_route()).setResultsName("v4_routes")
        + SkipTo(MatchFirst([vrf_line(), stringEnd])).setResultsName("padding")
    )


def routes_body_empty() -> ParserElement:
    """Parses an empty routes table."""
    return Literal("% No matching routes found")


def vrf_line() -> ParserElement:
    return "VRF: " + Word(printables).setResultsName("vrf") + to_eol


def single_route() -> ParserElement:
    """Grammar for parsing output of 'show ip route'"""
    return Group(
        MatchFirst(
            [
                _v4_ecmp_routes().setResultsName("v4_ecmp_routes"),
                _v4_route().setResultsName("v4_route"),
            ]
        )
    )


def _v4_ecmp_routes() -> ParserElement:
    return _v4_route().setResultsName("v4_route") + OneOrMore(
        Group(_route_suffix())
    ).setResultsName("v4_ecmp_routes_block")


def _directly_connected_line() -> ParserElement:
    return (
        "is directly connected,"
        + Optional(_time + ",")
        + Word(printables).setResultsName("nh_iface")
        + Optional(_nh_in_vrf())
    )


def _is_a_summary_line() -> ParserElement:
    return (
        Literal("is a summary,").setResultsName("summary")
        + Optional(_time + ",")
        + Word(printables).setResultsName("nh_iface")
    )


def _prefix_via_nhip_line() -> ParserElement:
    return (
        "["
        + dec.setResultsName("admin")
        + "/"
        + dec.setResultsName("metric")
        + "]"
        + "via"
        + ip.setResultsName("nh_ip")
        + Optional(_nh_in_vrf())
        + Optional(
            "(" + Word(printables, excludeChars="!)").setResultsName("source_vrf") + ")"
        )
        + Optional("," + _time)
        + Optional(", " + Word(printables).setResultsName("nh_iface"))
        + Optional(Literal("(!)").setResultsName("backup"))  # FRR backup indicator
    )


def _prefix_null_route_line() -> ParserElement:
    return (
        "["
        + dec.setResultsName("admin")
        + "/"
        + dec.setResultsName("metric")
        + "]"
        + Optional("," + _time)
        + Optional(", " + (Regex(r"Null\d+")).setResultsName("nh_iface"))
    )


def _nh_in_vrf() -> ParserElement:
    return (
        "(nexthop in vrf"
        + Word(printables, excludeChars=")").setResultsName("nh_vrf")
        + ")"
    )


def _v4_route() -> ParserElement:
    return (
        Optional(
            MatchFirst(
                [
                    Literal("C"),
                    Literal("B"),
                    Literal("L"),
                    Literal("O"),
                    Literal("S"),
                    Literal("D"),
                ]
            )
        ).setResultsName("protocol")
        + Optional(Literal("*").setResultsName("candidate_default"))
        + Optional(
            MatchFirst(
                [
                    Literal("E1"),
                    Literal("E2"),
                    Literal("IA"),
                    Literal("N1"),
                    Literal("N2"),
                ]
            )
        ).setResultsName("ospf_extensions")
        + Optional(MatchFirst([Literal("EX")])).setResultsName("eigrp_extensions")
        + Optional(prefix).setResultsName("network")
        + _route_suffix()
    )


def _route_suffix() -> ParserElement:
    return MatchFirst(
        [
            _directly_connected_line(),
            _is_a_summary_line(),
            _prefix_via_nhip_line(),
            _prefix_null_route_line(),
        ]
    )
