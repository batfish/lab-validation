import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Text, Tuple

from pybatfish.datamodel.route import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
)

from lab_validation.parsers.a10.commands.bgp import parse_show_ip_bgp
from lab_validation.parsers.a10.commands.routes import (
    parse_show_ip_route_acos,
    parse_show_ip_route_all,
)
from lab_validation.parsers.a10.models.bgp import A10BgpRoute
from lab_validation.parsers.a10.models.routes import A10MainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import ValidationError, VendorValidator


class A10AcosValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path
        self.bgp_routes: Optional[List[A10BgpRoute]] = None
        self.routes: Optional[List[A10MainRibRoute]] = None

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> Dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        return _compare_all_bgp_rib_routes(self._parse_bgp_rib_routes(), batfish_routes)

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validate main RIB routes."""
        return _compare_all_main_rib_routes(
            self._parse_main_rib_routes(), batfish_routes
        )

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        """Validating interfaces"""
        raise ValidationError("Not implemented")

    def _parse_bgp_rib_routes(self) -> List[A10BgpRoute]:
        """Returns the routes in the BGP RIB for this snapshot."""
        if self.bgp_routes is None:
            file = self.device_path / "show_ip_bgp.txt"
            if not file.is_file():
                self.bgp_routes = []
            else:
                text = file.read_text()
                self.bgp_routes = parse_show_ip_bgp(text)

        return self.bgp_routes

    def _parse_main_rib_routes(self) -> List[A10MainRibRoute]:
        """Returns the routes in the Main RIB for this snapshot."""
        if self.routes is None:
            self.routes = self._parse_show_route_all() + self._parse_show_route_acos()

        return self.routes

    def _parse_show_route_all(self) -> List[A10MainRibRoute]:
        file = self.device_path / "show_ip_route_all.txt"
        if not file.is_file():
            return []
        else:
            text = file.read_text()
            return parse_show_ip_route_all(text)

    def _parse_show_route_acos(self) -> List[A10MainRibRoute]:
        file = self.device_path / "show_ip_route_acos.txt"
        if not file.is_file():
            return []
        else:
            text = file.read_text()
            return parse_show_ip_route_acos(text)


def _compare_all_bgp_rib_routes(
    a10_routes: List[A10BgpRoute], batfish_routes: Sequence[BgpRibRoute]
) -> Dict[str, str]:
    """Compares A10 and Batfish BGP RIB routes."""
    matched_routes = match_pairs(
        a10_routes,
        batfish_routes,
        _bgp_rib_cost,
    )
    return matched_pairs_to_failures(matched_routes)


def _compare_all_main_rib_routes(
    a10_routes: List[A10MainRibRoute], batfish_routes: Sequence[MainRibRoute]
) -> Dict[str, str]:
    """Compares A10 and Batfish main RIB routes."""
    matched_routes = match_pairs(
        a10_routes,
        batfish_routes,
        _main_rib_cost,
    )
    return matched_pairs_to_failures(matched_routes)


def _bgp_rib_cost(
    a10_route: A10BgpRoute, bf_route: BgpRibRoute
) -> List[Tuple[str, float]]:
    """Compares a single pair of A10 and Batfish BGP RIB routes, explaining any differences."""
    if a10_route.network != bf_route.network:
        return [("network", math.inf)]

    ret: List[Tuple[str, float]] = []

    if isinstance(bf_route.next_hop, NextHopDiscard):
        if a10_route.next_hop_ip != "0.0.0.0":
            ret += [("next_hop_ip", 1)]
    elif isinstance(bf_route.next_hop, NextHopIp):
        if bf_route.next_hop.ip != a10_route.next_hop_ip:
            ret += [("next_hop_ip", 1)]
    else:
        raise ValueError("Unsupported next hop " + repr(bf_route.next_hop))

    if bf_route.metric != (a10_route.metric or 0):
        ret += [("metric", 1)]

    if bf_route.local_preference != (a10_route.local_preference or 100):
        ret += [("local_preference", 1)]

    if bf_route.weight != (a10_route.weight or 0):
        ret += [("weight", 1)]

    if bf_route.as_path != a10_route.as_path:
        ret += [("as_path", 1)]

    if not _bgp_origin_type_compatible(bf_route.origin_type, a10_route.origin_type):
        ret += [("origin_type", 1)]

    return ret


def _bgp_origin_type_compatible(bf: Text, acos: Text) -> bool:
    if bf == "igp":
        return bool(acos == "i")
    elif bf == "egp":
        return bool(acos == "e")
    assert bf == "incomplete"
    return bool(acos == "?")


def _main_rib_cost(
    a10_route: A10MainRibRoute, bf_route: MainRibRoute
) -> List[Tuple[str, float]]:
    """Compares a single pair of A10 and Batfish main RIB routes, explaining any differences."""
    if a10_route.network != bf_route.network:
        return [("network", math.inf)]

    ret: List[Tuple[str, float]] = []
    ret += _main_rib_protocol_cost(a10_route, bf_route)
    if any(cost == math.inf for reason, cost in ret):
        # Stop if we found inf already
        return ret

    ret += _main_rib_nexthop_cost(a10_route, bf_route.next_hop)

    if bf_route.admin != (a10_route.admin or 0):
        ret += [("admin", 1)]

    if bf_route.metric != (a10_route.metric or 0):
        ret += [("metric", 1)]

    return ret


_bf_kernel_route_tags = {"N": 1, "VF": 2, "V": 3, "F": 4}


def _main_rib_protocol_cost(
    a10_route: A10MainRibRoute, bf_route: MainRibRoute
) -> List[Tuple[str, float]]:
    """Compares the protocol fields, explaining any differences."""
    # show ip route acos routes (in Batfish as kernel route with specific tag)
    if a10_route.protocol == "N":
        if bf_route.protocol == "kernel" and bf_route.tag == _bf_kernel_route_tags["N"]:
            return []
        return [("protocol", math.inf)]
    if a10_route.protocol == "VF":
        if (
            bf_route.protocol == "kernel"
            and bf_route.tag == _bf_kernel_route_tags["VF"]
        ):
            return []
        return [("protocol", math.inf)]
    if a10_route.protocol == "V":
        if bf_route.protocol == "kernel" and bf_route.tag == _bf_kernel_route_tags["V"]:
            return []
        return [("protocol", math.inf)]
    if a10_route.protocol == "F":
        if bf_route.protocol == "kernel" and bf_route.tag == _bf_kernel_route_tags["F"]:
            return []
        return [("protocol", math.inf)]

    # static
    if a10_route.protocol == "S":
        if bf_route.protocol == "static":
            return []
        return [("protocol", math.inf)]

    # connected
    if a10_route.protocol == "C":
        if bf_route.protocol == "connected":
            return []
        return [("protocol", math.inf)]

    # bgp
    if a10_route.protocol == "B":
        if bf_route.protocol in {"bgp", "ibgp", "aggregate"}:
            return []
        return [("protocol", math.inf)]

    # no match
    return [("protocol", math.inf)]


def _main_rib_nexthop_cost(
    a10_route: A10MainRibRoute, next_hop: NextHop
) -> List[Tuple[str, float]]:
    """Compares the next hops, explaining any differences."""

    if a10_route.protocol in _bf_kernel_route_tags.keys():
        # show ip route acos routes (in Batfish as kernel route with specific tag)
        assert isinstance(next_hop, NextHopDiscard)
        return []

    # NB: A10 does not have null routes.
    assert not isinstance(next_hop, NextHopDiscard)

    if isinstance(next_hop, NextHopInterface):
        ret = []
        if a10_route.next_hop_int != next_hop.interface:
            ret.append(("nhint", math.inf))
        if next_hop.ip is not None and a10_route.next_hop_ip != next_hop.ip:
            ret.append(("nhip", 1.0))
        if a10_route.protocol != "C":
            ret.append(("nhint only expected on connected routes", 10.0))
        return ret
    else:
        # Connected routes must have next-hop interface routes.
        assert a10_route.protocol != "C"

    if isinstance(next_hop, NextHopIp):
        if a10_route.next_hop_ip != next_hop.ip:
            return [("nhip", 1.0)]
        return []

    raise ValueError("Unsupported next hop " + repr(next_hop))
