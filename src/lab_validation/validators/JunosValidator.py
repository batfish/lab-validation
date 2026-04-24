import math
from collections.abc import Sequence
from os import PathLike, path
from typing import (
    AbstractSet,
    Any,
)

from pybatfish.datamodel.route import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
    NextHopVtep,
)

from lab_validation.parsers.junos.commands.bgp_routes import (
    parse_show_route_protocol_bgp_display_json,
)
from lab_validation.parsers.junos.commands.interfaces import parse_show_interfaces_json
from lab_validation.parsers.junos.commands.routes import (
    parse_show_route_display_json,
    parse_show_route_evpn_display_json,
)
from lab_validation.parsers.junos.models.interfaces import JunosInterface
from lab_validation.parsers.junos.models.routes import (
    JunosBgpRoute,
    JunosEvpnRoute,
    JunosMainRibRoute,
)
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
)
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import CostResult, match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


class JunosValidator(VendorValidator):
    SHOW_ROUTE_FILENAME = "show_route_|_display_json.txt"
    SHOW_BGP_ROUTE_FILENAME = "show_route_protocol_bgp_|_display_json.txt"
    SHOW_INTERFACE_FILENAME = "show_interfaces_|_display_json.txt"

    def __init__(self, device_path: PathLike) -> None:
        self.device_path: PathLike = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        real_interfaces: Sequence[JunosInterface] = self._parse_interface()
        return NodeRuntimeData(
            interfaces=JunosValidator.get_interface_runtime_data(real_interfaces)
        )

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        real_routes = [r for r in self._parse_routes() if not filter_route(r)]

        # Filter Batfish local discard /32 routes. These are created for
        # deactivated interfaces (management or otherwise). The device never
        # has local+discard /32 routes — active interfaces have local routes
        # pointing to the interface, and deactivated interfaces have no route.
        batfish_routes = [
            r for r in batfish_routes if not _is_local_discard_host_route(r)
        ]

        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            _routes_cost,
        )
        return matched_pairs_to_failures(matched_routes)

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        # Filter Batfish VRF BGP routes that don't appear in device's
        # "show route protocol bgp": EVPN-leaked routes (ibgp in non-default
        # VRF) and locally-originated routes from connected subnets.
        batfish_routes = [
            r
            for r in batfish_routes
            if not (
                r.vrf != "default"
                and (r.protocol == "ibgp" or r.origin_protocol == "connected")
            )
        ]
        return self._compare_all_bgp_routes(self._parse_bgp_routes(), batfish_routes)

    def validate_evpn_rib_routes(
        self, batfish_routes: Sequence[EvpnRibRoute]
    ) -> dict[Any, Any]:
        if not batfish_routes:
            return {}
        real_routes = self._parse_evpn_routes()
        if not real_routes:
            return {}
        return self._compare_evpn_routes(real_routes, batfish_routes)

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        real_interfaces = self._parse_interface()

        diffs: dict[Any, Any] = {}
        batfish_index = {i.name.lower(): i for i in batfish_interfaces}
        real_index = {i.name.lower(): i for i in real_interfaces}

        # Get the extra interfaces in Batfish
        for name in batfish_index.keys() - real_index.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"

        # Get the missing interfaces in Batfish
        missing_in_batfish = real_index.keys() - batfish_index.keys()
        for name in missing_in_batfish:
            if not self._exclude_iface(name, missing_in_batfish):
                diffs[name] = f"Missing interface in Batfish: {real_index[name]}"

        # Get the diff for common interfaces
        for name in real_index.keys() & batfish_index.keys():
            diff = JunosValidator._compare_interfaces(
                real_index[name], batfish_index[name], vni_ifaces
            )
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _exclude_iface(iface_name: str, missing_in_batfish: set[str]) -> bool:
        # Junos reports many internal/pseudo interfaces that Batfish does not
        # model. Rather than enumerating every one, use prefix-based exclusion
        # to handle both existing (17.x) and newer (25.x) Junos versions.
        _EXCLUDE_PREFIXES = (
            "bme",  # backup mgmt for virtual chassis
            "cbp",  # customer backbone port
            "demux",  # demux interfaces (Junos 25.x+)
            "dsc",  # discard interface
            "em",  # management ethernet (many sub-interfaces)
            "esi",  # Ethernet Segment Interface (EVPN)
            "fti",  # flexible tunnel interface
            "fxp",  # management interface (vrnetlab/vMX)
            "gr-",  # GRE pseudo interface
            "gre",  # GMPLS control channel
            "ipip",  # IP-over-IP tunnel
            "irb",  # integrated routing and bridging
            "jsrv",  # sFlow monitoring
            "lc-",  # line card internal
            "mif",  # management infrastructure filter
            "lsi",  # label switched interface (VPLS/MPLS)
            "lt-",  # logical tunnel
            "mtun",  # multicast tunnel
            "pfe-",  # RE-PFE internal communication
            "pfh-",  # PFE host processor
            "pimd",  # multicast PIM
            "pime",  # multicast PIM
            "pip0",  # provider instance port
            "pp0",  # PPP interface
            "rbeb",  # EVPN backbone edge bridge
            "sp-",  # adaptive services
            "st0",  # secure tunnel
            "tap",  # traffic mirroring
            "vme",  # virtual management ethernet
            "vtep",  # VXLAN tunnel endpoint
        )

        _EXCLUDE_EXACT = {
            "lo0.16384",  # internal loopback unit
            "lo0.16385",  # non-configurable router control traffic
        }

        if iface_name in _EXCLUDE_EXACT:
            return True
        if iface_name.startswith(_EXCLUDE_PREFIXES):
            return True

        # Unconfigured xe/ge/et interfaces get a .16386 default unit
        if iface_name.endswith(".16386") or f"{iface_name}.16386" in missing_in_batfish:
            return True

        return False

    @staticmethod
    def _compare_interfaces(
        real_interface: JunosInterface,
        batfish_interface: InterfaceProperties,
        vni_ifaces: AbstractSet[str] = frozenset(),
    ) -> dict[str, str]:
        diff = {}

        is_mgmt = batfish_interface.name.startswith(("em", "fxp"))
        # IRB interfaces backed by VXLAN VNIs are inactive pre-dataplane in
        # Batfish but come up once VXLAN tunnels establish on the real device.
        is_vni_predataplane = (
            not batfish_interface.active
            and real_interface.state.admin
            and real_interface.state.line
            and batfish_interface.name in vni_ifaces
        )
        if not is_mgmt and not is_vni_predataplane:
            if batfish_interface.active != (
                real_interface.state.admin and real_interface.state.line
            ):
                diff["active"] = (
                    f"Batfish: {batfish_interface.active}, JUNOS: admin={real_interface.state.admin} line={real_interface.state.line}"
                )

        if real_interface.bandwidth is None:
            junos_bw = real_interface.speed
        else:
            junos_bw = real_interface.bandwidth

        if not is_mgmt and batfish_interface.bandwidth != junos_bw:
            # Skipping loopback interface bw: Junos sets it to `None` and batfish sets 1E12. So we already know it
            # will always disagree.
            if not (
                real_interface.name.startswith("lo0")
                and real_interface.bandwidth is None
            ):
                diff["bandwidth"] = (
                    f"Batfish: {batfish_interface.bandwidth}, JUNOS: {junos_bw}"
                )

        # Ignoring MTU as Batfish does not model it correctly
        # if batfish_if.mtu != junos_interface.mtu:
        #     diff["mtu"] = f"Batfish: {batfish_if.mtu}, JUNOS: {junos_interface.mtu}"

        return diff

    @staticmethod
    def get_interface_runtime_data(
        interfaces: Sequence[JunosInterface],
    ) -> dict[str, InterfaceRuntimeData]:
        return {
            iface.name: InterfaceRuntimeData(
                bandwidth=iface.bandwidth, lineUp=iface.state.line, speed=iface.speed
            )
            for iface in interfaces
        }

    def _parse_routes(self) -> Sequence[JunosMainRibRoute]:
        show_route_path = path.join(
            self.device_path, JunosValidator.SHOW_ROUTE_FILENAME
        )

        if not path.isfile(show_route_path):
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_route_display_json(routes_text)

    def _parse_evpn_routes(self) -> Sequence[JunosEvpnRoute]:
        show_route_path = path.join(
            self.device_path, JunosValidator.SHOW_ROUTE_FILENAME
        )

        if not path.isfile(show_route_path):
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_route_evpn_display_json(routes_text)

    @staticmethod
    def _compare_evpn_routes(
        real_routes: Sequence[JunosEvpnRoute],
        batfish_routes: Sequence[EvpnRibRoute],
    ) -> dict[Any, Any]:
        failures: dict[Any, Any] = {}

        real_by_key: dict[tuple[str, str], JunosEvpnRoute] = {}
        for real_rt in real_routes:
            real_by_key[(real_rt.route_distinguisher, real_rt.network)] = real_rt

        bf_by_key: dict[tuple[str, str], EvpnRibRoute] = {}
        for bf_rt in batfish_routes:
            bf_by_key[(bf_rt.route_distinguisher, bf_rt.network)] = bf_rt

        for key in real_by_key.keys() - bf_by_key.keys():
            failures[key] = f"Batfish is missing EVPN route: {real_by_key[key]}"

        for key in bf_by_key.keys() - real_by_key.keys():
            failures[key] = f"Batfish has extra EVPN route: {bf_by_key[key]}"

        for key in real_by_key.keys() & bf_by_key.keys():
            real = real_by_key[key]
            bf = bf_by_key[key]
            diff: dict[str, str] = {}

            if bf.as_path != tuple(real.as_path):
                diff["as_path"] = (
                    f"Batfish: {list(bf.as_path)}, real: {list(real.as_path)}"
                )

            if real.local_preference is not None:
                if bf.local_preference != real.local_preference:
                    diff["local_preference"] = (
                        f"Batfish: {bf.local_preference}, real: {real.local_preference}"
                    )

            valid_origin_pairs = {("I", "igp"), ("E", "egp"), ("?", "incomplete")}
            if (real.origin_type, bf.origin_type) not in valid_origin_pairs:
                diff["origin_type"] = (
                    f"Batfish: {bf.origin_type}, real: {real.origin_type}"
                )

            if diff:
                failures[key] = diff

        return failures

    def _parse_bgp_routes(self) -> Sequence[JunosBgpRoute]:
        show_route_path = path.join(
            self.device_path, JunosValidator.SHOW_BGP_ROUTE_FILENAME
        )

        if not path.isfile(show_route_path):
            return []

        with open(show_route_path) as fp:
            routes_text = fp.read()
        return parse_show_route_protocol_bgp_display_json(routes_text)

    def _parse_interface(self) -> Sequence[JunosInterface]:
        show_interface_path = path.join(
            self.device_path, JunosValidator.SHOW_INTERFACE_FILENAME
        )

        if not path.isfile(show_interface_path):
            return []

        with open(show_interface_path) as fp:
            interface_text = fp.read()
        return parse_show_interfaces_json(interface_text)

    def _compare_all_bgp_routes(
        self,
        real_routes: Sequence[JunosBgpRoute],
        batfish_routes: Sequence[BgpRibRoute],
    ) -> dict[Any, Any]:
        matched_routes = match_pairs(
            real_routes,
            batfish_routes,
            _bgp_routes_cost,
        )
        # Don't report inactive device routes as missing from Batfish.
        # Inactive means BGP-best but lost to a lower-admin-distance protocol
        # in the main RIB — Batfish may or may not have them.
        return matched_pairs_to_failures(
            [
                (left, right, cost)
                for left, right, cost in matched_routes
                if right is not None or (left is not None and left.is_active)
            ]
        )


