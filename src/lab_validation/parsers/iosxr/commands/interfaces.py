import logging
from typing import List, Text

from pyparsing import Group, Literal, MatchFirst, OneOrMore
from pyparsing import Optional as ParsingOptional
from pyparsing import ParserElement, ParseResults, SkipTo, Word, printables, stringEnd

from ...common.exceptions import UnrecognizedLinesError
from ...common.tokens import dec, prefix, to_eol
from ...common.utils import convert_cisco_intf_name
from ..models.interfaces import IosXrInterface

_state = MatchFirst([Literal("up"), Literal("down")])


def _get_iface_line() -> ParserElement:
    return (
        Word(printables).setResultsName("name")
        + "is"
        + ParsingOptional("administratively")
        + _state.setResultsName("admin_state")
        + ", line protocol is"
        + ParsingOptional("administratively")
        + _state.setResultsName("line_protocol")
        + to_eol
    )


def _get_mtu_bw_line() -> ParserElement:
    return (
        "MTU"
        + dec.setResultsName("mtu")
        + "bytes,"
        + "BW"
        + dec.setResultsName("bw")
        + "Kbit"
        + to_eol
    )


def _get_addr_line() -> ParserElement:
    return "Internet address is" + prefix.setResultsName("prefix")


def _interface_block() -> ParserElement:
    iface_line = _get_iface_line()
    return (
        iface_line
        + "Interface state"
        + to_eol
        + ParsingOptional(_dampening())
        + "Hardware is"
        + to_eol
        + ParsingOptional("Description" + to_eol)
        + ParsingOptional(_get_addr_line())
        + SkipTo("MTU")
        + _get_mtu_bw_line()
        + SkipTo(MatchFirst([iface_line, stringEnd]))
    )


def _dampening() -> ParserElement:
    return (
        "Dampening enabled"
        + to_eol
        + "half-life"
        + to_eol
        + "suppress"
        + to_eol
        + "restart-penalty"
        + to_eol
    )


def parse_show_interfaces(text: Text) -> List[IosXrInterface]:
    all_parse_results = OneOrMore(Group(_interface_block())).scanString(text)
    results: List[IosXrInterface] = []

    logger = logging.getLogger(__name__)
    last_loc = 0
    for records, start_loc, end_loc in all_parse_results:
        for record in records:
            results.append(construct_iface(record))
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(
                "Did not match:\n{}".format(text[last_loc:start_loc])
            )
        last_loc = end_loc
    if not results:
        logger.warning("No interface data found")
    return results


def construct_iface(record: ParseResults) -> IosXrInterface:
    assert_list = ["name", "line_protocol", "admin_state"]
    assert all(item in record for item in assert_list)
    return IosXrInterface(
        name=convert_cisco_intf_name(record["name"]),
        line_protocol=record["line_protocol"],
        admin_state=record["admin_state"],
        prefix=record.get("prefix"),
        mtu=record.get("mtu"),
        bw=record.get("bw"),
    )
