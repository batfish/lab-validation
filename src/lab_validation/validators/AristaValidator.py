import math
from collections.abc import Sequence
from pathlib import Path
from typing import AbstractSet, Any

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
from .utils.validation_utils import CostResult, match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator

# RFC 5549 unnumbered BGP: Arista reports the peer's IPv6 link-local as the
# next-hop (e.g. 'fe80::.../Et1') while Batfish models it with a synthetic
# IPv4 169.254.x.x address paired with the outgoing interface.
_IPV6_LINK_LOCAL_PREFIX = "fe80:"
_IPV4_LINK_LOCAL_PREFIX = "169.254."

# Arista interface name abbreviations used in IPv6 zone identifiers and CLI
# short forms. Used to normalize e.g. 'Et1' into the canonical 'Ethernet1'.
_ARISTA_IFACE_ABBREVIATIONS = {
    "Eth": "Ethernet",
    "Et": "Ethernet",
    "Lo": "Loopback",
    "Ma": "Management",
    "Po": "Port-Channel",
    "Vl": "Vlan",
}


def _canonicalize_arista_interface(name: str) -> str:
    """Expand an abbreviated Arista interface name to its canonical form."""
    for prefix in sorted(_ARISTA_IFACE_ABBREVIATIONS, key=len, reverse=True):
        if (
            name.startswith(prefix)
            and len(name) > len(prefix)
            and not name[len(prefix)].isalpha()
        ):
            return _ARISTA_IFACE_ABBREVIATIONS[prefix] + name[len(prefix) :]
    return name


def _split_ipv6_zone(nhip: str | None) -> tuple[str | None, str | None]:
    """Split an IPv6 address with an optional zone identifier.

    e.g. 'fe80::1%Et1' -> ('fe80::1', 'Ethernet1'); '10.0.0.1' -> ('10.0.0.1', None).
    """
    if nhip is None:
        return (None, None)
    ip, sep, zone = nhip.partition("%")
    if not sep:
        return (ip, None)
    return (ip, _canonicalize_arista_interface(zone))


def _is_rfc5549_unnumbered_match(
    arista_nhip: str | None,
    batfish_nhip: str | None,
) -> bool:
    """Return True if the device's IPv6 link-local next-hop matches Batfish's
    synthetic IPv4 link-local next-hop used for RFC 5549 unnumbered peering."""
    if not arista_nhip or not batfish_nhip:
        return False
    arista_ip, _ = _split_ipv6_zone(arista_nhip)
    return bool(
        arista_ip
        and arista_ip.lower().startswith(_IPV6_LINK_LOCAL_PREFIX)
        and batfish_nhip.startswith(_IPV4_LINK_LOCAL_PREFIX)
    )


