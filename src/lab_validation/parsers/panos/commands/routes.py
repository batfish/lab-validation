import logging
import re
from collections.abc import Sequence

from pyparsing import ParseResults

from ...common.exceptions import UnrecognizedLinesError
from ..grammar.route import show_route
from ..models.routes import PanosMainRibRoute

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


def parse_show_routing_route(text: str) -> Sequence[PanosMainRibRoute]:
    """
    Parses a PanOS `show routing route` output.

    A given file may contain more than one routing table.
    """
    logger = logging.getLogger(__name__)
    all_parse_results = show_route().scanString(text)
    routes: list[PanosMainRibRoute] = []
    last_loc = 0
    for vr_record, start_loc, end_loc in all_parse_results:
        if start_loc != last_loc and last_loc != 0 and text[last_loc:start_loc].strip():
            raise UnrecognizedLinesError(
                f"Did not match: [bytes {last_loc} to {start_loc}, end_loc is {end_loc}]\n{text[last_loc:start_loc]}"
            )
        if _IPv4_PATTERN.search(vr_record.padding):
            # An IP address appears in the padding, likely indicating a parsing problem
            raise UnrecognizedLinesError(
                "Unexpected IP address in what is being parsed as padding: "
                + vr_record.padding
            )
        virtual_router = vr_record["vr"].strip()
        for route_record in vr_record.routes:
            routes.append(_deserialize_route(route_record, virtual_router))
        last_loc = end_loc
    if not routes:
        logger.warning("No routes found")
    return routes


def _deserialize_route(record: ParseResults, vr: str) -> PanosMainRibRoute:
    """
    Converts a single route into a PanosMainRibRoute.
    """
    if record.route_line_tail.strip():
        raise UnrecognizedLinesError(
            f"Unexpected text after a route record: {record.route_line_tail.strip()}"
        )
    return PanosMainRibRoute(
        virtual_router=vr,
        network=record.destination,
        next_hop_ip=record.nexthop,
        metric=record.get("metric"),
        flags=set(record.flags),
        age=record.get("age"),
        next_hop_int=record.get("interface"),
        next_AS=record.get("next-AS"),
    )