def _bgp_routes_cost(
    real_route: JunosBgpRoute, batfish_route: BgpRibRoute
) -> CostResult:
    if real_route.network != batfish_route.network:
        return [("network", math.inf)]
    if real_route.vrf != batfish_route.vrf:
        return [("vrf", math.inf)]

    cost: CostResult = []
    real_metric = 0 if real_route.metric is None else real_route.metric

    # When Batfish shows ibgp and device shows BGP, the route was learned
    # via overlay iBGP in Batfish but underlay eBGP on the device. AS path
    # and origin_protocol will differ due to the dual-plane architecture.
    protocol_mismatch = (
        batfish_route.protocol == "ibgp" and real_route.origin_protocol == "BGP"
    )

    if batfish_route.metric != real_metric:
        cost.append(("metric", 1.0))
    if batfish_route.local_preference != real_route.local_preference:
        cost.append(("local_preference", 1.0))
    if not protocol_mismatch and batfish_route.as_path != real_route.as_path:
        cost.append(("as_path", 1.0))
    assert batfish_route.origin_protocol is not None
    if (
        not protocol_mismatch
        and batfish_route.origin_protocol.lower() != real_route.origin_protocol.lower()
    ):
        cost.append(("origin_protocol", 1.0))
    valid_origin_pairs = {("I", "igp"), ("E", "egp"), ("?", "incomplete")}
    if (real_route.origin_type, batfish_route.origin_type) not in valid_origin_pairs:
        cost.append(("origin_type", 1.0))

    return cost


