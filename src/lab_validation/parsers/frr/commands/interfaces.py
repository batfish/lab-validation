import logging
from typing import List, Optional, Sequence, Text

from pyparsing import Group, OneOrMore, ParseResults

from ...common.exceptions import UnrecognizedLinesError
from ..grammar.interface import interface_block
from ..models.interfaces import FrrInterface

_state_code = ["up", "down"]


def parse_show_interface(text: Text) -> Sequence[FrrInterface]:
    logger = logging.getLogger(__name__)
    all_parse_results = OneOrMore(Group(interface_block())).scanString(text)
    results: List[FrrInterface] = []

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


def construct_iface(record: ParseResults) -> FrrInterface:
    assert_list = ["name", "admin_state", "speed", "mtu"]
    assert all(item in record for item in assert_list)
    return FrrInterface(
        name=record["name"],
        admin=decide_iface_status(record["admin_state"]),
        line=decide_iface_status(record.get("line_state")),
        bandwidth=decide_iface_bandwidth(
            record["speed"], record.get("bandwidth"), record.get("bit_rate_unit")
        ),
        mtu=record["mtu"],
    )


def decide_iface_status(state: Optional[Text]) -> bool:
    if state is None or state == "down":
        return False
    else:
        return True


def decide_iface_bandwidth(
    speed: int, bandwidth: Optional[int], bit_rate_unit: Optional[Text]
) -> int:
    assert bit_rate_unit == "Mbps" or bit_rate_unit is None
    if bandwidth is None:
        return speed * 1000000
    else:
        # Whenever BW available in show output, FRR always assign it in `Mbps` unit only
        return bandwidth * 1000000
