import logging
import re
from typing import List, Sequence, Text

from pyparsing import Group, ParseResults

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.common.utils import hex_to_ip
from lab_validation.parsers.nxos.commands.utils import to_interface_name
from lab_validation.parsers.nxos.grammar.route import show_route
from lab_validation.parsers.nxos.models.routes import NxosMainRibRoute

_IPv4_PATTERN = re.compile(r"\d+\.\d+\.\d+\.\d+")


def parse_show_ip_route_vrf_all(text: Text) -> Sequence[NxosMainRibRoute]:
    logger = logging.getLogger(__name__)
    all_parse_results = Group(show_route()).scanString(text)
    routes: List[NxosMainRibRoute] = []
    last_loc = 0
    for records, start_loc, end_loc in all_parse_results:
        if last_loc != 0 and start_loc != last_loc and text[last_loc:start_loc].strip():
            # There is text between records that is not whitespace, throw an error so we investigate
            raise UnrecognizedLinesError(
                "Did not match: [bytes {} to {}, end_loc is {}]\n{}".format(
                    last_loc, start_loc, end_loc, text[last_loc:start_loc]
                )
            )
        for record in records:
            vrf = record["vrf"]
            for single_v4_route in record.v4_routes:
                for nhop in single_v4_route["next_hops"]:
                    if not _is_best(nhop):  # only keep best routes
                        continue
                    nhint = nhop.get("nhint")
                    if nhint is not None:
                        nhint = to_interface_name(nhint)
                    routes.append(
                        NxosMainRibRoute(
                            vrf=vrf,
                            network=single_v4_route["network"],
                            protocol=_get_protocol(nhop),
                            next_vrf=nhop.get("nhvrf", None),
                            next_hop_ip=nhop.get("nhip", None),
                            next_hop_int=nhint,
                            admin=nhop["admin"],
                            metric=nhop["metric"],
                            tag=nhop.get("tag", None),
                            evpn=nhop.get("evpn") is not None,
                            segid=nhop.get("segid", None),
                            tunnelid=hex_to_ip(nhop["tunnelid"])
                            if "tunnelid" in nhop
                            else None,
                        )
                    )
            if "padding" in record and _IPv4_PATTERN.search(record.padding):
                # An IP address appears in the padding, likely indicating a parsing problem
                raise UnrecognizedLinesError(
                    "Unexpected IP address in what is being parsed as padding: "
                    + record.padding
                )
        last_loc = end_loc
    if not routes:
        logger.warning("No routes found")
    return routes


BGP_EXTENSIONS = {
    "internal": "ibgp",
    "external": "bgp",
}

EIGRP_EXTENSIONS = {
    "internal": "eigrp",
    "external": "eigrpEX",
}

OSPF_EXTENSIONS = {
    "inter": "ospfIA",
    "intra": "ospf",
    "type-1": "ospfE1",
    "type-2": "ospfE2",
}


def _get_protocol(protocol: ParseResults) -> Text:
    if protocol.am:
        return "am"  # adjacency manager
    elif protocol.bgp:
        if protocol.extension:
            return BGP_EXTENSIONS[protocol.extension]
        # local route
        return "bgp"
    if protocol.direct:
        return "direct"
    if protocol.eigrp:
        return EIGRP_EXTENSIONS[protocol.extension]
    if protocol.hmm:
        return "hmm"
    if protocol.hsrp:
        return "hsrp"
    if protocol.local:
        return "local"
    if protocol.ospf:
        return OSPF_EXTENSIONS[protocol.extension]
    if protocol.static:
        return "static"
    raise ValueError(protocol)


def _is_best(best_status: ParseResults) -> bool:
    return True if best_status.best_ucast or best_status.best_mcast else False
