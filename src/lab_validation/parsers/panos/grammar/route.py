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
    + SkipTo(" (id").setResultsName("vr")
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
    prefix.setResultsName("destination")
    + ip.setResultsName("nexthop")
    + Optional(dec).setWhitespaceChars(" ").setResultsName("metric")
    + _flags.setWhitespaceChars(" ").setResultsName("flags")
    + Optional(dec).setWhitespaceChars(" ").setResultsName("age")
    + Optional(Word(alphas, printables))
    .setWhitespaceChars(" ")
    .setResultsName("interface")
    + Optional(dec).setWhitespaceChars(" ").setResultsName("next-AS")
    + to_eol.setResultsName("route_line_tail")
)


def show_route() -> ParserElement:
    return (
        _vr
        + ZeroOrMore(_route_line).setResultsName("routes")
        + SkipTo(MatchFirst([_vr, stringEnd])).setResultsName("padding")
    )
