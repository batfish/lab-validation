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
    "isis": {"isis"},
    "ospf": {"ospf"},
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
        # interfaces); they live in the separate `/state port` tree. Compare only the
        # L3 interfaces here, so the port interfaces are not flagged as "extra".
        batfish_index = {
            i.name.lower(): i
            for i in batfish_interfaces
            if i.interface_type != "PHYSICAL"
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
        # A local/connected route has no next-hop IP (next-hop is the interface);
        # Batfish models it as a NextHopInterface. Treat "SR OS has no nhip" as
        # compatible with a Batfish interface next-hop.
        if sros_route.next_hop_ip is None:
            if isinstance(next_hop, (NextHopInterface, NextHopDiscard)):
                return []
            # Batfish has an IP next-hop where SR OS reports none.
            return [("asymmetric nhip", 5.0)]
        if isinstance(next_hop, NextHopIp):
            if sros_route.next_hop_ip == next_hop.ip:
                return []
            return [("nhip", 1.0)]
        if isinstance(next_hop, NextHopInterface):
            if next_hop.ip is not None and next_hop.ip == sros_route.next_hop_ip:
                return []
            return [("nhip", 1.0)]
        return [("asymmetric next hop", 5.0)]

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

        # next-hop: locally-originated routes report 0.0.0.0 in SR OS; Batfish
        # uses a discard/own next-hop, so only compare for learned routes.
        if sros_route.owner == "bgp":
            cost += SrosValidator._bgp_next_hop_cost(
                sros_route.next_hop_ip, batfish_route.next_hop
            )

        if sros_route.as_path != list(batfish_route.as_path):
            cost.append(("as_path", 1.0))

        return cost

    @staticmethod
    def _bgp_next_hop_cost(
        sros_next_hop_ip: str | None, next_hop: NextHop
    ) -> CostResult:
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
        # the VPRN's VRF; interface comparison is by name, so include them so the
        # VPRN interfaces are validated, not flagged as extra Batfish interfaces.
        for vprn_path in sorted(
            self.device_path.glob("info_json_state_service_vprn_*_interface.txt")
        ):
            interfaces.extend(parse_interface_state_json(vprn_path.read_text()))
        return interfaces

    def _parse_routes(self) -> Sequence[SrosIpRoute]:
        path = self.device_path / self.ROUTE_TABLE_FILENAME
        assert path.is_file(), f"missing route-table state file: {path}"
        routes: list[SrosIpRoute] = list(
            parse_route_table_json(path.read_text(), _BASE_VRF)
        )
        # VPRN (multi-VRF) route-tables, if collected: a file named
        # info_json_state_service_vprn_<name>_route-table.txt holds the VPRN's
        # routes (same nokia-state schema as Base). The VPRN's Batfish VRF is the
        # service-name, so tag these routes with <name> to compare against the
        # corresponding Batfish VRF — proving VRF separation, not just Base.
        for vprn_path in sorted(
            self.device_path.glob("info_json_state_service_vprn_*_route-table.txt")
        ):
            vrf = self._vprn_name_from_filename(vprn_path.name)
            routes.extend(parse_route_table_json(vprn_path.read_text(), vrf))
        return routes

    @staticmethod
    def _vprn_name_from_filename(filename: str) -> str:
        """Extract the VPRN service-name from its route-table state filename."""
        prefix = "info_json_state_service_vprn_"
        suffix = "_route-table.txt"
        return filename[len(prefix) : -len(suffix)]

    def _parse_bgp_routes(self) -> Sequence[SrosBgpRoute]:
        path = self.device_path / self.BGP_RIB_FILENAME
        assert path.is_file(), f"missing bgp rib state file: {path}"
        return parse_bgp_rib_json(path.read_text(), _BASE_VRF)
