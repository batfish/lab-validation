import math
from collections.abc import Sequence
from os import PathLike, path
from typing import Any

from pybatfish.datamodel import NextHop, NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.frr.commands.interfaces import parse_show_interface
from lab_validation.parsers.frr.commands.routes import parse_show_ip_route_vrf_all_json
from lab_validation.parsers.frr.commands.vrf import get_show_vrf
from lab_validation.parsers.frr.models.interfaces import FrrInterface
from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class CumulusFrrValidator(VendorValidator):
    # Plain TEXT files
    SHOW_INTERFACES_FILENAME_TXT = "vtysh_-c_'show_interface_vrf_all'.txt"
    SHOW_VRF_FILENAME_TXT = "vtysh_-c_'show_vrf'.txt"
    SHOW_ROUTE_FILENAME_TXT = "vtysh_-c_'show_ip_route_vrf_all_json'.txt"

    # JSON files
    SHOW_ROUTE_FILENAME = "vtysh_-c_'show_ip_route_vrf_all_json'.json"

    def _first_file(self, json_filename: str, txt_filename: str) -> str:
        """Returns the name of the first file that exists."""
        filename = path.join(self.device_path, json_filename)
        return (
            filename
            if path.isfile(filename)
            else path.join(self.device_path, txt_filename)
        )

    def __init__(self, device_path: PathLike) -> None:
        self.device_path: PathLike = device_path
        self.vrf_mapping: dict = self._show_vrf()

    def _show_vrf(self) -> dict:
        show_vrf_path = path.join(
            self.device_path, CumulusFrrValidator.SHOW_VRF_FILENAME_TXT
        )

        if not path.isfile(show_vrf_path):
            return {}

        with open(show_vrf_path) as fp:
            vrf_text = fp.read()
            # Check if file is empty
            if not vrf_text:
                return {}
        return get_show_vrf(vrf_text)

    def get_runtime_data(self) -> NodeRuntimeData:
        interfaces = self._show_interfaces()
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=iface.bandwidth, lineUp=iface.line, speed=None
                )
                for iface in interfaces
            }
        )

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> dict[Any, Any]:
        return self._compare_all_interfaces(self._show_interfaces(), batfish_interfaces)

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[str, str]:
        """Validating main RIB routes from all VRFs"""
        show_routes: Sequence[FrrIpRoute] = self._parse_routes()
        show_routes_updated: list[FrrIpRoute] = self._show_route_processed(show_routes)

        matched_routes = match_pairs(
            show_routes_updated,
            batfish_routes,
            CumulusFrrValidator._diff_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    def _show_route_processed(
        self, show_routes: Sequence[FrrIpRoute]
    ) -> list[FrrIpRoute]:
        show_routes_updated: list[FrrIpRoute] = []
        for r in show_routes:
            """Adding vrf from `show_vrf_cmd` as FRR `show_route` data does not have vrf_name.
            It only has vrf_id. So doing mapping of vrf_id --> vrf_name"""
            vrf = self.vrf_mapping.get(str(r.vrf)) if r.vrf is not None else "default"

            # Exclude kernel routes
            if r.protocol in ["kernel"]:
                continue

            # FRR shows up active and/or inactive routes in main RIB
            # Skipping inactive routes
            if r.active is False:
                continue

            show_routes_updated.append(
                FrrIpRoute(
                    vrf=vrf,
                    network=r.network,
                    next_hop_int=r.next_hop_int,
                    next_hop_ip=r.next_hop_ip,
                    protocol=r.protocol,
                    admin_distance=r.admin_distance,
                    metric=r.metric,
                    active=r.active,
                    blackhole=r.blackhole,
                )
            )
        return show_routes_updated

    def _show_interfaces(self) -> Sequence[FrrInterface]:
        show_interfaces_path = path.join(
            self.device_path, CumulusFrrValidator.SHOW_INTERFACES_FILENAME_TXT
        )

        assert path.isfile(show_interfaces_path)

        with open(show_interfaces_path) as fp:
            interfaces_text = fp.read()
        return parse_show_interface(interfaces_text)

    @staticmethod
    def _compare_all_interfaces(
        show_interfaces: Sequence[FrrInterface],
        batfish_interfaces: Sequence[InterfaceProperties],
    ) -> dict[Any, Any]:
        diffs: dict[Any, Any] = {
            "batfish_extra": {},
            "batfish_missing": {},
            "batfish_mismatch": {},
        }
        batfish_iface_index = {i.name.lower(): i for i in batfish_interfaces}
        show_iface_index = {i.name.lower(): i for i in show_interfaces}
        for name in batfish_iface_index.keys() - show_iface_index.keys():
            diffs["batfish_extra"][name] = batfish_iface_index[name]
        for name, show_iface_detail in show_iface_index.items():
            if name not in batfish_iface_index:
                diffs["batfish_missing"][name] = show_iface_index[name]
                continue
            batfish_mismatch = CumulusFrrValidator._compare_interfaces(
                show_iface_detail, batfish_iface_index[name]
            )
            if batfish_mismatch:
                diffs["batfish_mismatch"][name] = batfish_mismatch
        return diffs

    @staticmethod
    def _compare_interfaces(
        show_iface_detail: FrrInterface, batfish_iface_detail: InterfaceProperties
    ) -> dict[str, str]:
        diff = {}

        if batfish_iface_detail.active != show_iface_detail.admin:
            diff["active"] = (
                f"Batfish: {batfish_iface_detail.active}, show_data: {show_iface_detail.admin}"
            )

        if batfish_iface_detail.bandwidth != show_iface_detail.bandwidth:
            diff["bandwidth"] = (
                f"Batfish: {batfish_iface_detail.bandwidth}, show_data: {show_iface_detail.bandwidth}"
            )

        if batfish_iface_detail.mtu != show_iface_detail.mtu:
            diff["mtu"] = (
                f"Batfish: {batfish_iface_detail.mtu}, show_data: {show_iface_detail.mtu}"
            )

        return diff

    def _parse_routes(self) -> Sequence[FrrIpRoute]:
        show_route_path = self._first_file(
            CumulusFrrValidator.SHOW_ROUTE_FILENAME,
            CumulusFrrValidator.SHOW_ROUTE_FILENAME_TXT,
        )
        assert path.isfile(show_route_path)

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_ip_route_vrf_all_json(routes_text)

    @staticmethod
    def _diff_routes_cost(show_route: FrrIpRoute, batfish_route: MainRibRoute) -> float:
        cost = 0.0
        # return infinite cost if prefix does not match
        if show_route.network != batfish_route.network:
            return math.inf
        if show_route.protocol != batfish_route.protocol:
            cost += compute_protocol_cost(show_route.protocol, batfish_route.protocol)

        if show_route.metric != batfish_route.metric:
            cost += 1.0
        if show_route.admin_distance != batfish_route.admin:
            cost += 1.0
        if show_route.vrf != batfish_route.vrf:
            cost += 1.0
        cost += compute_next_hop_cost(show_route, batfish_route.next_hop)

        return cost


def compute_next_hop_cost(frr_route: FrrIpRoute, next_hop: NextHop) -> float:
    """Returns a cost based on the next-hops of the routes. Takes into account null route, ip, and interface."""
    if frr_route.blackhole and isinstance(next_hop, NextHopDiscard):
        # Both null routes, don't compare anything else
        return 0.0
    if frr_route.blackhole or isinstance(next_hop, NextHopDiscard):
        # Null route and non-null route are dang incompatible
        return 10.0

    if isinstance(next_hop, NextHopIp):
        if frr_route.next_hop_ip != next_hop.ip:
            return 1.0
        return 0.0
    # For static routes with only next-hop IP, FRR includes the resolved interface,
    # so do not check that it's not present.

    if isinstance(next_hop, NextHopInterface):
        cost = 0.0
        if frr_route.next_hop_int != next_hop.interface:
            # Different interfaces, not a match.
            cost += 3.0
        if next_hop.ip and frr_route.next_hop_ip != next_hop.ip:
            cost += 1.0
        return cost

    raise ValueError("Unsupported next hop " + repr(next_hop))


def compute_protocol_cost(real_protocol: str, batfish_protocol: str) -> float:
    if real_protocol == batfish_protocol:
        return 0.0
    if real_protocol == "bgp" and batfish_protocol in {"bgp", "ibgp"}:
        # Show data doesn't distinguish different BGP types
        return 0.0
    if real_protocol == "ospf" and batfish_protocol in {
        "ospf",
        "ospfE1",
        "ospfE2",
        "ospfIA",
        "ospfIS",
    }:
        # Show data doesn't distinguish different OSPF types
        return 0.0
    return math.inf
