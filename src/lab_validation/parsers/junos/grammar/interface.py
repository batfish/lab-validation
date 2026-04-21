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
    stringEnd,
)

from ...common.tokens import to_eol

_state = MatchFirst([Literal("up"), Literal("down")]).set_name("state")
_ip_or_ethernet_mtu = MatchFirst([Literal("IP MTU"), Literal("Ethernet MTU")])

_physical_block_header = "Physical interface"
_logical_block_header = "Logical interface"
_interface_block_header = MatchFirst(
    [Literal(_physical_block_header), Literal(_logical_block_header)]
)

# exclude , so we can use Word(_interface_name) to extrace interface names
_noncomma_printables = "".join(c for c in printables if c != ",")


def show_interface() -> ParserElement:
    physical = _physical_record()
    logical = _logical_record()
    return OneOrMore(
        Group(
            MatchFirst([physical, logical])
            + MatchFirst([SkipTo(_interface_block_header), SkipTo(stringEnd)])
        )
    )


def _physical_record() -> ParserElement:
    return (
        _physical_name_line()
        + SkipTo(_physical_type_line())
        + _physical_type_line()
        + SkipTo(_interface_block_header | to_eol)
    )


def _physical_name_line() -> ParserElement:
    return (
        Literal(_physical_block_header).set_results_name("type")
        + ":"
        + Word(_noncomma_printables).set_results_name("name")
        + ","
        + MatchFirst([Literal("Enabled"), Literal("Disabled")]).set_results_name(
            "admin_state"
        )
        + ","
        + "Physical link is"
        + MatchFirst([Literal("Up"), Literal("Down")]).set_results_name("line_state")
    )


def _physical_type_line() -> ParserElement:
    return (
        "Type:"
        + SkipTo("MTU")
        + "MTU:"
        + Word(_noncomma_printables).set_results_name("mtu")
        + Optional(
            Literal(",")
            + Literal("Speed:")
            + Word(printables).set_results_name("speed")
        )
    )


def _logical_record() -> ParserElement:
    return (
        _logical_name_line()
        + "Flags:"
        + Word(printables).set_results_name("admin_state")
        + to_eol
        + Optional("Bandwidth:" + Word(printables).set_results_name("bw"))
        + SkipTo("MTU:")
        + "MTU:"
        + Word(printables).set_results_name("mtu")
        + SkipTo(_interface_block_header | stringEnd)
    )


def _logical_name_line() -> ParserElement:
    return (
        Literal(_logical_block_header).set_results_name("type")
        + Word(_noncomma_printables).set_results_name("name")
        + to_eol
    )
