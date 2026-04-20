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
        + SkipTo(single_route()).set_results_name("preamble")
        + OneOrMore(single_route()).set_results_name("v4_routes")
        + SkipTo(MatchFirst([vrf_line(), stringEnd])).set_results_name("padding")
    )


def routes_body_empty() -> ParserElement:
    """Parses an empty routes table."""
    return Literal("% No matching routes found")


def vrf_line() -> ParserElement:
    return "VRF: " + Word(printables).set_results_name("vrf") + to_eol


def single_route() -> ParserElement:
    """Grammar for parsing output of 'show ip route'"""
    return Group(
        MatchFirst(
            [
                _v4_ecmp_routes().set_results_name("v4_ecmp_routes"),
                _v4_route().set_results_name("v4_route"),
            ]
        )
    )


def _v4_ecmp_routes() -> ParserElement:
    return _v4_route().set_results_name("v4_route") + OneOrMore(
        Group(_route_suffix())
    ).set_results_name("v4_ecmp_routes_block")


def _directly_connected_line() -> ParserElement:
    return (
        "is directly connected,"
        + Optional(_time + ",")
        + Word(printables).set_results_name("nh_iface")
        + Optional(_nh_in_vrf())
    )


def _is_a_summary_line() -> ParserElement:
    return (
        Literal("is a summary,").set_results_name("summary")
        + Optional(_time + ",")
        + Word(printables).set_results_name("nh_iface")
    )


def _prefix_via_nhip_line() -> ParserElement:
    return (
        "["
        + dec.set_results_name("admin")
        + "/"
        + dec.set_results_name("metric")
        + "]"
        + "via"
        + ip.set_results_name("nh_ip")
        + Optional(_nh_in_vrf())
        + Optional(
            "("
            + Word(printables, excludeChars="!)").set_results_name("source_vrf")
            + ")"
        )
        + Optional("," + _time)
        + Optional(", " + Word(printables).set_results_name("nh_iface"))
        + Optional(Literal("(!)").set_results_name("backup"))  # FRR backup indicator
    )


def _prefix_null_route_line() -> ParserElement:
    return (
        "["
        + dec.set_results_name("admin")
        + "/"
        + dec.set_results_name("metric")
        + "]"
        + Optional("," + _time)
        + Optional(", " + (Regex(r"Null\d+")).set_results_name("nh_iface"))
    )


def _nh_in_vrf() -> ParserElement:
    return (
        "(nexthop in vrf"
        + Word(printables, excludeChars=")").set_results_name("nh_vrf")
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
        ).set_results_name("protocol")
        + Optional(Literal("*").set_results_name("candidate_default"))
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
        ).set_results_name("ospf_extensions")
        + Optional(MatchFirst([Literal("EX")])).set_results_name("eigrp_extensions")
        + Optional(prefix).set_results_name("network")
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
