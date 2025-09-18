import logging
from typing import Any

from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional as ParsingOptional,
    ParserElement,
    SkipTo,
    Word,
    printables,
    stringEnd,
)

from ...common.exceptions import UnrecognizedLinesError
from ...common.tokens import dec, prefix, to_eol
from ...common.utils import convert_cisco_intf_name

_state = MatchFirst([Literal("up"), Literal("down")])


def _get_iface_line() -> ParserElement:
    return (
        Word(printables).setResultsName("name")
        + _get_admin_line()
        + ", line protocol is"
        + _state.setResultsName("line_protocol")
        + to_eol
    )


def _get_admin_line() -> ParserElement:
    return (
        "is"
        + ParsingOptional("administratively")
        + _state.setResultsName("admin_state")
    )


def _get_mtu_bw_line() -> ParserElement:
    return (
        "MTU"
        + dec.setResultsName("mtu")
        + "bytes,"
        + "BW"
        + dec.setResultsName("bw")
        + "Kbit/sec,"
        + to_eol
    )


def _get_addr_line() -> ParserElement:
    return "Internet address is" + prefix.setResultsName("prefix")


def _interface_block() -> ParserElement:
    iface_line = _get_iface_line()
    return (
        iface_line
        + "Hardware is"
        + to_eol
        + ParsingOptional("Description" + to_eol)
        + ParsingOptional(_get_addr_line())
        + SkipTo("MTU")
        + _get_mtu_bw_line()
        + SkipTo(MatchFirst([iface_line, stringEnd]))
    )


# TODO: this matches return values and signature of genie parsers. Write IosInterface model
def parse_show_interfaces(text: str) -> dict[str, dict[str, Any]]:
    all_parse_results = OneOrMore(Group(_interface_block())).scanString(text)
    results: dict[str, dict[str, Any]] = {}

    logger = logging.getLogger(__name__)
    last_loc = 0
    for records, start_loc, end_loc in all_parse_results:
        for record in records:
            iface_name = convert_cisco_intf_name(record["name"])
            iface_prefix = record.get("prefix")
            results[iface_name] = dict(
                enabled=record["admin_state"] == "up",
                line_protocol=record["line_protocol"],
                bandwidth=record["bw"],
                mtu=record["mtu"],
                ipv4={} if iface_prefix is None else {iface_prefix: None},
            )
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(f"Did not match:\n{text[last_loc:start_loc]}")
        last_loc = end_loc
    if not results:
        logger.warning("No interface data found")
    return results


def _convert_speed(speed: str | None) -> float | None:
    if speed is None:
        return speed
    if speed.lower().endswith("kbps"):
        return int(speed[:-4]) * 1e3
    if speed.lower().endswith("mbps"):
        return int(speed[:-4]) * 1e6
    if speed.lower().endswith("gbps"):
        return int(speed[:-4]) * 1e9
    return float(speed)
