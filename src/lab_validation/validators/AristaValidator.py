import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from pybatfish.datamodel import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
    NextHopVtep,
)

from lab_validation.parsers.arista.commands.bgp_routes import (
    parse_show_ip_bgp_vrf_all_json,
)
from lab_validation.parsers.arista.commands.evpn_routes import parse_show_bgp_evpn_json
from lab_validation.parsers.arista.commands.interfaces import parse_show_interfaces_json
from lab_validation.parsers.arista.commands.routes import (
    parse_show_ip_route_vrf_all_json,
)
from lab_validation.parsers.arista.models.interfaces import AristaInterface
from lab_validation.parsers.arista.models.routes import (
    AristaBgpRoute,
    AristaEvpnRoute,
    AristaIpRoute,
)

from .batfish_models.interface_properties import InterfaceProperties
from .batfish_models.routes import BgpRibRoute, EvpnRibRoute, MainRibRoute
from .batfish_models.runtime_data import InterfaceRuntimeData, NodeRuntimeData
from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class AristaValidator(VendorValidator):
    SHOW_ROUTE_FILENAME = "show_ip_route_vrf_all__|_json.txt"
    SHOW_ROUTE_FILENAME_TXT = "show_ip_route_vrf_all__|_json.json"
    SHOW_BGP_ROUTE_FILENAME = "show_ip_bgp_vrf_all_|_json.txt"
    SHOW_BGP_ROUTE_FILENAME_TXT = "show_ip_bgp_vrf_all_|_json.json"
    SHOW_INTERFACES_FILENAME = "show_interfaces_|_json.txt"
    SHOW_INTERFACES_FILENAME_TXT = "show_interfaces_|_json.json"
    SHOW_EVPN_FILENAME = "show_bgp_evpn_|_json.txt"
    SHOW_EVPN_FILENAME_TXT = "show_bgp_evpn_|_json.json"

    def __init__(self, device_path: Union[str, Path]) -> None:
        self.device_path = Path(device_path)

    def get_runtime_data(self) -> NodeRuntimeData:
        interfaces = self._parse_interfaces()
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=iface.bandwidth, lineUp=iface.line, speed=None
                )
                for iface in interfaces
            }
        )

    def validate_main_rib_routes(
        self, routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        return self._validate_main_rib_routes(self._parse_routes(), routes)

    def validate_bgp_rib_routes(
        self, bgp_routes: Sequence[BgpRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        return AristaValidator._validate_bgp_rib_routes(
            self._parse_bgp_routes(), bgp_routes
        )

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        return AristaValidator._compare_all_interfaces(
            self._parse_interfaces(), batfish_interfaces
        )

    def validate_evpn_rib_routes(
        self, evpn_routes: Sequence[EvpnRibRoute]
    ) -> Dict[Any, Any]:
        return self._validate_evpn_rib_routes(self._parse_evpn_routes(), evpn_routes)

    def _validate_main_rib_routes(
        self,
        arista_routes: Sequence[AristaIpRoute],
        batfish_routes: Sequence[MainRibRoute],
    ) -> Dict[Any, Any]:
        validate_routes = [
            r
            for r in arista_routes
            # skip connected route management interface
            if r.next_hop_int is None or not r.next_hop_int.startswith("Management")
        ]

        matched_routes = match_pairs(
            validate_routes,
            batfish_routes,
            AristaValidator._diff_routes_cost,
        )

        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _diff_routes_cost(
        arista_route: AristaIpRoute,
        batfish_route: MainRibRoute,
    ) -> List[Tuple[str, float]]:
        if arista_route.network != batfish_route.network:
            return [("network", math.inf)]
        if arista_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []

        arista_protocol: str = arista_route.protocol.lower()
        cost += AristaValidator.compute_protocol_cost(
            arista_protocol, batfish_route.protocol
        )
        cost += AristaValidator.compute_next_hop_cost(
            arista_route, batfish_route.next_hop
        )

        arista_preference = arista_route.preference
        if arista_preference is None:
            if arista_protocol == "connected":
                arista_preference = 0
            if arista_protocol == "static":
                arista_preference = 1
            if arista_protocol == "bgpaggregate":
                # local BGP route admin distance
                arista_preference = 200

        if arista_preference != batfish_route.admin:
            cost.append(("admin", 2.0))

        arista_metric = 0 if arista_route.metric is None else arista_route.metric
        if arista_metric != batfish_route.metric:
            cost.append(("metric", 1.0))

        return cost

    @staticmethod
    def compute_protocol_cost(
        arista_protocol: str, batfish_protocol: str
    ) -> List[Tuple[str, float]]:
        """Computes the cost related to protocol differences in Main RIB."""
        if arista_protocol == batfish_protocol:
            return []

        if arista_protocol == "ebgp" and batfish_protocol == "bgp":
            return []

        if arista_protocol == "bgpaggregate" and batfish_protocol == "aggregate":
            return []

        if "bgp" in arista_protocol and "bgp" in batfish_protocol:
            # One is ebgp and another is ibgp
            return [("bgp subtype", 1.0)]

        if arista_protocol.startswith("ospf") and batfish_protocol.startswith("ospf"):
            return [("ospf subtype", 1.0)]

        # Protocols are incompatible.
        return [("protocol", math.inf)]

    @staticmethod
    def compute_next_hop_cost(
        arista_route: AristaIpRoute, next_hop: NextHop
    ) -> List[Tuple[str, float]]:
        """Computes the cost related to next hops."""
        if isinstance(next_hop, NextHopVtep):
            if not arista_route.vni or not arista_route.vtep_ip:
                return [("asymmetric vtep", 10.0)]
            cost = []
            if arista_route.vni != next_hop.vni:
                cost.append(("vni", 1.0))
            if arista_route.vtep_ip != next_hop.vtep:
                cost.append(("vtep", 1.0))
            return cost
        elif arista_route.vni or arista_route.vtep_ip:
            return [("asymmetric vtep", 10.0)]

        if arista_route.next_hop_int == "Null0" and isinstance(
            next_hop, NextHopDiscard
        ):
            return []
        if arista_route.next_hop_int == "Null0" or isinstance(next_hop, NextHopDiscard):
            # Only one null routed
            return [("asymmetric null route", 10.0)]

        if isinstance(next_hop, NextHopIp):
            if arista_route.protocol == "static":
                # For IP-only static routes, Arista's nhip is fully resolved. Batfish does not.
                return []
            if arista_route.next_hop_ip == next_hop.ip:
                return []
            return [("nhip", 1.0)]

        if isinstance(next_hop, NextHopInterface):
            cost = []
            if not arista_route.next_hop_int:
                cost.append(("asymmetric nhint", 5.0))
            elif arista_route.next_hop_int.lower() != next_hop.interface.lower():
                cost.append(("nhint", 5.0))
            if next_hop.ip and next_hop.ip != arista_route.next_hop_ip:
                cost.append(("nhip", 1.0))
            return cost

        raise ValueError("Unsupported next hop " + repr(next_hop))

    @staticmethod
    def _next_hop_int_compatible(
        arista_nhint: Optional[str], batfish_nhint: str, batfish_protocol: str
    ) -> bool:
        """Returns true if the next-hop interfaces for Arista and Batfish routes are compatible."""
        if arista_nhint is None:
            return batfish_nhint == "dynamic"

        # skip next hop interfaces that need resolution
        if batfish_protocol == "static" and batfish_nhint == "dynamic":
            return True

        assert batfish_nhint is not None
        return bool(arista_nhint.lower() == batfish_nhint.lower())

    def _first_file(self, json_filename: str, txt_filename: str) -> Path:
        """Returns the path of the first file that exists."""
        json_path = self.device_path / json_filename
        txt_path = self.device_path / txt_filename
        return json_path if json_path.is_file() else txt_path

    def _parse_routes(self) -> Sequence[AristaIpRoute]:
        show_route_path = self._first_file(
            AristaValidator.SHOW_ROUTE_FILENAME, AristaValidator.SHOW_ROUTE_FILENAME_TXT
        )

        if not show_route_path.is_file():
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_ip_route_vrf_all_json(routes_text)

    def _parse_bgp_routes(self) -> Sequence[AristaBgpRoute]:
        show_bgp_route_path = self._first_file(
            AristaValidator.SHOW_BGP_ROUTE_FILENAME,
            AristaValidator.SHOW_BGP_ROUTE_FILENAME_TXT,
        )

        if not show_bgp_route_path.is_file():
            return []

        with open(show_bgp_route_path) as fp:
            routes_text = fp.read()
        return parse_show_ip_bgp_vrf_all_json(routes_text)

    @staticmethod
    def _validate_bgp_rib_routes(
        arista_routes: Sequence[AristaBgpRoute],
        batfish_routes: Sequence[BgpRibRoute],
    ) -> Dict[Any, Any]:
        # For now, drop non-best-path routes.
        validate_routes = [
            r for r in arista_routes if AristaValidator.is_best_bgp_route(r)
        ]

        matched_routes = match_pairs(
            validate_routes,
            batfish_routes,
            AristaValidator._diff_bgp_routes_cost,
        )

        return matched_pairs_to_failures(matched_routes)

    # visible for testing
    @staticmethod
    def is_best_bgp_route(r: AristaBgpRoute) -> bool:
        # In presence of ECMP, Arista marks only one as active and others as ecmp
        # routeBestInactive is equivalent to Cisco's RIB failure: this is the best
        # BGP route, but there's a better main RIB route.
        return r.is_active or r.is_ecmp or r.not_installed_reason == "routeBestInactive"

    @staticmethod
    def _diff_bgp_routes_cost(
        arista_route: AristaBgpRoute,
        batfish_route: BgpRibRoute,
    ) -> List[Tuple[str, float]]:
        if arista_route.network != batfish_route.network:
            return [("network", math.inf)]
        if arista_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []

        # AristaBgpRoute currently doesn't have information on whether the route is iBGP or eBGP or the origin_protocol
        # https://github.com/batfish/lab-validation/issues/62

        if arista_route.next_hop_ip != batfish_route.next_hop_ip:
            if (
                arista_route.next_hop_ip is None
                and batfish_route.next_hop_ip == "AUTO/NONE(-1l)"
                and batfish_route.next_hop_int == "null_interface"
            ):
                pass
            else:
                cost.append(("nhip", 1.0))

        arista_metric = 0 if arista_route.metric is None else arista_route.metric
        if batfish_route.metric != arista_metric:
            cost.append(("metric", 1.0))

        arista_local_pref = (
            arista_route.local_preference
            if arista_route.local_preference is not None
            else 0
        )
        if batfish_route.local_preference != arista_local_pref:
            cost.append(("local preference", 1.0))

        if batfish_route.weight != arista_route.weight:
            cost.append(("weight", 1.0))

        if batfish_route.as_path != arista_route.as_path:
            cost.append(("as path", 1.0))

        return cost

    def _parse_interfaces(self) -> Sequence[AristaInterface]:
        show_interfaces_path = self._first_file(
            AristaValidator.SHOW_INTERFACES_FILENAME,
            AristaValidator.SHOW_INTERFACES_FILENAME_TXT,
        )

        if not show_interfaces_path.is_file():
            return []

        with open(show_interfaces_path) as fp:
            interfaces_text = fp.read()
        return parse_show_interfaces_json(interfaces_text)

    @staticmethod
    def _compare_all_interfaces(
        arista_interfaces: Sequence[AristaInterface],
        batfish_interfaces: Sequence[InterfaceProperties],
    ) -> Dict[Any, Any]:
        diffs: Dict[Any, Any] = {}
        batfish_index = {i.name.lower(): i for i in batfish_interfaces}
        real_index = {i.name.lower(): i for i in arista_interfaces}
        for name in batfish_index.keys() - real_index.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"
        for name, arista_if in real_index.items():
            # excluding below interfaces & reasons
            # vxlan: Batfish does not create this interface
            # management: Batfish deactivates mgmt interface
            # Todo: To identify dynamic vlan interfaces, we need `show vlan` output
            # vlan: vxlan L3VNI creates dynamic VLAN interfaces that Batfish does not create

            exclude_iface = ("vxlan", "vlan", "management")
            if name.lower().startswith(exclude_iface):
                continue
            if name not in batfish_index:
                diffs[name] = f"Missing interface in Batfish: {arista_if}"
                continue
            diff = AristaValidator._compare_interface(arista_if, batfish_index[name])
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _compare_interface(
        arista_interface: AristaInterface, batfish_if: InterfaceProperties
    ) -> Dict[str, str]:
        diff = {}

        if batfish_if.active != arista_interface.line:
            diff[
                "active"
            ] = f"Batfish: {batfish_if.active}, Arista: {arista_interface.line}"

        # bandwidth reported in GNS3 for Arista is not accurate, so we ignore it
        # arista_bw = arista_interface.bandwidth
        # if batfish_if.bandwidth != arista_bw:
        #     diff["bandwidth"] = f"Batfish: {batfish_if.bandwidth}, Arista: {arista_bw}"

        # Ignoring MTU as Batfish does not model it correctly
        # if batfish_if.mtu != arista_interface.mtu:
        #     diff["mtu"] = f"Batfish: {batfish_if.mtu}, Arista: {arista_interface.mtu}"

        return diff

    def _parse_evpn_routes(self) -> Sequence[AristaEvpnRoute]:
        show_evpn_route_path = self._first_file(
            AristaValidator.SHOW_EVPN_FILENAME, AristaValidator.SHOW_EVPN_FILENAME_TXT
        )

        if not show_evpn_route_path.is_file():
            return []

        with open(show_evpn_route_path) as fp:
            text = fp.read()
        return parse_show_bgp_evpn_json(text)

    def _validate_evpn_rib_routes(
        self,
        arista_routes: Sequence[AristaEvpnRoute],
        batfish_routes: Sequence[EvpnRibRoute],
    ) -> Dict[Any, Any]:
        validate_routes = [r for r in arista_routes if r.is_active]

        matched_routes = match_pairs(
            validate_routes,
            batfish_routes,
            AristaValidator._diff_evpn_routes_cost,
        )

        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _diff_evpn_routes_cost(
        arista_route: AristaEvpnRoute,
        batfish_route: EvpnRibRoute,
    ) -> List[Tuple[str, float]]:
        if arista_route.network != batfish_route.network:
            return [("network", math.inf)]
        if arista_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]
        if batfish_route.route_distinguisher != arista_route.route_distinguisher:
            return [("route_distinguisher", math.inf)]

        cost = []

        if batfish_route.next_hop_ip != arista_route.next_hop_ip:
            if (
                arista_route.next_hop_ip is None
                and batfish_route.next_hop_ip == "AUTO/NONE(-1l)"
                and batfish_route.next_hop_int == "null_interface"
            ):
                pass
            else:
                cost.append(("next_hop_ip", 10.0))

        arista_local_pref = (
            arista_route.local_preference
            if arista_route.local_preference is not None
            else 0
        )
        if batfish_route.local_preference != arista_local_pref:
            cost.append(("local_preference", 1.0))

        if batfish_route.as_path != arista_route.as_path:
            cost.append(("as_path", 1.0))

        if batfish_route.origin_type.lower() != arista_route.origin.lower():
            cost.append(("origin_type", 1.0))

        return cost
