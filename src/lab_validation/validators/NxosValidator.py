import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Text, Tuple

from pybatfish.datamodel.route import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
    NextHopVtep,
)

from lab_validation.parsers.nxos.commands.bgp_route import parse_show_ip_bgp_all
from lab_validation.parsers.nxos.commands.interfaces import parse_show_interface
from lab_validation.parsers.nxos.commands.routes import parse_show_ip_route_vrf_all
from lab_validation.parsers.nxos.models.interfaces import NxosInterface
from lab_validation.parsers.nxos.models.routes import NxosBgpRoute, NxosMainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class NxosValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path
        # Parsing interfaces show data is dang slow; cache them.
        self.interfaces: Optional[Sequence[NxosInterface]] = None

    def get_runtime_data(self) -> NodeRuntimeData:
        interfaces = self._get_interfaces()
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=iface.bandwidth, lineUp=iface.line, speed=None
                )
                for iface in interfaces
                if iface.is_physical()
            }
        )

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        nxos_interfaces = self._get_interfaces()

        diffs: Dict[Any, Any] = {}
        batfish_index = {i.name.lower(): i for i in batfish_interfaces}
        real_index = {i.name.lower(): i for i in nxos_interfaces}
        for name in batfish_index.keys() - real_index.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"
        for name, nxos_if in real_index.items():
            if name not in batfish_index:
                diffs[name] = f"Missing interface in Batfish: {nxos_if}"
                continue
            diff = NxosValidator._compare_interfaces(nxos_if, batfish_index[name])
            if diff:
                diffs[name] = diff
        return diffs

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        nxos_routes = self._get_main_rib_all_vrfs()

        return NxosValidator._validate_main_rib_routes(batfish_routes, nxos_routes)

    @staticmethod
    def _validate_main_rib_routes(
        batfish_routes: Sequence[MainRibRoute], nxos_routes: Sequence[NxosMainRibRoute]
    ) -> Dict[Any, Any]:
        # Drop mgmt routes and hsrp routes (https://github.com/batfish/lab-validation/issues/59)
        # Drop hmm routes: https://github.com/batfish/lab-validation/issues/61
        validate_routes = [
            r
            for r in nxos_routes
            if r.protocol != "hsrp"
            and r.protocol != "hmm"
            and (r.next_hop_int is None or not r.next_hop_int.startswith("mgmt"))
        ]

        matched_routes = match_pairs(
            batfish_routes,
            validate_routes,
            NxosValidator._diff_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _diff_routes_cost(
        batfish_route: MainRibRoute, nxos_route: NxosMainRibRoute
    ) -> List[Tuple[str, float]]:
        if nxos_route.network != batfish_route.network:
            return [("network", math.inf)]
        if nxos_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []
        cost += NxosValidator.compute_protocol_cost(
            nxos_route.protocol, batfish_route.protocol
        )
        cost += NxosValidator.compute_next_hop_cost(nxos_route, batfish_route.next_hop)

        if nxos_route.metric != batfish_route.metric:
            cost.append(("metric", 1.0))
        if nxos_route.admin != batfish_route.admin:
            cost.append(("admin", 2.0))
        if not NxosValidator._tag_compatible(batfish_route.tag, nxos_route.tag):
            cost.append(("tag", 1.0))
        return cost

    def validate_bgp_rib_routes(self, routes: Sequence[BgpRibRoute]) -> Dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        return NxosValidator._validate_bgp_rib_routes(
            self._get_bgp_rib_all_vrfs(), routes
        )

    @staticmethod
    def _validate_bgp_rib_routes(
        nxos_routes: Sequence[NxosBgpRoute], batfish_routes: Sequence[BgpRibRoute]
    ) -> Dict[Any, Any]:
        # For now, drop non-best-path routes.
        validate_routes = [r for r in nxos_routes if r.best_path]

        matched_routes = match_pairs(
            batfish_routes,
            validate_routes,
            NxosValidator._diff_bgp_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _diff_bgp_routes_cost(
        batfish_route: BgpRibRoute, nxos_route: NxosBgpRoute
    ) -> List[Tuple[str, float]]:
        if nxos_route.network != batfish_route.network:
            return [("network", math.inf)]
        if nxos_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []
        cost += NxosValidator.compute_bgp_protocol_cost(
            nxos_route.protocol, batfish_route.protocol
        )
        cost.extend(
            NxosValidator._diff_bgp_next_hop_cost(batfish_route.next_hop, nxos_route)
        )

        # NX-OS does not show AD in BGP routes

        if nxos_route.metric != batfish_route.metric:
            cost.append(("metric", 1.0))

        # NX-OS does not show tag in BGP routes

        if nxos_route.local_preference != batfish_route.local_preference:
            cost.append(("local_preference", 1.0))
        if nxos_route.weight != batfish_route.weight:
            cost.append(("weight", 1.0))
        if nxos_route.as_path != batfish_route.as_path:
            cost.append(("as_path", 1.0))
        if not NxosValidator._bgp_origin_type_compatible(
            batfish_route.origin_type, nxos_route.origin_type
        ):
            cost.append(("origin_type", 1.0))

        return cost

    @staticmethod
    def _diff_bgp_next_hop_cost(
        next_hop: NextHop, nxos_route: NxosBgpRoute
    ) -> List[Tuple[str, float]]:
        cost = []
        if isinstance(next_hop, NextHopDiscard):
            if nxos_route.next_hop_ip != "0.0.0.0":
                # asymmetric next hop
                cost.append(("nhip", 2.0))
        elif isinstance(next_hop, NextHopIp):
            if nxos_route.next_hop_ip == "0.0.0.0":
                # asymmetric next hop
                cost.append(("nhip", 2.0))
            elif nxos_route.next_hop_ip != next_hop.ip:
                cost.append(("nhip", 1.0))
        elif isinstance(next_hop, NextHopInterface):
            if nxos_route.next_hop_ip != "0.0.0.0":
                # TODO: confirm it should be 0.0.0.0 for unnumbered
                # asymmetric
                cost.append(("nhip", 2.0))
            else:
                # TODO: validate interface for unnumbered NXOS next hop if possible
                pass
        elif isinstance(next_hop, NextHopVtep):
            # TODO: cannot validate VNI until NX-OS source of truth is changed to detail
            if nxos_route.next_hop_ip == "0.0.0.0":
                # asymmetric next hop
                cost.append(("nhip", 2.0))
            elif nxos_route.next_hop_ip != next_hop.vtep:
                cost.append(("nhip", 1.0))
        else:
            raise ValueError("Unsupported next hop " + repr(next_hop))
        return cost

    @staticmethod
    def _compare_interfaces(
        nxos_interface: NxosInterface, batfish_if: InterfaceProperties
    ) -> Dict[Text, Text]:
        diff = {}

        if batfish_if.active != (nxos_interface.admin and nxos_interface.line):
            if not batfish_if.name.startswith("mgmt"):
                # Batfish deactivates management interfaces
                diff[
                    "active"
                ] = f"Batfish: {batfish_if.active}, NXOS: admin={nxos_interface.admin} line={nxos_interface.line}"

        nxos_bw = nxos_interface.bandwidth
        if batfish_if.bandwidth != nxos_bw:
            if not batfish_if.active and batfish_if.name.startswith("port-channel"):
                # https://github.com/batfish/lab-validation/issues/60
                # NX-OS sticks a default bandwidth on down port-channel, but Batfish does not.
                # No obvious reason to care about this.
                pass
            else:
                diff["bandwidth"] = f"Batfish: {batfish_if.bandwidth}, NXOS: {nxos_bw}"

        if batfish_if.mtu != nxos_interface.mtu:
            diff["mtu"] = f"Batfish: {batfish_if.mtu}, NXOS: {nxos_interface.mtu}"

        if str(batfish_if.switchport_mode).lower() != str(nxos_interface.mode).lower():
            diff[
                "switchport_mode"
            ] = f"Batfish: {batfish_if.switchport_mode}, NXOS: {nxos_interface.mode}"

        return diff

    @staticmethod
    def _tag_compatible(bf_tag: Optional[int], tag: Optional[int]) -> bool:
        if bf_tag == tag:
            return True
        if (bf_tag is None or bf_tag == 0) and (tag is None or tag == 0):
            return True
        return False

    @staticmethod
    def _bgp_origin_type_compatible(bf: Text, nx: Text) -> bool:
        if bf == "igp":
            return bool(nx == "i")
        elif bf == "egp":
            return bool(nx == "e")
        assert bf == "incomplete"
        return bool(nx == "?")

    def _get_main_rib_all_vrfs(self) -> Sequence[NxosMainRibRoute]:
        """Parses and returns the main rib for all VRFs."""

        default_vrf_routes_path = self.device_path / "show_ip_route_vrf_all.txt"
        assert default_vrf_routes_path.is_file()

        return parse_show_ip_route_vrf_all(default_vrf_routes_path.read_text())

    def _get_interfaces(self) -> Sequence[NxosInterface]:
        """Parses and returns the interfaces."""
        if self.interfaces is not None:
            return self.interfaces

        interfaces: Sequence[NxosInterface] = []
        default_interfaces_path = self.device_path / "show_interface.txt"
        if default_interfaces_path.is_file():
            interfaces = parse_show_interface(default_interfaces_path.read_text())
        self.interfaces = interfaces
        return interfaces

    def _get_bgp_rib_all_vrfs(self) -> Sequence[NxosBgpRoute]:
        """Parses and returns the BGP rib for all VRFs."""

        default_bgp_routes_path = self.device_path / "show_ip_bgp_vrf_all.txt"
        if not default_bgp_routes_path.is_file():
            return []

        file_text = default_bgp_routes_path.read_text()
        if not file_text.strip():
            return []

        return parse_show_ip_bgp_all(file_text)

    @staticmethod
    def compute_protocol_cost(
        nxos_protocol: Text, batfish_protocol: Text
    ) -> List[Tuple[str, float]]:
        """Computes the cost related to protocol differences in Main RIB."""
        batfish_protocol = batfish_protocol
        if nxos_protocol == batfish_protocol:
            return []

        if nxos_protocol == "direct" and batfish_protocol == "connected":
            return []

        if nxos_protocol == "bgp" and batfish_protocol == "aggregate":
            # In Main RIB, NX-OS just says BGP, not aggregate.
            return []

        if nxos_protocol in {"bgp", "ibgp"} and batfish_protocol in {"ibgp", "bgp"}:
            # Not equal, so one is ebgp and one is ibgp
            return [("bgp subtype", 1.0)]

        ospf_sub_types = {"ospf", "ospfE1", "ospfE2", "ospfIA"}
        if nxos_protocol in ospf_sub_types and batfish_protocol in ospf_sub_types:
            return [("ospf subtype", 1.0)]

        # Protocols are incompatible.
        return [("protocol", math.inf)]

    @staticmethod
    def compute_bgp_protocol_cost(
        nxos_protocol: Text, batfish_protocol: Text
    ) -> List[Tuple[str, float]]:
        """Computes the cost related to protocol differences in BGP RIB."""
        batfish_protocol = batfish_protocol
        if nxos_protocol == batfish_protocol:
            return []

        if nxos_protocol == "bgp_aggregate" and batfish_protocol == "aggregate":
            # In BGP RIB, NX-OS indicates aggregate.
            return []

        return [("bgp subtype", 1.0)]

    @staticmethod
    def compute_next_hop_cost(
        nxos_route: NxosMainRibRoute, next_hop: NextHop
    ) -> List[Tuple[str, float]]:
        """Computes the cost related to next hops."""
        if isinstance(next_hop, NextHopVtep):
            # We judge if nxos_route is learned via EVPN using the evpn field
            if not nxos_route.evpn:
                return [("asymmetric vtep", 10.0)]
            ret = []
            if nxos_route.segid != next_hop.vni:
                ret.append(("vni", 1.0))
            if nxos_route.tunnelid != next_hop.vtep:
                ret.append(("vtep", 1.0))
            return ret
        elif nxos_route.evpn:
            return [("asymmetric vtep", 10.0)]

        if isinstance(next_hop, NextHopDiscard):
            if nxos_route.next_hop_int == "Null0":
                return []
            return [("asymmetric null route", 10.0)]
        elif nxos_route.next_hop_int == "Null0":
            return [("asymmetric null route", 10.0)]

        if isinstance(next_hop, NextHopIp):
            if nxos_route.next_hop_ip != next_hop.ip:
                return [("nhip", 1.0)]
            if nxos_route.protocol == "static" and nxos_route.next_hop_int is not None:
                # NX-OS does not put resolved interface, so if it has one then Batfish messed up.
                return [("asymmetric nhint", 5.0)]
            return []

        if isinstance(next_hop, NextHopInterface):
            ret = []
            if nxos_route.next_hop_int is None:
                ret.append(("asymmetric nhint", 5.0))
            elif next_hop.interface.lower() != nxos_route.next_hop_int.lower():
                ret.append(("nhint", 5.0))
            if next_hop.ip is not None and next_hop.ip != nxos_route.next_hop_ip:
                ret.append(("nhip", 1.0))
            return ret

        raise ValueError("Unsupported next hop " + repr(next_hop))
