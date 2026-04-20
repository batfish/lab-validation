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
    ZeroOrMore,
    printables,
    stringEnd,
)

from ...common.tokens import dec, ip, prefix, to_eol

_time_hours = Regex(r"\d+:\d+:\d+")
_time_days = Regex(r"\d+d\d+h")
_time_weeks = Regex(r"\d+w\d+d")
_time = MatchFirst([_time_hours, _time_days, _time_weeks])


def show_route() -> ParserElement:
    return (
        Optional(routing_table_line())
        + middle()
        + ZeroOrMore(single_route()).set_results_name("v4_routes")
        + SkipTo(MatchFirst([routing_table_line(), stringEnd])).set_results_name(
            "padding"
        )
    )


def routing_table_line() -> ParserElement:
    return "Routing Table: " + Word(printables).set_results_name("vrf") + to_eol


def single_route() -> ParserElement:
    """Grammar for parsing output of 'show ip route'"""
    return Group(
        MatchFirst(
            [
                _routes_block().set_results_name("v4_routes_block"),
                _routes_block_within_subnet().set_results_name(
                    "v4_routes_block_within_subnet"
                ),
            ]
        )
    )


def middle() -> ParserElement:
    return Group(
        Literal("Codes:") + SkipTo("Gateway of last resort is") + to_eol
    ).set_results_name("skipped")


def _directly_connected_line() -> ParserElement:
    return (
        "is directly connected,"
        + Optional(_time + ",")
        + Word(printables).set_results_name("nh_iface")
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
        + Optional(
            "("
            + Word(printables, excludeChars=",)").set_results_name("source_vrf")
            + ")"
        )
        + Optional("," + _time)
        + Optional(", " + Word(printables).set_results_name("nh_iface"))
    )


def _prefix_null_route_line() -> ParserElement:
    return (
        "["
        + dec.set_results_name("admin")
        + "/"
        + dec.set_results_name("metric")
        + "]"
        + Optional("," + _time)
        + Optional(", " + Literal("Null0").set_results_name("nh_iface"))
    )


def _routes_block_within_subnet() -> ParserElement:
    return _prefix_is_subnetted_line() + _routes_block()


def _routes_block() -> ParserElement:
    return OneOrMore(Group(_v4_route())).set_results_name("v4_routes_block")


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
        + Optional(MatchFirst([prefix, ip])).set_results_name("network")
        + MatchFirst(
            [
                _directly_connected_line(),
                _is_a_summary_line(),
                _prefix_via_nhip_line(),
                _prefix_null_route_line(),
            ]
        )
    )


def _prefix_is_subnetted_line() -> ParserElement:
    return (
        prefix.set_results_name("subnet_prefix")
        + "is"
        + Optional("variably")
        + "subnetted,"
        + dec
        + "subnets"
        + Optional("," + dec + "masks")
    )
