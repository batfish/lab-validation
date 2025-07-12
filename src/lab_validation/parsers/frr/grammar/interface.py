from pyparsing import (
    Literal,
    MatchFirst,
    Optional,
    ParserElement,
    SkipTo,
    Word,
    printables,
    stringEnd,
)

from ...common.tokens import dec, to_eol

_state = MatchFirst([Literal("up"), Literal("down")])


def interface_block() -> ParserElement:
    iface_line = _get_iface_line()
    return (
        iface_line
        + SkipTo("mtu")
        + _get_mtu_speed()
        # Bandwidth will be available only when configured manually, otherwise bandwidth==speed
        + Optional(SkipTo("bandwidth"))
        + Optional(_get_bandwidth())
        + to_eol
        + SkipTo(MatchFirst([iface_line, stringEnd]))
    )


def _get_iface_line() -> ParserElement:
    return MatchFirst([_get_iface_line_admin_up(), _get_iface_line_admin_down()])


def _get_iface_line_admin_up() -> ParserElement:
    return (
        Literal("Interface").suppress()
        + Word(printables).setResultsName("name")
        + Literal("is").suppress()
        + Literal("up").setResultsName("admin_state")
        + Literal(",").suppress()
        + Literal("line protocol is").suppress()
        + _state.setResultsName("line_state")
        + to_eol
    )


def _get_iface_line_admin_down() -> ParserElement:
    return (
        Literal("Interface").suppress()
        + Word(printables).setResultsName("name")
        + Literal("is").suppress()
        + Word(printables).setResultsName("admin_state")
        + to_eol
    )


def _get_mtu_speed() -> ParserElement:
    return (
        Literal("mtu").suppress()
        + dec.setResultsName("mtu")
        # bit-rate unit for speed is mbps in FRR show interface
        + Literal("speed").suppress()
        + dec.setResultsName("speed")
        + to_eol
    )


def _get_bandwidth() -> ParserElement:
    return (
        Literal("bandwidth").suppress()
        + dec.setResultsName("bandwidth")
        + Word(printables).setResultsName("bit_rate_unit")
        + to_eol
    )