def _routes_cost(
    expected_route: JunosMainRibRoute, batfish_route: MainRibRoute
) -> CostResult:
    if expected_route.network != batfish_route.network:
        return [("network", math.inf)]
    if expected_route.vrf != batfish_route.vrf:
        return [("vrf", math.inf)]

    cost: CostResult = []

    cost += _compute_protocol_cost(expected_route, batfish_route)
    cost += _compute_nexthop_cost(expected_route, batfish_route.next_hop)

    if (expected_route.metric or 0) != batfish_route.metric:
        cost.append(("metric", 1.0))
    if expected_route.admin != batfish_route.admin:
        cost.append(("admin", 1.0))

    return cost


def _compute_protocol_cost(
    expected_route: JunosMainRibRoute, batfish_route: MainRibRoute
) -> CostResult:
    _PROTOCOL_MAP = {
        "Direct": {"connected"},
        "Local": {"local"},
        "Aggregate": {"aggregate"},
        "Static": {"static"},
        "BGP": {"bgp", "ibgp"},
        "EVPN": {"bgp", "ibgp"},
        "OSPF": {"ospf", "ospfE1", "ospfE2", "ospfIA", "ospfIS"},
    }
    valid = _PROTOCOL_MAP.get(expected_route.protocol)
    if valid is not None and batfish_route.protocol in valid:
        return []
    return [("protocol", math.inf)]


