import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pybatfish.datamodel import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
    NextHopVrf,
)

from lab_validation.parsers.iosxr.commands.interfaces import parse_show_interfaces
from lab_validation.parsers.iosxr.commands.route import (
    parse_show_route,
    parse_show_route_vrf_all,
)
from lab_validation.parsers.iosxr.commands.show_bgp_all_all import (
    parse_show_bgp_all_all,
)
from lab_validation.parsers.iosxr.models.bgp import IosXrBgpRoute
from lab_validation.parsers.iosxr.models.interfaces import IosXrInterface
from lab_validation.parsers.iosxr.models.routes import IosXrRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import (
    match_pairs,
    matched_pairs_to_failures,
    preprocess_batfish_bgp_route,
)
from .vendor_validator import VendorValidator

IGNORED_IFACE_PATTERNS = (
    re.compile(r"null\d+", re.IGNORECASE),
    re.compile(r"mgmteth\d+.*", re.IGNORECASE),
)

LOOPBACK_IFACE_PATTERN = re.compile(r"loopback\d+", re.IGNORECASE)


class IosXrValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path
        # Parsing interfaces show data is dang slow; cache them.
        self.interfaces: list[IosXrInterface] | None = None

    def get_runtime_data(self) -> NodeRuntimeData:
        interfaces = self._get_interfaces()
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=iface.bw, lineUp=iface.line_protocol == "up", speed=None
                )
                for iface in interfaces
                if iface.is_physical()
            }
        )

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        real_routes: Sequence[IosXrRoute] = self._get_main_rib_all_vrfs()

        return IosXrValidator._validate_main_rib_routes(batfish_routes, real_routes)

    def _get_main_rib_all_vrfs(self) -> Sequence[IosXrRoute]:
        """Parses and returns the main rib for all VRFs."""
        default_vrf_routes_path = self.device_path / "show_route.txt"
        assert default_vrf_routes_path.is_file()
        non_default_vrf_routes_path = self.device_path / "show_route_vrf_all.txt"
        assert non_default_vrf_routes_path.is_file()

        default_vrf_routes = parse_show_route(default_vrf_routes_path.read_text())
        non_default_vrf_routes = parse_show_route_vrf_all(
            non_default_vrf_routes_path.read_text()
        )
        return list(default_vrf_routes) + list(non_default_vrf_routes)

    @staticmethod
    def _validate_main_rib_routes(
        batfish_routes: Sequence[MainRibRoute], real_routes: Sequence[IosXrRoute]
    ) -> dict[Any, Any]:
        # Drop routes with next hop to a mgmt interface and backup routes
        real_routes = [
            r
            for r in real_routes
            if r.next_hop_int is None
            or not r.next_hop_int.startswith("Mgmt")
            or r.backup
        ]

        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            IosXrValidator._diff_routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    @staticmethod
    def _diff_routes_cost(
        xr_route: IosXrRoute, batfish_route: MainRibRoute
    ) -> list[tuple[str, float]]:
        if xr_route.network != batfish_route.network:
            return [("network", math.inf)]
        if xr_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []
        cost += IosXrValidator.compute_protocol_cost(
            xr_route.protocol,
            batfish_route.protocol,
        )

        cost += IosXrValidator.compute_next_hop_cost(xr_route, batfish_route.next_hop)

        # TODO: test that batfish_route.next_hop_vrf matches when Batfish provides it
        xr_route_is_vrf_leaked_interface_route = (
            xr_route.next_hop_vrf is not None
            and xr_route.protocol == "bgp"
            and xr_route.next_hop_int is not None
        )

        if xr_route.metric != batfish_route.metric:
            if xr_route.protocol == "ospfIS" or xr_route_is_vrf_leaked_interface_route:
                # IOS XR doesn't put metric in the show output for these routes.
                pass
            else:
                cost.append(("metric", 1.0))
        if xr_route.admin != batfish_route.admin:
            if xr_route.protocol == "ospfIS" or xr_route_is_vrf_leaked_interface_route:
                # IOS XR doesn't put AD in the show output for these routes.
                pass
            else:
                cost.append(("admin", 1.0))

        return cost

    @staticmethod
    def compute_protocol_cost(
        xr_protocol: str, batfish_protocol: str
    ) -> list[tuple[str, float]]:
        """
        Computes the protocol cost, given that they are not equal.
        Return [], when ios xr is bgp and batfish is bgp sub-types as ios xr does not provide bgp sub-type info.
        Return ["ospf subtype", 1.0], when protocols are from ospf sub-types.
        Return ["protocol", math.inf], when they are totally different protocols. Examples bgp & ospf, ospf & eigrp etc...
        """
        if xr_protocol == batfish_protocol:
            return []

        if xr_protocol == "local" and batfish_protocol in {"local", "connected"}:
            return []

        # Batfish reports generated routes as aggregate routes
        if batfish_protocol == "aggregate" and xr_protocol == "bgp":
            return []

        # IOS does not provide granular(IBGP/EBGP) info. IOS will only show `bgp`, while Batfish will say IBGP.
        if xr_protocol == "bgp" and batfish_protocol in {"ibgp", "bgp"}:
            return []

        # Both IOS and Batfish model OSPF subtype. So if they disagree, return 1.
        ospf_sub_types = {"ospf", "ospfE1", "ospfE2", "ospfIA"}
        if xr_protocol in ospf_sub_types and batfish_protocol in ospf_sub_types:
            return [("ospf subtype", 1.0)]

        # Both IOS and Batfish model EIGRP subtype. So if they disagree, return 1.
        eigrp_sub_types = {"eigrp", "eigrpEX"}
        if xr_protocol in eigrp_sub_types and batfish_protocol in eigrp_sub_types:
            return [("eigrp subtype", 1.0)]

        # Protocols are completely different. (TODO: update when we have labs with other protocols that have subtypes)
        return [("protocol", math.inf)]

    @staticmethod
    def compute_next_hop_cost(
        xr_route: IosXrRoute, next_hop: NextHop
    ) -> list[tuple[str, float]]:
        """Computes cost related to next hops."""
        if isinstance(next_hop, NextHopVrf):
            if xr_route.next_hop_vrf != next_hop.vrf:
                return [("vrf leak mismatch", 10.0)]
            return []
        elif xr_route.next_hop_vrf:
            return [("vrf leak mismatch", 10.0)]

        if xr_route.next_hop_int == "Null0" and isinstance(next_hop, NextHopDiscard):
            return []
        if xr_route.next_hop_int == "Null0" or isinstance(next_hop, NextHopDiscard):
            # Only one null routed
            return [("asymmetric null route", 10.0)]

        if isinstance(next_hop, NextHopIp):
            cost = []
            if xr_route.next_hop_ip != next_hop.ip:
                cost.append(("nhip", 1.0))
            if xr_route.protocol == "static" and xr_route.next_hop_int:
                # IOS-XR static routes only include next hop interface when configured
                cost.append(("asymmetric nhint", 5.0))
            return cost

        if isinstance(next_hop, NextHopInterface):
            cost = []
            if xr_route.next_hop_int is None:
                # Batfish should not have an interface if IOS-XR doesn't
                cost.append(("asymmetric nhint", 5.0))
            elif xr_route.next_hop_int.lower() != next_hop.interface.lower():
                cost.append(("nhint", 5.0))
            if next_hop.ip is not None and xr_route.next_hop_ip != next_hop.ip:
                cost.append(("nhip", 1.0))
            return cost

        raise ValueError("Unsupported next hop " + repr(next_hop))

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        # IosXrBgpRoute doesn't contain its VRF; the tuples in real_routes are (vrf, route)
        real_routes: list[tuple[str, IosXrBgpRoute]] = self._get_bgp_rib_all_vrfs()
        matched_routes = match_pairs(
            real_routes,
            list(map(preprocess_batfish_bgp_route, batfish_routes)),
            IosXrValidator._diff_bgp_routes_cost,
        )
        # Post-process differences to eliminate expected differences:
        # 1. Routes that appear to have been leaked from another VRF and only differ in next hop info; in
        #    Batfish leaked routes have next VRF instead of NHIP or next hop interface
        # TODO This step should not be necessary once we account for next VRF info in compute_bgp_nexthop_cost.
        post_processed_matched_routes = [
            diff
            for diff in matched_routes
            if IosXrValidator.difference_matters(diff, real_routes)
        ]
        return matched_pairs_to_failures(post_processed_matched_routes)

    @staticmethod
    def difference_matters(
        difference: tuple[tuple[str, IosXrBgpRoute] | None, BgpRibRoute | None, Any],
        show_routes: Sequence[tuple[str, IosXrBgpRoute]],
    ) -> bool:
        """Checks if a difference produced by match_pairs really indicates an inconsistency between Batfish and show
        data. By default, differences matter, but need to weed out differences in VRF-leaked routes.

         :param difference: One route difference from the output of match_pairs, in the form of a tuple of
                (xr_route, bf_route, cost). Indicates an extra Batfish route if xr_route is None, or missing Batfish
                route if bf_route is None (both can't be None).
         :param show_routes: All routes in the BGP show data, in the form of tuples of (vrf_name, route)
        """
        xr_tuple, bf, unused_cost = difference
        if (
            # Check that the only difference is next hop
            xr_tuple is not None
            and bf is not None
            and IosXrValidator.could_have_been_leaked(xr_tuple, show_routes)
            # Check that both routes look like they could have been leaked from another VRF
            and bf.next_hop_ip is None
            and bf.next_hop_int == "dynamic"
        ):
            # TODO: add next VRF to BgpRibRoute so that these differences can be ignored in compute_bgp_nexthop_cost.
            return False
        return True

    @staticmethod
    def could_have_been_leaked(
        xr_route_tuple: tuple[str, IosXrBgpRoute],
        show_routes: Sequence[tuple[str, IosXrBgpRoute]],
    ) -> bool:
        route_vrf = xr_route_tuple[0]
        route = xr_route_tuple[1]
        for vrf, r in show_routes:
            if vrf != route_vrf and r == route:
                return True
        return False

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> dict[Any, Any]:
        """Validating interfaces"""
        xr_ifaces = self._get_interfaces()
        diffs: dict[Any, Any] = {}

        batfish_ifaces = {i.name.lower(): i for i in batfish_interfaces}
        real_ifaces = {i.name.lower(): i for i in xr_ifaces}

        for name in batfish_ifaces.keys() - real_ifaces.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_ifaces[name]}"
        for name, iface in real_ifaces.items():
            # Skip things like management ifaces
            if any(p.match(name) for p in IGNORED_IFACE_PATTERNS):
                continue
            if name not in batfish_ifaces:
                diffs[name] = f"Missing interface in Batfish: {iface}"
                continue
            diff = self._compare_interfaces(iface, batfish_ifaces[name])
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _compare_interfaces(
        iface: IosXrInterface,
        bf_iface: InterfaceProperties,
    ) -> dict[str, str]:
        diff = {}

        xr_active = iface.admin_state == "up"
        if bf_iface.active != xr_active:
            diff["active"] = (
                f"Batfish: {bf_iface.active}, IOS XR: status={iface.admin_state}"
            )

        if LOOPBACK_IFACE_PATTERN.match(iface.name):
            # Loopbacks don't have bandwidth on XR, so don't check those
            pass
        elif not xr_active and iface.name.startswith("Bundle-Ether"):
            # XR forces bandwidth to 0 on inactive interfaces, ignore that
            pass
        else:
            # Batfish reports bps, XR uses kbps
            xr_bw_bps = iface.bw * 1000
            if bf_iface.bandwidth != xr_bw_bps:
                diff["bandwidth"] = (
                    f"Batfish: {bf_iface.bandwidth}, IOS XR: {xr_bw_bps}"
                )

        # TODO: compare primary address instead of all prefixes
        if iface.prefix and iface.prefix not in bf_iface.all_prefixes:
            diff["ipv4 address"] = (
                f"Batfish: {bf_iface.all_prefixes}, IOS XR: {iface.prefix}"
            )

        # TODO: Ignoring MTU as Batfish does not model it correctly
        # See https://github.com/batfish/batfish/issues/3437 and https://github.com/batfish/batfish/issues/5119
        # if bf_iface.mtu != iface.mtu:
        #     diff["mtu"] = f"Batfish: {bf_iface.mtu}, IOS XR: {iface.mtu}"

        return diff

    def _get_bgp_rib_all_vrfs(self) -> list[tuple[str, IosXrBgpRoute]]:
        """Parses and returns the BGP rib for all VRFs."""

        bgp_path = self.device_path / "show_bgp_all_all.txt"
        assert bgp_path.is_file()

        text = bgp_path.read_text()
        bgp_afs = parse_show_bgp_all_all(text)
        ret: list[tuple[str, IosXrBgpRoute]] = []
        for af in bgp_afs:
            if af.name not in ["IPv4 Unicast", "VPNv4 Unicast"]:
                continue
            for v in af.vrfs:
                for r in v.routes:
                    if r.best_path:  # Batfish only has best-path routes
                        ret.append((v.name, r))
        return ret

    def _get_interfaces(self) -> list[IosXrInterface]:
        if self.interfaces is not None:
            return self.interfaces

        if_file = self.device_path / "show_interfaces.txt"
        self.interfaces = parse_show_interfaces(if_file.read_text())
        return self.interfaces

    @staticmethod
    def is_local_route(r: IosXrBgpRoute) -> bool:
        return r.weight == 32768 and r.next_hop_ip == "0.0.0.0"

    @staticmethod
    def _diff_bgp_routes_cost(
        expected_route_and_vrf: tuple[str, IosXrBgpRoute], batfish_route: BgpRibRoute
    ) -> list[tuple[str, float]]:
        # return infinite cost if vrf or network subnet does not match
        expected_vrf = expected_route_and_vrf[0]
        if expected_vrf != batfish_route.vrf:
            return [("vrf", math.inf)]
        expected_route = expected_route_and_vrf[1]
        if expected_route.network != batfish_route.network:
            return [("network", math.inf)]

        cost = []

        expected_metric = 0 if expected_route.metric is None else expected_route.metric
        if expected_metric != batfish_route.metric:
            cost.append(("metric", 1.0))

        if expected_route.local_preference != batfish_route.local_preference:
            cost.append(("local preference", 1.0))

        if expected_route.weight != batfish_route.weight:
            cost.append(("weight", 1.0))

        if expected_route.as_path != batfish_route.as_path:
            # TODO Better AS path comparison
            cost.append(("as path", 1.0))

        if not IosXrValidator._bgp_origin_type_compatible(
            batfish_route.origin_type, expected_route.origin_type
        ):
            cost.append(("origin type", 1.0))

        cost += IosXrValidator.compute_bgp_nexthop_cost(expected_route, batfish_route)

        return cost

    @staticmethod
    def compute_bgp_nexthop_cost(
        expected_route: IosXrBgpRoute, batfish_route: BgpRibRoute
    ) -> list[tuple[str, float]]:
        if (
            batfish_route.next_hop_ip is None
            and batfish_route.next_hop_int == "null_interface"
            and IosXrValidator.is_local_route(expected_route)
        ):
            # This is a local route.
            return []
        if (
            expected_route.next_hop_ip is None
            or batfish_route.next_hop_int == "null_interface"
        ):
            # TODO: handle null route. Currently no XR labs have null-routed BGP routes
            return [("nhip/null", 1.0)]

        # TODO Can BGP routes in show data have next hop interfaces?
        return (
            []
            if expected_route.next_hop_ip == batfish_route.next_hop_ip
            else [("nhip", 1.0)]
        )

    @staticmethod
    def _bgp_origin_type_compatible(bf: str, xr: str) -> bool:
        if bf == "igp":
            return xr == "i"
        elif bf == "egp":
            return xr == "e"
        assert bf == "incomplete"
        return xr == "?"
