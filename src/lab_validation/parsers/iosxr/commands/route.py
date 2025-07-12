import logging
import re
from typing import Generator, List, Sequence, Text, Tuple

from pyparsing import ParseResults

from ...common.exceptions import UnrecognizedLinesError
from ..grammar.route import show_route, show_route_vrf
from ..models.routes import IosXrRoute

_protocols = {
    "B": "bgp",
    "C": "connected",
    "L": "local",
    "S": "static",
    # OSPF keywords
    "O": "ospf",
    "IA": "ospfIA",
    "E1": "ospfE1",
    "E2": "ospfE2",
    "N1": "ospfE1",
    "N2": "ospfE2",
    # EIGRP keywords
    "D": "eigrp",
    "EX": "eigrpEX",
}

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")
_IPv4_PREFIX_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+/\d+")


def parse_show_route(routes_output: Text) -> Sequence[IosXrRoute]:
    """Parses show route output for IOS XR"""
    return _parse_helper(routes_output, show_route().scanString(routes_output), True)


def parse_show_route_vrf_all(routes_output: Text) -> Sequence[IosXrRoute]:
    """Parses show route vrf all output for IOS XR"""
    return _parse_helper(routes_output, show_route_vrf().scanString(routes_output))


def _parse_helper(
    routes_output: Text,
    raw_parsed_results: Generator[Tuple[ParseResults, int, int], None, None],
    default_vrf: bool = False,
) -> Sequence[IosXrRoute]:
    logger = logging.getLogger(__name__)
    routes: List[IosXrRoute] = []
    last_loc = 0
    # the table for the default vrf will not have a vrf header
    last_vrf = "default" if default_vrf else None
    for vrf_table, start_loc, end_loc in raw_parsed_results:
        if (
            last_loc != 0
            and start_loc != last_loc
            and routes_output[last_loc:start_loc].strip()
        ):
            # There is text between records that is not whitespace, throw an error so we investigate
            raise UnrecognizedLinesError(
                "Did not match: [bytes {} to {}, end_loc is {}]\n{}".format(
                    last_loc, start_loc, end_loc, routes_output[last_loc:start_loc]
                )
            )
        if "preamble" in vrf_table and _IPv4_PREFIX_PATTERN.search(vrf_table.preamble):
            # A prefix appears in what is parsed as the preamble, indicating a parsing problem
            raise UnrecognizedLinesError(
                "Found a prefix in what is being parsed as preamble: "
                + vrf_table.preamble
            )
        if "padding" in vrf_table and _IPv4_PATTERN.search(vrf_table.padding):
            # An IP address appears in the padding, likely indicating a parsing problem
            raise UnrecognizedLinesError(
                "Unexpected IP address in what is being parsed as padding: "
                + vrf_table.padding
            )
        if default_vrf:
            assert "vrf" not in vrf_table
        else:
            assert "vrf" in vrf_table
            last_vrf = vrf_table["vrf"]
        assert last_vrf is not None
        if "v4_routes" in vrf_table:
            routes += _parse_routes_in_vrf(vrf_table.v4_routes, last_vrf)
        last_loc = end_loc
    if not routes:
        logger.warning(f"No routes found in {last_vrf} vrf")
    return routes


def _parse_routes_in_vrf(v4_route_records: ParseResults, vrf: str) -> List[IosXrRoute]:
    routes = []
    for record in v4_route_records:
        routes += _parse_single_record(record, vrf)
    return routes


def _parse_single_record(record: ParseResults, vrf: str) -> List[IosXrRoute]:
    if "v4_route" not in record:
        raise UnrecognizedLinesError("Unexpected record: " + repr(record))

    routes = [_get_v4_route(record, vrf)]
    assert "protocol" in record
    network: str = record.get("network")
    assert network is not None
    protocol: str = _get_protocol(record)
    assert protocol is not None

    if "v4_ecmp_routes_block" in record:
        for v4_route in record["v4_ecmp_routes_block"]:
            routes.append(_get_v4_ecmp_routes_block(v4_route, network, protocol, vrf))

    return routes


def _get_v4_ecmp_routes_block(
    parsed_route: ParseResults,
    network: Text,
    protocol: Text,
    vrf: Text,
) -> IosXrRoute:
    """
    Get v4_route from ecmp block
    Example:
    B        1.1.1.3/32 [20/0] via 10.10.101.1, 00:40:12
                        [20/0] via 10.10.100.1, 00:40:12
    """
    return _get_v4_route_helper(network, protocol, parsed_route, vrf)


def _get_v4_route(parsed_route: ParseResults, vrf: Text) -> IosXrRoute:
    """
    Get normal/single v4_route
    Example:
        B     192.168.122.0/24 [20/0] via 10.12.11.1, 00:03:1
    """
    return _get_v4_route_helper(
        parsed_route["network"], _get_protocol(parsed_route), parsed_route, vrf
    )


def _get_v4_route_helper(
    network: str, protocol: str, parsed_route: ParseResults, vrf: Text
) -> IosXrRoute:
    """
    Get normal/single v4_route
    Example:
        B     192.168.122.0/24 [20/0] via 10.12.11.1, 00:03:1
    """
    return IosXrRoute(
        network=network,
        protocol=protocol,
        next_hop_ip=parsed_route.get("nh_ip"),
        next_hop_int=parsed_route.get("nh_iface"),
        next_hop_vrf=parsed_route.get("nh_vrf"),
        admin=parsed_route.get("admin", _get_default_admin(protocol)),
        metric=parsed_route.get("metric", 0),
        vrf=vrf,
        backup="backup" in parsed_route,
    )


def _get_default_admin(protocol: str) -> int:
    if protocol == "static":
        return 1
    # TODO support more default admin distances for different types of routes
    # https://www.cisco.com/c/en/us/support/docs/ip/enhanced-interior-gateway-routing-protocol-eigrp/8651-21.html
    return 0


def _get_protocol(parsed_route: ParseResults) -> Text:
    protocol = _protocols[parsed_route["protocol"]]
    if protocol == "ospf":
        if "ospf_extensions" in parsed_route:
            return _protocols[parsed_route["ospf_extensions"]]
        elif "summary" in parsed_route:
            return "ospfIS"
    if protocol == "eigrp" and "eigrp_extensions" in parsed_route:
        return _protocols[parsed_route["eigrp_extensions"]]
    return protocol
