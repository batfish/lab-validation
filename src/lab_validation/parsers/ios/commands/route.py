import ipaddress
import logging
import re
from typing import List, Optional, Sequence, Text

from pyparsing import ParseResults

from ...common.exceptions import UnrecognizedLinesError
from ..grammar.route import show_route
from ..models.routes import IosIpRoute

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


def parse_show_ip_route(routes_output: Text) -> Sequence[IosIpRoute]:
    """Parses show ip route output for IOS"""
    logger = logging.getLogger(__name__)
    raw_parsed_results = show_route().scanString(routes_output)
    routes: List[IosIpRoute] = []
    last_loc = 0
    last_vrf = "default"  # the table for the default vrf will not have a vrf header
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
        if "padding" in vrf_table and _IPv4_PATTERN.search(vrf_table.padding):
            # An IP address appears in the padding, likely indicating a parsing problem
            raise UnrecognizedLinesError(
                "Unexpected IP address in what is being parsed as padding: "
                + vrf_table.padding
            )
        if "vrf" in vrf_table:
            last_vrf = vrf_table["vrf"]
        routes += _parse_routes_in_vrf(vrf_table.v4_routes, last_vrf)
        last_loc = end_loc
    if not routes:
        logger.warning(f"No routes found in {last_vrf} vrf")
    return routes


def _parse_routes_in_vrf(v4_route_records: ParseResults, vrf: str) -> List[IosIpRoute]:
    routes = []
    for record in v4_route_records:
        routes += _parse_single_route_record(record, vrf)
    return routes


def _parse_single_route_record(record: ParseResults, vrf: str) -> List[IosIpRoute]:
    if "v4_routes_block" not in record:
        raise UnrecognizedLinesError("Unexpected record: " + repr(record))

    if "v4_routes_block_within_subnet" in record:
        subnet_prefix = record["subnet_prefix"]
    else:
        subnet_prefix = None

    network: Optional[str] = None
    protocol: Optional[str] = None
    routes = []
    for v4_route in record["v4_routes_block"]:
        if "network" not in v4_route:
            # happens for second line during ECMP
            assert "protocol" not in v4_route
            assert network is not None
            assert protocol is not None
        else:
            assert "protocol" in v4_route
            network = v4_route["network"]
            assert network is not None
            protocol = _get_protocol(v4_route)
            assert protocol is not None
        routes.append(_get_v4_route(v4_route, network, protocol, subnet_prefix, vrf))
    return routes


def _get_v4_route(
    parsed_route: ParseResults,
    network: Text,
    protocol: Text,
    subnet_prefix: Optional[Text],
    vrf: Text,
) -> IosIpRoute:
    """
    Get v4_route from subnet block
    Example:
              192.168.123.0/32 is subnetted, 7 subnets
        B        192.168.123.1 [20/0] via 10.12.11.1, 00:42:30
        B        192.168.123.2 [20/0] via 10.12.11.1, 00:42:30
    """
    default_admin = 1 if protocol == "static" else 0
    return IosIpRoute(
        network=_get_network(network, subnet_prefix),
        protocol=protocol,
        next_hop_ip=parsed_route.get("nh_ip", None),
        next_hop_int=parsed_route.get("nh_iface", None),
        admin=parsed_route.get("admin", default_admin),
        metric=parsed_route.get("metric", 0),
        vrf=vrf,
    )


def _get_network(network: Text, subnet_prefix: Optional[Text]) -> Text:
    """Add subnet mask to network if needed"""
    if "/" in network:
        return network

    assert subnet_prefix is not None
    return str(
        ipaddress.ip_network(
            network + "/" + subnet_prefix.split("/")[1],
            strict=False,
        )
    )


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