def _is_mgmt_iface(junos_name: str | None) -> bool:
    """Return true iff Batfish treats this interface as a management interface."""
    if junos_name is None:
        return False
    return junos_name.startswith(("em0", "fxp0"))


def _compute_nexthop_cost(
    expected_route: JunosMainRibRoute, next_hop: NextHop
) -> CostResult:
    if _is_mgmt_iface(expected_route.next_hop_int) and isinstance(
        next_hop, NextHopDiscard
    ):
        return []

    if expected_route.nh_type in {"Discard", "Reject"} and isinstance(
        next_hop, NextHopDiscard
    ):
        return []
    if expected_route.nh_type in {"Discard", "Reject"} or isinstance(
        next_hop, NextHopDiscard
    ):
        return [("next_hop", 10.0)]

    if isinstance(next_hop, NextHopIp):
        if expected_route.protocol in ("Static", "BGP", "EVPN"):
            # Junos recursively resolves next-hops to underlay addresses while
            # Batfish reports the protocol-level next-hop.
            return []
        elif expected_route.next_hop_ip == next_hop.ip:
            return []
        else:
            return [("next_hop_ip", 1.0)]

    if isinstance(next_hop, NextHopInterface):
        cost: CostResult = []
        if expected_route.next_hop_int != next_hop.interface:
            cost.append(("next_hop_int", 5.0))
        if next_hop.ip is not None and expected_route.next_hop_ip != next_hop.ip:
            cost.append(("next_hop_ip", 1.0))
        return cost

    if isinstance(next_hop, NextHopVtep):
        # NextHopVtep carries the VTEP IP and VNI, but Junos resolves EVPN
        # routes to underlay physical next-hops.
        return []

    raise ValueError("Unsupported next hop " + repr(next_hop))


def _is_local_discard_host_route(route: MainRibRoute) -> bool:
    """Check if a Batfish route is a local /32 discard route.

    Batfish creates these for deactivated interfaces. The device never has
    local+discard /32 routes — active interfaces produce local routes
    pointing to the interface, and deactivated interfaces produce no route.
    """
    return (
        isinstance(route.next_hop, NextHopDiscard)
        and route.protocol == "local"
        and route.network.endswith("/32")
    )


def filter_route(real_route: JunosMainRibRoute) -> bool:
    # Multipath routes are ECMP resolution entries, not independent routes
    if real_route.protocol == "Multipath":
        return True
    # Juniper throws in a multicast route when you're using OSPF, filter it out
    if real_route.network.startswith("224.0.0") and real_route.nh_type == "MultiRecv":
        return True
    # mgmt_junos is the management routing instance (vrnetlab/vMX)
    elif real_route.vrf == "mgmt_junos":
        return True
    elif _is_mgmt_iface(real_route.next_hop_int):
        return True
    # batfish creates only active routes
    elif not real_route.active:
        return True
    else:
        return False
