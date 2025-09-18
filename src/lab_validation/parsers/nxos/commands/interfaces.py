import logging
from collections.abc import Sequence

from pyparsing import Group, OneOrMore

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.nxos.commands.utils import to_interface_name
from lab_validation.parsers.nxos.grammar.interface import interface_block
from lab_validation.parsers.nxos.models.interfaces import NxosInterface


def parse_show_interface(text: str) -> Sequence[NxosInterface]:
    logger = logging.getLogger(__name__)
    all_parse_results = OneOrMore(Group(interface_block())).scanString(text)
    results: list[NxosInterface] = []

    last_loc = 0
    for records, start_loc, end_loc in all_parse_results:
        for record in records:
            admin_state = record.get("admin_state", None)
            port_status_reason = record.get("port_status_reason", None)
            results.append(
                NxosInterface(
                    name=to_interface_name(record["name"]),
                    admin=get_admin_state(admin_state, port_status_reason),
                    line=record["line_state"] == "up",
                    bandwidth=record["bw"] * 1000,
                    mtu=record["mtu"],
                    mode=record.get("mode", None),
                )
            )
        if start_loc != last_loc and last_loc != 0:
            raise UnrecognizedLinesError(f"Did not match:\n{text[last_loc:start_loc]}")
        last_loc = end_loc
    if not results:
        logger.warning("No interface data found")
    return results


def get_admin_state(admin_state: str | None, port_status_reason: str) -> bool:
    """
    return admin_state based on parsed admin_state or port_status_reason
    """
    if admin_state is None:
        return not port_status_reason == "(Administratively down)"
    else:
        return admin_state == "up"
