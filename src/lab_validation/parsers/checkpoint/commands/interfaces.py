import logging
from collections.abc import Iterable

from pyparsing import (
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    ParserElement,
    ParseResults,
    Word,
    printables,
)

from ...common.exceptions import UnrecognizedLinesError
from ...common.tokens import dec, prefix, to_eol
from ..models.interfaces import CheckpointInterface

_state = MatchFirst([Literal("on"), Literal("off")])


def _interface_block() -> ParserElement:
    iface_line = "Interface" + Word(printables).setResultsName("name") + to_eol
    state_line = "state" + _state.setResultsName("state") + to_eol
    mac_addr_line = "mac-addr" + to_eol
    type_line = "type" + Word(printables).setResultsName("type") + to_eol
    link_state_line = "link-state" + to_eol
    mtu_line = "mtu" + dec.setResultsName("mtu") + to_eol
    auto_negotiation_line = "auto-negotiation" + to_eol
    speed_line = (
        "speed"
        + MatchFirst([dec.setResultsName("speed_Mbps"), Literal("N/A")])
        + to_eol
    )
    ipv6_autoconfig_line = "ipv6-autoconfig" + to_eol
    duplex_line = "duplex" + to_eol
    monitor_mode_line = "monitor-mode" + to_eol
    link_speed_line = "link-speed" + to_eol
    comments_line = "comments" + to_eol
    ipv4_address_line = (
        "ipv4-address"
        + MatchFirst([prefix.setResultsName("prefix"), Literal("Not")])
        + to_eol
    )
    ipv6_address_line = "ipv6-address" + to_eol
    ipv6_local_link_address_line = "ipv6-local-link-address" + to_eol
    return (
        iface_line
        + state_line
        + mac_addr_line
        + type_line
        + link_state_line
        + mtu_line
        + auto_negotiation_line
        + speed_line
        + ipv6_autoconfig_line
        + duplex_line
        + monitor_mode_line
        + link_speed_line
        + comments_line
        + ipv4_address_line
        + ipv6_address_line
        + ipv6_local_link_address_line
        + _statistics_block()
    )


def _statistics_block() -> ParserElement:
    return "Statistics:" + to_eol + "TX" + to_eol + "RX" + to_eol


def parse_show_interfaces(text: str) -> Iterable[CheckpointInterface]:
    all_parse_results = OneOrMore(Group(_interface_block())).scanString(text)
    results: list[CheckpointInterface] = []

    last_loc = 0
    for records, start_loc, end_loc in all_parse_results:
        for record in records:
            results.append(construct_iface(record))
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(f"Did not match:\n{text[last_loc:start_loc]}")
        last_loc = end_loc
    if not results:
        logging.getLogger(__name__).warning("No interface data found")
    return results


def construct_iface(record: ParseResults) -> CheckpointInterface:
    assert_list = ["name", "state", "type", "mtu"]
    assert all(item in record for item in assert_list)
    speed = None if "speed_Mbps" not in record else record["speed_Mbps"] * 1e6
    return CheckpointInterface(
        name=record["name"],
        state=record["state"] == "on",
        type=record["type"],
        mtu=record["mtu"],
        speed=speed,
        prefix=record.get("prefix"),
    )
