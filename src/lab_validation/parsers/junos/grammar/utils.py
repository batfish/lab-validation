from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    ParserElement,
    Regex,
    Word,
    ZeroOrMore,
    printables,
)

from ...common.tokens import dec

non_colon_printables = "".join(filter(lambda c: c != ":", printables))

origin_type = MatchFirst([Literal("I"), Literal("E"), Literal("?")], savelist=False)
as_set = dec.setResultsName("as_numbers") | (
    Literal("(") + OneOrMore(dec).setResultsName("as_numbers") + Literal(")")
)
as_path = ZeroOrMore(Group(as_set))


def rib_meta_info() -> ParserElement:
    return (
        Word(non_colon_printables).setResultsName("vrf_ip_info")
        + ":"
        + Regex(
            r"\d+ destinations, \d+ routes \(\d+ active, \d+ holddown, \d+ hidden\)"
        )
        + Literal("+ = Active Route, - = Last Active, * = Both")
    )
