from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    SkipTo,
    Word,
    ZeroOrMore,
    alphas,
    printables,
    stringEnd,
)

from ...common.tokens import dec, ip, prefix, to_eol

_vr_line_1 = (
    "VIRTUAL ROUTER: "
    + SkipTo(" (id").set_results_name("vr")
    + "(id "
    + dec
    + ")"
    + to_eol
)
_vr_line_2 = OneOrMore("=") + to_eol
_vr_line_3 = (
    Literal("destination")
    + Literal("nexthop")
    + Literal("metric")
    + Literal("flags")
    + Literal("age")
    + Literal("interface")
    + Literal("next-AS")
    + to_eol
)
_vr = _vr_line_1 + _vr_line_2 + _vr_line_3

_flags = ZeroOrMore(
    MatchFirst(
        [
            Literal("A"),
            Literal("?"),
            Literal("C"),
            Literal("H"),
            Literal("S"),
            Literal("~"),
            Literal("R"),
            Literal("O"),
            Literal("B"),
            Literal("Oi"),
            Literal("Oo"),
            Literal("O1"),
            Literal("O2"),
            Literal("E"),
            Literal("M"),
        ]
    )
)

# Inside of the route line, limit whitespace chars so it can't eat part of the next line
_route_line = Group(
    prefix.set_results_name("destination")
    + ip.set_results_name("nexthop")
    + Optional(dec).setWhitespaceChars(" ").set_results_name("metric")
    + _flags.setWhitespaceChars(" ").set_results_name("flags")
    + Optional(dec).setWhitespaceChars(" ").set_results_name("age")
    + Optional(Word(alphas, printables))
    .setWhitespaceChars(" ")
    .set_results_name("interface")
    + Optional(dec).setWhitespaceChars(" ").set_results_name("next-AS")
    + to_eol.set_results_name("route_line_tail")
)


def show_route() -> ParserElement:
    return (
        _vr
        + ZeroOrMore(_route_line).set_results_name("routes")
        + SkipTo(MatchFirst([_vr, stringEnd])).set_results_name("padding")
    )
