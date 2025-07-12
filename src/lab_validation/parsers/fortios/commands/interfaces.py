import logging
from typing import List, Sequence, Text

from pyparsing import Group, OneOrMore, ParseResults

from ...common.exceptions import UnrecognizedLinesError
from ..grammar.interface import interface_block, physical_interface_block
from ..models.interfaces import FortiosInterface, FortiosPhysicalInterface


def parse_get_system_interface(ifaces_text: Text) -> Sequence[FortiosInterface]:
    logger = logging.getLogger(__name__)
    all_logical_parse_results = OneOrMore(Group(interface_block())).scanString(
        ifaces_text
    )
    results: List[FortiosInterface] = []

    last_loc = 0
    for records, start_loc, end_loc in all_logical_parse_results:
        for record in records:
            results.append(construct_iface(record))
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(
                "Did not match:\n{}".format(ifaces_text[last_loc:start_loc])
            )
        last_loc = end_loc

    if not results:
        logger.warning("No interface data found")
    return results


def parse_get_system_interface_physical(
    ifaces_physical_text: Text,
) -> Sequence[FortiosPhysicalInterface]:
    logger = logging.getLogger(__name__)
    all_physical_parse_results = OneOrMore(
        Group(physical_interface_block())
    ).scanString(ifaces_physical_text)
    results: List[FortiosPhysicalInterface] = []

    last_loc = 0
    for records, start_loc, end_loc in all_physical_parse_results:
        for record in records:
            results.append(construct_physical_iface(record))
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(
                "Did not match:\n{}".format(ifaces_physical_text[last_loc:start_loc])
            )
        last_loc = end_loc

    if not results:
        logger.warning("No physical interface data found")
    return results


def construct_iface(record: ParseResults) -> FortiosInterface:
    assert_list = ["name", "status", "type"]
    assert all(item in record for item in assert_list)
    return FortiosInterface(
        name=record["name"],
        mode=record.get("mode"),
        ip_addr=record.get("ip_addr"),
        ip_mask=record.get("ip_mask"),
        status=record["status"],
        type=record["type"],
    )


def construct_physical_iface(record: ParseResults) -> FortiosPhysicalInterface:
    assert_list = ["name", "mode", "status"]
    assert all(item in record for item in assert_list)
    return FortiosPhysicalInterface(
        name=record["name"],
        mode=record["mode"],
        ip_addr=record.get("ip_addr"),
        ip_mask=record.get("ip_mask"),
        ipv6_addr=record.get("ipv6_addr"),
        status=record["status"],
        speed=record.get("speed") if record.get("speed") != "n/a" else None,
        bit_rate_unit=record.get("bit_rate_unit"),
        duplex=record.get("duplex"),
    )
