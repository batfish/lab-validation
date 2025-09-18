import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pybatfish.datamodel import NextHop, NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.panos.commands.routes import parse_show_routing_route
from lab_validation.parsers.panos.models.routes import PanosMainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import ValidationError, VendorValidator


class PanosValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        real_routes: Sequence[PanosMainRibRoute] = self._get_main_rib_all_vrfs()
        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            PanosValidator._diff_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        raise ValidationError("Not implemented")

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> dict[Any, Any]:
        """Validating interfaces"""
        raise ValidationError("Not implemented")

    def _get_main_rib_all_vrfs(self) -> Sequence[PanosMainRibRoute]:
        """Parses and returns the main rib for all VRFs."""

        routes_path = self.device_path / "run_show_routing_route.txt"
        assert routes_path.is_file()

        routes_text = routes_path.read_text()
        return parse_show_routing_route(routes_text)

    @staticmethod
    def _diff_routes_cost(
        expected_route: PanosMainRibRoute, batfish_route: MainRibRoute
    ) -> float:
        cost = 0.0
        expected_network_tokens = expected_route.network.split("/")
        batfish_network_tokens = batfish_route.network.split("/")
        # return infinite cost if vrf or network subnet does not match
        if expected_network_tokens[0] != batfish_network_tokens[0]:
            return math.inf
        if expected_route.virtual_router != batfish_route.vrf:
            return math.inf

        if expected_network_tokens[1] != batfish_network_tokens[1]:
            cost += abs(
                float(expected_network_tokens[1]) - float(batfish_network_tokens[1])
            )

        expected_protocol = expected_route.get_protocol()
        if expected_protocol != batfish_route.protocol:
            cost += PanosValidator.compute_protocol_cost(
                expected_protocol, batfish_route.protocol
            )

        if expected_route.metric != batfish_route.metric:
            # show data metric missing(none) means 0. So, skipping that case
            if expected_route.metric is None and batfish_route.metric == 0:
                pass
            else:
                cost += 1.0

        cost += PanosValidator.compute_nexthop_cost(
            expected_route, batfish_route.next_hop
        )

        return cost

    @staticmethod
    def compute_nexthop_cost(
        expected_route: PanosMainRibRoute, next_hop: NextHop
    ) -> float:
        # null route section
        if expected_route.next_hop_ip == "discard" and isinstance(
            next_hop, NextHopDiscard
        ):
            return 0.0
        elif expected_route.next_hop_ip == "discard" or isinstance(
            next_hop, NextHopDiscard
        ):
            # Only one is null-routed.
            return 10.0

        # nh_ip section
        if isinstance(next_hop, NextHopIp):
            if expected_route.next_hop_ip == next_hop.ip:
                return 0.0
            return 1.0

        if isinstance(next_hop, NextHopInterface):
            cost = 0.0
            if next_hop.interface != expected_route.next_hop_int:
                if "H" not in expected_route.flags:
                    # PanOS Host routes (local routes) do not have the interface listed
                    cost += 1.0
            if next_hop.ip is not None and next_hop.ip != expected_route.next_hop_ip:
                cost += 1.0
            return cost

        raise ValueError("Unsupported next hop " + repr(next_hop))

    @staticmethod
    def compute_protocol_cost(panos_protocol: str, batfish_protocol: str) -> float:
        """
        Computes the protocol cost, given that they are not equal.
        Return math.inf when they are totally different protocols. Examples bgp & ospf, ospf & eigrp etc...
        """

        # Return 0 when panos is bgp and batfish is bgp sub-type; panos does not provide bgp sub-type info.
        if panos_protocol == "bgp" and batfish_protocol in {"ibgp", "bgp"}:
            return 0.0

        # TODO: Add cases for more protocols (e.g. OSPF, EIGRP) as PAN showparser supports them.
        # Protocols are completely different.
        return math.inf
