import math
from pathlib import Path
from typing import (
    AbstractSet,
    Any,
    DefaultDict,
    Dict,
    List,
    MutableSet,
    Optional,
    Sequence,
    Text,
    Tuple,
)

from pybatfish.datamodel import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
    NextHopVrf,
)

from lab_validation.parsers.ios.commands.interfaces import parse_show_interfaces
from lab_validation.parsers.ios.commands.route import parse_show_ip_route
from lab_validation.parsers.ios.commands.show_bgp_all import parse_show_bgp_all
from lab_validation.parsers.ios.commands.vrf import parse_show_vrf
from lab_validation.parsers.ios.models.bgp import IosBgpRoute
from lab_validation.parsers.ios.models.routes import IosIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .utils.validation_utils import match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class IosValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()

    def validate_bgp_rib_routes(self, routes: Sequence[BgpRibRoute]) -> Dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        return IosValidator._compare_all_bgp_rib_routes(
            self._get_bgp_rib_all_vrfs(), routes
        )

    @staticmethod
    def _compare_all_bgp_rib_routes(
        expected_routes: Sequence[Tuple[Text, IosBgpRoute]],
        bf_routes: Sequence[BgpRibRoute],
    ) -> Dict[Any, Any]:
        matched_routes = match_pairs(
            expected_routes,
            bf_routes,
            IosValidator._diff_bgp_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        if_file = self.device_path / "show_interfaces.txt"
        ios_interfaces = parse_show_interfaces(if_file.read_text())

        diffs: Dict[Any, Any] = {}
        batfish_index = {i.name: i for i in batfish_interfaces}
        real_ifnames = ios_interfaces.keys()
        for name in batfish_index.keys() - real_ifnames:
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"
        for name, ios_if in ios_interfaces.items():
            batfish_if = batfish_index.get(name)
            if batfish_if is None:
                diffs[name] = f"Missing interface in Batfish: {ios_interfaces[name]}"
                continue
            if batfish_if.vrf == "management":
                continue
            diff = IosValidator._compare_interfaces(ios_if, batfish_if)
            if diff:
                diffs[name] = diff
        return diffs

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        real_routes: Sequence[IosIpRoute] = self._get_main_rib_all_vrfs()
        # excluding "management routes"
        real_routes = [route for route in real_routes if route.vrf != "management"]
        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            IosValidator._diff_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _compare_interfaces(
        ios_interface: Dict[str, Any], batfish_if: InterfaceProperties
    ) -> Dict[Text, Text]:
        diff = {}

        ios_active = ios_interface["enabled"]
        if batfish_if.active != ios_interface["enabled"]:
            diff["active"] = f"Batfish: {batfish_if.active}, IOS: {ios_active}"

        ios_bw = ios_interface["bandwidth"] * 1000
        if batfish_if.bandwidth != ios_bw:
            diff["bandwidth"] = f"Batfish: {batfish_if.bandwidth}, IOS: {ios_bw}"

        ios_speed = ios_interface.get("port_speed", None)
        if batfish_if.speed != ios_speed:
            if ios_speed is not None:
                # IOS may not include speed data
                diff["speed"] = f"Batfish: {batfish_if.speed}, IOS: {ios_speed}"

        ios_prefixes = list(ios_interface.get("ipv4", {}).keys())
        if batfish_if.all_prefixes != ios_prefixes:
            diff[
                "ipv4 address"
            ] = f"Batfish: {batfish_if.all_prefixes}, IOS: {ios_prefixes}"

        return diff

    @staticmethod
    def _diff_bgp_routes_cost(
        ios_route_and_vrf: Tuple[Text, IosBgpRoute], bf_route: BgpRibRoute
    ) -> float:
        # return infinite cost if vrf or network subnet does not match
        expected_vrf = ios_route_and_vrf[0]
        if expected_vrf != bf_route.vrf:
            return math.inf
        ios_route = ios_route_and_vrf[1]
        if ios_route.network != bf_route.network:
            return math.inf

        cost = 0.0

        if bf_route.metric != ios_route.metric:
            cost += 1.0

        if bf_route.local_preference != ios_route.local_preference:
            cost += 1.0

        if bf_route.weight != ios_route.weight:
            cost += 1.0

        if bf_route.as_path != ios_route.as_path:
            # TODO Better AS path comparison
            cost += 1.0

        if not IosValidator._bgp_origin_type_compatible(
            bf_route.origin_type, ios_route.origin_type
        ):
            cost += 1.0

        cost += IosValidator.compute_bgp_nexthop_cost(ios_route, bf_route.next_hop)

        return cost

    @staticmethod
    def is_local_route(r: IosBgpRoute) -> bool:
        return r.weight == 32768 and r.next_hop_ip == "0.0.0.0"

    @staticmethod
    def compute_bgp_nexthop_cost(ios_route: IosBgpRoute, next_hop: NextHop) -> float:
        if isinstance(next_hop, NextHopDiscard):
            if IosValidator.is_local_route(ios_route):
                return 0.0
            return 10.0

        if isinstance(next_hop, NextHopIp):
            return 0.0 if ios_route.next_hop_ip == next_hop.ip else 1.0

        if isinstance(next_hop, NextHopVrf):
            # It's indistinguishable in IOS show data, trust Batfish.
            # TODO: We simply need to not build labs where the same route is originated in different VRFs.
            return 0.0

        raise ValueError("Unsupported next hop " + repr(next_hop))

    @staticmethod
    def _bgp_origin_type_compatible(bf: Text, ios: Text) -> bool:
        if bf == "igp":
            return bool(ios == "i")
        elif bf == "egp":
            return bool(ios == "e")
        assert bf == "incomplete"
        return bool(ios == "?")

    def _get_main_rib_all_vrfs(self) -> Sequence[IosIpRoute]:
        """Parses and returns the main rib for all VRFs."""

        default_vrf_routes_path = self.device_path / "show_ip_route.txt"
        assert default_vrf_routes_path.is_file()

        all_files = [default_vrf_routes_path]

        vrfs_path = self.device_path / "show_vrf.txt"
        if vrfs_path.is_file():
            vrfs = parse_show_vrf(vrfs_path.read_text())
            all_files.extend(
                self.device_path / f"show_ip_route_vrf_{v.name}.txt" for v in vrfs
            )

        all_vrf_ip_routes: List[IosIpRoute] = []
        for vrf_routes_file in all_files:
            vrf_routes_text = vrf_routes_file.read_text()
            ios_vrf_routes: Sequence[IosIpRoute] = parse_show_ip_route(vrf_routes_text)
            all_vrf_ip_routes += ios_vrf_routes
        return all_vrf_ip_routes

    def _get_bgp_rib_all_vrfs(self) -> Sequence[Tuple[Text, IosBgpRoute]]:
        """Parses and returns the BGP rib for all VRFs."""

        bgp_path = self.device_path / "show_ip_bgp_all.txt"
        assert bgp_path.is_file()

        text = bgp_path.read_text()
        bgp_afs = parse_show_bgp_all(text)
        ret: List[Tuple[Text, IosBgpRoute]] = []
        for af in bgp_afs:
            if af.name not in ["IPv4 Unicast", "VPNv4 Unicast"]:
                continue
            for v in af.vrfs:
                for r in v.routes:
                    if r.best_path:
                        ret.append((v.name, r))
        return ret

    @staticmethod
    def _diff_routes_cost(
        expected_route: IosIpRoute, batfish_route: MainRibRoute
    ) -> float:
        cost = 0.0
        if expected_route.network != batfish_route.network:
            return math.inf
        if expected_route.vrf != batfish_route.vrf:
            return math.inf

        if expected_route.protocol != batfish_route.protocol:
            cost += IosValidator.compute_protocol_cost(
                expected_route.protocol, batfish_route.protocol
            )
        if expected_route.metric != batfish_route.metric:
            if expected_route.protocol == "ospfIS":
                # IOS doesn't put metric in the show output for these routes.
                pass
            else:
                cost += 1.0
        if expected_route.admin != batfish_route.admin:
            if expected_route.protocol == "ospfIS":
                # IOS doesn't put AD in the show output for these routes.
                pass
            else:
                cost += 1.0

        cost += IosValidator._next_hop_cost(expected_route, batfish_route.next_hop)

        return cost

    @staticmethod
    def _next_hop_cost(ios_route: IosIpRoute, next_hop: NextHop) -> float:
        """Returns the cost of the next-hop difference."""
        if isinstance(next_hop, NextHopDiscard):
            if ios_route.next_hop_int == "Null0":
                return 0.0
            # Next-hop mismatch - IOS is not null routed.
            return 10.0
        elif ios_route.next_hop_int == "Null0":
            # Next-hop mismatch - Batfish is not null routed.
            return 10.0

        if isinstance(next_hop, NextHopInterface):
            cost = 0.0
            if (
                ios_route.next_hop_int is None
                or ios_route.next_hop_int.lower() != next_hop.interface.lower()
            ):
                cost += 1.0
            if next_hop.ip is not None and next_hop.ip != ios_route.next_hop_ip:
                cost += 1.0
            return cost

        if isinstance(next_hop, NextHopIp):
            if next_hop.ip != ios_route.next_hop_ip:
                return 1.0
            return 0.0

        if isinstance(next_hop, NextHopVrf):
            if next_hop.vrf != ios_route.vrf:
                return 5.0
            return 0.0

        raise ValueError("Unsupported next hop " + repr(next_hop))

    @staticmethod
    def compute_protocol_cost(ios_protocol: Text, batfish_protocol: Text) -> float:
        """
        Computes the protocol cost, given that they are not equal.
        Return 0, when ios is bgp and batfish is bgp sub-types as ios does provide bgp sub-type info.
        Return 1, when protocols are from ospf sub-types.
        Return math.inf, when they are totally different protocols. Examples bgp & ospf, ospf & eigrp etc...
        :param ios_protocol:
        :param batfish_protocol:
        :return: cost
        """

        # IOS does not provide granular(IBGP/EBGP) info. IOS will only show `bgp`, while Batfish will say IBGP.
        if ios_protocol == "bgp" and batfish_protocol in {"ibgp", "bgp"}:
            return 0.0

        # Both IOS and Batfish model OSPF subtype. So if they disagree, return 1.
        ospf_sub_types = {"ospf", "ospfE1", "ospfE2", "ospfIA"}
        if ios_protocol in ospf_sub_types and batfish_protocol in ospf_sub_types:
            return 1.0

        # Both IOS and Batfish model EIGRP subtype. So if they disagree, return 1.
        eigrp_sub_types = {"eigrp", "eigrpEX"}
        if ios_protocol in eigrp_sub_types and batfish_protocol in eigrp_sub_types:
            return 1.0

        # Protocols are completely different. (TODO: update when we have labs with other protocols that have subtypes)
        return math.inf
