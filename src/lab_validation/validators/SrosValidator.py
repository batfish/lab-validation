"""Nokia SR OS validator.

Validates Batfish's analysis of a Nokia SR OS (SR-SIM) device against the
device's own operational state, captured as JSON from the MD-CLI state tree
(``info json /state router "Base" ...``). The state branch renders as JSON
keyed by the ``nokia-state`` YANG modules, which is the SR OS analog of Junos
``show | display json`` — so, like the Arista validator, this is JSON-driven
rather than CLI-text parsing.

This is the first SR OS validation slice (P5-V): it covers what Batfish models
after parse/extract/convert — interfaces, the main RIB, and the BGP RIB. SR OS
``router "Base"`` is the main routing instance, which maps to Batfish's default
VRF.
"""

import math
from collections.abc import Sequence
from pathlib import Path
from typing import AbstractSet, Any

import attr
from pybatfish.datamodel import (
    NextHop,
    NextHopDiscard,
    NextHopInterface,
    NextHopIp,
)

from lab_validation.parsers.sros.commands.bgp_routes import parse_bgp_rib_json
from lab_validation.parsers.sros.commands.interfaces import parse_interface_state_json
from lab_validation.parsers.sros.commands.routes import parse_route_table_json
from lab_validation.parsers.sros.models.interfaces import SrosInterface
from lab_validation.parsers.sros.models.routes import SrosBgpRoute, SrosIpRoute

from .batfish_models.interface_properties import InterfaceProperties
from .batfish_models.routes import BgpRibRoute, MainRibRoute
from .batfish_models.runtime_data import InterfaceRuntimeData, NodeRuntimeData
from .utils.validation_utils import CostResult, match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator

# SR OS "Base" router instance == Batfish default VRF.
_BASE_VRF = "default"

# SR OS route-table protocol string -> the set of Batfish main-RIB protocol
# strings that are an acceptable match. SR OS reports every BGP-learned route
# (eBGP or iBGP) as protocol "bgp" in its route-table, whereas Batfish
# distinguishes "bgp" (eBGP) from "ibgp", so SR OS "bgp" matches either.
_PROTOCOL_MAP = {
    "local": {"connected"},
    "bgp": {"bgp", "ibgp"},
    "static": {"static"},
    # SR OS reports a single "isis" owner in the route-table; Batfish labels IS-IS
    # routes by level (isisL1/isisL2, and isisEL1/isisEL2 for externals).
    "isis": {"isis", "isisL1", "isisL2", "isisEL1", "isisEL2"},
    "ospf": {"ospf", "ospfIA", "ospfE1", "ospfE2"},
}