class AristaValidator(VendorValidator):
    SHOW_ROUTE_FILENAME = "show_ip_route_vrf_all_|_json.txt"
    SHOW_ROUTE_FILENAME_TXT = "show_ip_route_vrf_all_|_json.json"
    SHOW_BGP_ROUTE_FILENAME = "show_ip_bgp_vrf_all_|_json.txt"
    SHOW_BGP_ROUTE_FILENAME_TXT = "show_ip_bgp_vrf_all_|_json.json"
    SHOW_INTERFACES_FILENAME = "show_interfaces_|_json.txt"
    SHOW_INTERFACES_FILENAME_TXT = "show_interfaces_|_json.json"
    SHOW_EVPN_FILENAME = "show_bgp_evpn_|_json.txt"
    SHOW_EVPN_FILENAME_TXT = "show_bgp_evpn_|_json.json"

    def __init__(self, device_path: str | Path) -> None:
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
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        return self._validate_main_rib_routes(self._parse_routes(), routes)

    def validate_bgp_rib_routes(
        self, bgp_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        return AristaValidator._validate_bgp_rib_routes(
            self._parse_bgp_routes(), bgp_routes
        )

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        return AristaValidator._compare_all_interfaces(
            self._parse_interfaces(), batfish_interfaces
        )

    def validate_evpn_rib_routes(
        self, evpn_routes: Sequence[EvpnRibRoute]
    ) -> dict[Any, Any]:
        return self._validate_evpn_rib_routes(self._parse_evpn_routes(), evpn_routes)

    def _validate_main_rib_routes(
        self,
        arista_routes: Sequence[AristaIpRoute],
        batfish_routes: Sequence[MainRibRoute],
    ) -> dict[Any, Any]:
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
    ) -> CostResult:
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

        # EOS reports directly-connected OSPF neighbor routes (e.g., on unnumbered p2p links)
        # with no preference, metric, or next-hop IP. Skip those comparisons when all are absent.
        _directly_connected = (
            arista_route.preference is None
            and arista_route.metric is None
            and arista_route.next_hop_ip is None
            and arista_protocol == "ospf"
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

        if not _directly_connected and arista_preference != batfish_route.admin:
            cost.append(("admin", 2.0))

        if not _directly_connected:
            arista_metric = 0 if arista_route.metric is None else arista_route.metric
            if arista_metric != batfish_route.metric:
                cost.append(("metric", 1.0))

        return cost

    @staticmethod
    def compute_protocol_cost(
        arista_protocol: str, batfish_protocol: str
    ) -> CostResult:
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
    ) -> CostResult:
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
            if (
                next_hop.ip
                and arista_route.next_hop_ip is not None
                and next_hop.ip != arista_route.next_hop_ip
                and not _is_rfc5549_unnumbered_match(
                    arista_route.next_hop_ip, next_hop.ip
                )
            ):
                cost.append(("nhip", 1.0))
            return cost

        raise ValueError("Unsupported next hop " + repr(next_hop))

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
    ) -> dict[Any, Any]:
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
    ) -> CostResult:
        if arista_route.network != batfish_route.network:
            return [("network", math.inf)]
        if arista_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost = []

        if arista_route.origin_protocol is not None:
            cost += AristaValidator._compute_bgp_protocol_cost(
                arista_route.origin_protocol, batfish_route.protocol
            )

        if arista_route.origin_type != batfish_route.origin_type:
            cost.append(("origin_type", 1.0))

        cost += AristaValidator._compute_bgp_next_hop_cost(
            arista_route, batfish_route.next_hop
        )

        arista_metric = 0 if arista_route.metric is None else arista_route.metric
        if batfish_route.metric != arista_metric:
            cost.append(("metric", 1.0))

        # Arista's "show ip bgp" omits localPreference for locally-
        # originated paths on newer EOS (4.36+ multi-agent), parsed as
        # None. Older EOS (4.23 ribd) reports explicit 0. In both cases
        # the effective local-pref used on iBGP export is the BGP
        # default 100 (see lab-validation#8 and private issue analysis).
        # We treat None (field absent) as 100. Explicit 0 is ambiguous
        # (could be unset-default or route-map-set-to-0) and is left
        # as-is; mismatches from that ambiguity are tracked under #8.
        arista_local_pref = (
            arista_route.local_preference
            if arista_route.local_preference is not None
            else 100
        )
        if batfish_route.local_preference != arista_local_pref:
            cost.append(("local preference", 1.0))

        if batfish_route.weight != arista_route.weight:
            cost.append(("weight", 1.0))

        if batfish_route.as_path != arista_route.as_path:
            cost.append(("as path", 1.0))

        return cost

    @staticmethod
    def _compute_bgp_next_hop_cost(
        arista_route: AristaBgpRoute, next_hop: NextHop
    ) -> CostResult:
        arista_ip, arista_zone = _split_ipv6_zone(arista_route.next_hop_ip)

        if isinstance(next_hop, NextHopDiscard):
            if arista_route.next_hop_ip is None:
                return []
            return [("nhip", 1.0)]

        if isinstance(next_hop, NextHopIp):
            if arista_ip == next_hop.ip:
                return []
            if _is_rfc5549_unnumbered_match(arista_route.next_hop_ip, next_hop.ip):
                return []
            return [("nhip", 1.0)]

        if isinstance(next_hop, NextHopInterface):
            cost: CostResult = []
            if arista_ip != next_hop.ip:
                if not _is_rfc5549_unnumbered_match(
                    arista_route.next_hop_ip, next_hop.ip
                ):
                    cost.append(("nhip", 1.0))
            if arista_zone is not None and next_hop.interface:
                if arista_zone.lower() != next_hop.interface.lower():
                    cost.append(("nhint", 5.0))
            return cost

        if isinstance(next_hop, NextHopVtep):
            if arista_ip == next_hop.vtep:
                return []
            return [("nhip", 1.0)]

        raise ValueError("Unsupported next hop " + repr(next_hop))

    @staticmethod
    def _compute_bgp_protocol_cost(
        arista_protocol: str, batfish_protocol: str
    ) -> CostResult:
        if arista_protocol == batfish_protocol:
            return []
        return [("bgp subtype", 1.0)]

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
    ) -> dict[Any, Any]:
        diffs: dict[Any, Any] = {}
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
    ) -> dict[str, str]:
        diff = {}

        if batfish_if.active != arista_interface.line:
            diff["active"] = (
                f"Batfish: {batfish_if.active}, Arista: {arista_interface.line}"
            )

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
    ) -> dict[Any, Any]:
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
    ) -> CostResult:
        if arista_route.network != batfish_route.network:
            return [("network", math.inf)]
        if arista_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]
        if batfish_route.route_distinguisher != arista_route.route_distinguisher:
            return [("route_distinguisher", math.inf)]

        cost = []

        if arista_route.origin_protocol is not None:
            cost += AristaValidator._compute_bgp_protocol_cost(
                arista_route.origin_protocol, batfish_route.protocol
            )

        cost += AristaValidator._compute_evpn_next_hop_cost(
            arista_route, batfish_route.next_hop
        )

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

    @staticmethod
    def _compute_evpn_next_hop_cost(
        arista_route: AristaEvpnRoute, next_hop: NextHop
    ) -> CostResult:
        if isinstance(next_hop, NextHopDiscard):
            if arista_route.next_hop_ip is None:
                return []
            return [("next_hop_ip", 10.0)]

        if isinstance(next_hop, (NextHopIp, NextHopInterface)):
            if arista_route.next_hop_ip == next_hop.ip:
                return []
            return [("next_hop_ip", 10.0)]

        if isinstance(next_hop, NextHopVtep):
            if arista_route.next_hop_ip == next_hop.vtep:
                return []
            return [("next_hop_ip", 10.0)]

        raise ValueError("Unsupported next hop " + repr(next_hop))