class SrosValidator(VendorValidator):
    INTERFACE_FILENAME = "info_json_state_router_Base_interface.txt"
    ROUTE_TABLE_FILENAME = "info_json_state_router_Base_route-table.txt"
    BGP_RIB_FILENAME = "info_json_state_router_Base_bgp_rib.txt"

    def __init__(self, device_path: str | Path) -> None:
        self.device_path = Path(device_path)

    # --- runtime data -----------------------------------------------------------

    def get_runtime_data(self) -> NodeRuntimeData:
        # SR OS interface state has no bandwidth/speed in the modeled subset, and
        # the interfaces come up once configured; supply line status so Batfish's
        # pre-dataplane interface activity matches the device.
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=None, lineUp=iface.oper_up, speed=None
                )
                for iface in self._parse_interfaces()
            }
        )

    # --- interfaces -------------------------------------------------------------

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        return SrosValidator._compare_all_interfaces(
            self._parse_interfaces(), batfish_interfaces
        )

    @staticmethod
    def _compare_all_interfaces(
        sros_interfaces: Sequence[SrosInterface],
        batfish_interfaces: Sequence[InterfaceProperties],
    ) -> dict[Any, Any]:
        diffs: dict[Any, Any] = {}
        # Batfish models each SR OS L3 router-interface (e.g. "to-r2") as a LOGICAL
        # interface bound to a distinct PHYSICAL port interface (e.g. "1/1/c1/1"), so
        # that a Layer-1 topology naming the port drives the L3 adjacency. Those
        # synthetic port interfaces are L1 hardware and do not appear in the device's
        # `info json /state router "Base" interface` tree (which lists only L3 router
        # interfaces); they live in the separate `/state port` tree. An AGGREGATED
        # interface (a LAG, e.g. "lag-1") is likewise an L1/bundle construct in the
        # `/state lag` tree, not a router interface. Compare only the L3 interfaces
        # here, so the port/LAG interfaces are not flagged as "extra".
        batfish_index = {
            i.name.lower(): i
            for i in batfish_interfaces
            if i.interface_type not in ("PHYSICAL", "AGGREGATED")
        }
        real_index = {i.name.lower(): i for i in sros_interfaces}
        for name in batfish_index.keys() - real_index.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_index[name]}"
        for name, sros_if in real_index.items():
            if name not in batfish_index:
                diffs[name] = f"Missing interface in Batfish: {sros_if}"
                continue
            diff = SrosValidator._compare_interface(sros_if, batfish_index[name])
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _compare_interface(
        sros_interface: SrosInterface, batfish_if: InterfaceProperties
    ) -> dict[str, str]:
        diff = {}
        if batfish_if.active != sros_interface.oper_up:
            diff["active"] = (
                f"Batfish: {batfish_if.active}, SR OS oper-state up: {sros_interface.oper_up}"
            )
        # Compare the primary IPv4 address (prefix length is not in the SR OS
        # interface state tree, so compare the address only).
        sros_addr = sros_interface.primary_address
        batfish_addrs = {p.split("/")[0] for p in batfish_if.all_prefixes}
        if sros_addr is not None and sros_addr not in batfish_addrs:
            diff["address"] = (
                f"Batfish prefixes: {batfish_if.all_prefixes}, SR OS primary: {sros_addr}"
            )
        elif sros_addr is None and batfish_addrs:
            diff["address"] = (
                f"Batfish prefixes: {batfish_if.all_prefixes}, SR OS primary: none"
            )
        return diff

    # --- main RIB ---------------------------------------------------------------

    def validate_main_rib_routes(
        self, routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        return SrosValidator._validate_main_rib_routes(self._parse_routes(), routes)

    @staticmethod
    def _validate_main_rib_routes(
        sros_routes: Sequence[SrosIpRoute],
        batfish_routes: Sequence[MainRibRoute],
    ) -> dict[Any, Any]:
        matched = match_pairs(
            sros_routes, batfish_routes, SrosValidator._diff_routes_cost
        )
        return matched_pairs_to_failures(matched)

    @staticmethod
    def _diff_routes_cost(
        sros_route: SrosIpRoute, batfish_route: MainRibRoute
    ) -> CostResult:
        if sros_route.network != batfish_route.network:
            return [("network", math.inf)]
        if sros_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost: CostResult = []
        cost += SrosValidator._protocol_cost(
            sros_route.protocol, batfish_route.protocol
        )
        cost += SrosValidator._next_hop_cost(sros_route, batfish_route.next_hop)

        # SR OS route preference == Batfish admin distance. A local/connected
        # route reports preference 0, which Batfish also models as 0.
        if (
            sros_route.preference is not None
            and sros_route.preference != batfish_route.admin
        ):
            cost.append(("admin", 2.0))

        # Metric: for BGP routes the two sides model the main-RIB metric
        # differently — Batfish carries the BGP MED into the main-RIB metric,
        # while the SR OS route-table reports the IGP cost to the BGP next-hop
        # (0 for a directly-connected peer). The MED itself is validated on the
        # BGP RIB (see _diff_bgp_routes_cost), so skip the main-RIB metric
        # comparison for BGP routes rather than flag this known representation
        # gap. For non-BGP routes (connected/static/IGP) the metric is compared.
        if batfish_route.protocol not in ("bgp", "ibgp"):
            sros_metric = 0 if sros_route.metric is None else sros_route.metric
            if sros_metric != batfish_route.metric:
                cost.append(("metric", 1.0))

        return cost

    @staticmethod
    def _protocol_cost(sros_protocol: str, batfish_protocol: str) -> CostResult:
        accepted = _PROTOCOL_MAP.get(sros_protocol, {sros_protocol})
        if batfish_protocol in accepted:
            return []
        return [("protocol", math.inf)]

    @staticmethod
    def _next_hop_cost(sros_route: SrosIpRoute, next_hop: NextHop) -> CostResult:
        # SR OS route next-hops come in three shapes, resolved from the route-table
        # JSON: an egress interface (connected/local; if-index resolved to a name),
        # a next-hop IP (BGP), or both (resolved static/IGP); a blackhole has
        # neither. Validate the shape that SR OS reports against Batfish's NextHop.
        nhip = sros_route.next_hop_ip
        nhif = sros_route.next_hop_interface

        # Blackhole / discard: no IP and no interface.
        if nhip is None and nhif is None:
            if isinstance(next_hop, NextHopDiscard):
                return []
            return [("asymmetric discard next hop", 5.0)]

        cost: CostResult = []
        if isinstance(next_hop, NextHopIp):
            # Batfish IP next-hop: the IP must match; SR OS should have reported one.
            if nhip is None or nhip != next_hop.ip:
                cost.append(("nhip", 1.0))
        elif isinstance(next_hop, NextHopInterface):
            # Batfish interface next-hop: the egress interface name must match the
            # SR OS-resolved interface, and any IP on it must match SR OS's nhip.
            if nhif is None or nhif != next_hop.interface:
                cost.append(("nhint", 1.0))
            if next_hop.ip is not None and nhip is not None and next_hop.ip != nhip:
                cost.append(("nhip", 1.0))
        else:
            cost.append(("asymmetric next hop", 5.0))
        return cost

    # --- BGP RIB ----------------------------------------------------------------

    def validate_bgp_rib_routes(
        self, bgp_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        return SrosValidator._validate_bgp_rib_routes(
            self._parse_bgp_routes(), bgp_routes
        )

    @staticmethod
    def _validate_bgp_rib_routes(
        sros_routes: Sequence[SrosBgpRoute],
        batfish_routes: Sequence[BgpRibRoute],
    ) -> dict[Any, Any]:
        # Compare against the routes in the device's actual BGP route table, i.e. those
        # learned from a peer (owner == "bgp"). This is not a workaround: the JSON state
        # `bgp rib local-rib` over-lists relative to the operational BGP table. The
        # device's `show router bgp routes` shows exactly one route here (2.2.2.2/32,
        # "Total Remote Rts: 1"); the `owner == local` entries (1.1.1.1/32, 10.0.0.0/31)
        # carry `in-rtm: false` and are main-RIB routes that BGP can see *for
        # advertisement via an export policy* — not BGP-originated routes. They are
        # absent from Batfish's BGP RIB for the same reason (SR OS advertises from the
        # main RIB; see SrosConfiguration setExportBgpFromBgpRib(false)). Selecting the
        # learned subset compares like-for-like against Batfish's BGP RIB question.
        validate_routes = [r for r in sros_routes if r.best and r.owner == "bgp"]
        matched = match_pairs(
            validate_routes, batfish_routes, SrosValidator._diff_bgp_routes_cost
        )
        return matched_pairs_to_failures(matched)

    @staticmethod
    def _diff_bgp_routes_cost(
        sros_route: SrosBgpRoute, batfish_route: BgpRibRoute
    ) -> CostResult:
        if sros_route.network != batfish_route.network:
            return [("network", math.inf)]
        if sros_route.vrf != batfish_route.vrf:
            return [("vrf", math.inf)]

        cost: CostResult = []
        if (
            sros_route.origin_type
            and sros_route.origin_type != batfish_route.origin_type
        ):
            cost.append(("origin_type", 1.0))

        # These are learned routes only (validate_bgp_rib_routes filters to
        # owner == "bgp"), so each has a real peer next-hop IP to compare against
        # Batfish's BGP next-hop.
        cost += SrosValidator._bgp_next_hop_cost(
            sros_route.next_hop_ip, batfish_route.next_hop
        )

        if sros_route.as_path != list(batfish_route.as_path):
            cost.append(("as_path", 1.0))

        # Communities on the learned route. SR OS carries them on the route's
        # attr-set; compare as sets against Batfish's communities. (On the current
        # labs both sides are empty for learned routes — the communities r1 *sets*
        # appear on the advertised rib-out routes, validated cross-vendor by the
        # cEOS oracle and, on the SR OS side, parseable via parse_bgp_rib_out_json.)
        if set(sros_route.communities) != set(batfish_route.communities):
            cost.append(("communities", 1.0))

        return cost

    @staticmethod
    def _bgp_next_hop_cost(
        sros_next_hop_ip: str | None, next_hop: NextHop
    ) -> CostResult:
        if isinstance(next_hop, NextHopDiscard):
            # A locally-originated route advertised into BGP (e.g. an aggregate) carries a
            # 0.0.0.0 next-hop on SR OS; Batfish models the aggregate as a discard route. Treat
            # these as a match.
            if sros_next_hop_ip in (None, "0.0.0.0"):
                return []
            return [("asymmetric next hop", 5.0)]
        if isinstance(next_hop, NextHopIp):
            if sros_next_hop_ip == next_hop.ip:
                return []
            return [("nhip", 1.0)]
        if sros_next_hop_ip is None:
            return []
        return [("asymmetric next hop", 5.0)]

    # --- parsing helpers --------------------------------------------------------

    def _parse_interfaces(self) -> Sequence[SrosInterface]:
        path = self.device_path / self.INTERFACE_FILENAME
        assert path.is_file(), f"missing interface state file: {path}"
        interfaces: list[SrosInterface] = list(
            parse_interface_state_json(path.read_text())
        )
        # VPRN (multi-VRF) interfaces, if collected: a file named
        # info_json_state_service_vprn_<name>_interface.txt holds the VPRN's L3
        # interfaces (same schema as Base). Batfish models them as interfaces in
        # the VPRN's VRF; include them so the VPRN interfaces are validated, not
        # flagged as extra Batfish interfaces.
        for vprn_path in sorted(
            self.device_path.glob("info_json_state_service_vprn_*_interface.txt")
        ):
            interfaces.extend(self._parse_vprn_interfaces(vprn_path))
        return interfaces

    @staticmethod
    def _parse_vprn_interfaces(vprn_path: Path) -> Sequence[SrosInterface]:
        """Parse a VPRN interface state file, qualifying each name with its VRF.

        SR OS scopes interface names per router instance, so the same name (e.g.
        ``to-cea``) can appear in two VPRNs. Batfish keys interfaces by name per
        node, so it models a non-Base (VPRN) interface under the qualified name
        ``<vrf>.<name>`` (see SrosConversions.viInterfaceName). Mirror that here so
        the comparison pairs by the same name and reused names are not collapsed.
        """
        vrf = SrosValidator._vprn_name_from_filename(
            vprn_path.name, suffix="_interface.txt"
        )
        return [
            attr.evolve(iface, name=f"{vrf}.{iface.name}")
            for iface in parse_interface_state_json(vprn_path.read_text())
        ]

    def _parse_routes(self) -> Sequence[SrosIpRoute]:
        path = self.device_path / self.ROUTE_TABLE_FILENAME
        assert path.is_file(), f"missing route-table state file: {path}"
        # Build an if-index -> interface-name map from the Base interface state so
        # route nexthops that reference an egress interface by index resolve to a
        # name (validated against Batfish's NextHopInterface).
        base_ifmap = self._if_index_map(
            parse_interface_state_json(
                (self.device_path / self.INTERFACE_FILENAME).read_text()
            )
        )
        routes: list[SrosIpRoute] = list(
            parse_route_table_json(path.read_text(), _BASE_VRF, base_ifmap)
        )
        # VPRN (multi-VRF) route-tables, if collected: a file named
        # info_json_state_service_vprn_<name>_route-table.txt holds the VPRN's
        # routes (same nokia-state schema as Base). The VPRN's Batfish VRF is the
        # service-name, so tag these routes with <name> to compare against the
        # corresponding Batfish VRF — proving VRF separation, not just Base. Use
        # the matching VPRN interface file for that VPRN's if-index -> name map.
        for vprn_path in sorted(
            self.device_path.glob("info_json_state_service_vprn_*_route-table.txt")
        ):
            vrf = self._vprn_name_from_filename(vprn_path.name)
            if_path = (
                self.device_path / f"info_json_state_service_vprn_{vrf}_interface.txt"
            )
            # Resolve VPRN route egress interfaces to their qualified VI names
            # (<vrf>.<name>), matching Batfish's NextHopInterface (see
            # _parse_vprn_interfaces).
            ifmap = (
                self._if_index_map(self._parse_vprn_interfaces(if_path))
                if if_path.is_file()
                else {}
            )
            routes.extend(parse_route_table_json(vprn_path.read_text(), vrf, ifmap))
        return routes

    @staticmethod
    def _if_index_map(interfaces: Sequence[SrosInterface]) -> dict[int, str]:
        return {i.if_index: i.name for i in interfaces if i.if_index is not None}

    @staticmethod
    def _vprn_name_from_filename(
        filename: str, suffix: str = "_route-table.txt"
    ) -> str:
        """Extract the VPRN service-name from its per-VPRN state filename."""
        prefix = "info_json_state_service_vprn_"
        assert filename.startswith(prefix) and filename.endswith(suffix), (
            f"unexpected VPRN state filename: {filename}"
        )
        return filename[len(prefix) : -len(suffix)]

    def _parse_bgp_routes(self) -> Sequence[SrosBgpRoute]:
        path = self.device_path / self.BGP_RIB_FILENAME
        assert path.is_file(), f"missing bgp rib state file: {path}"
        return parse_bgp_rib_json(path.read_text(), _BASE_VRF)
