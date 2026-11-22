import math
from collections.abc import Sequence
from os import path
from typing import AbstractSet, Any

from pybatfish.datamodel import NextHop, NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.frr.commands.bgp_routes import (
    parse_show_ip_bgp_vrf_all_json,
)
from lab_validation.parsers.frr.commands.routes import (
    parse_show_ip_route_vrf_all_json_by_vrf,
)
from lab_validation.parsers.frr.models.routes import FrrBgpRoute, FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute

from .CumulusFrrValidator import CumulusFrrValidator
from .utils.validation_utils import CostResult, match_pairs, matched_pairs_to_failures
from .vendor_validator import ValidationError

# Linux interfaces outside the device config: the management port and the
# docker bridge. Batfish does not model them.
HOST_ONLY_INTERFACES = frozenset({"eth0", "docker0"})


class FrrValidator(CumulusFrrValidator):
    """FRR 10 on Linux: containerlab FRR nodes, and the routing stack of SONiC.

    FRR 10 keys 'show ip route vrf all json' by VRF name, unlike the FRR
    shipped with Cumulus. Routes and interfaces on the management port, and
    local routes, are excluded.
    """

    SHOW_BGP_FILENAME_TXT = "vtysh_-c_'show_bgp_vrf_all_ipv4_unicast_json'.txt"

    def validate_bgp_rib_routes(
        self, bgp_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        """Compares the best and multipath IPv4 unicast paths in all VRFs."""
        show_bgp_path = path.join(self.device_path, FrrValidator.SHOW_BGP_FILENAME_TXT)
        if not path.isfile(show_bgp_path):
            raise ValidationError(
                f"{FrrValidator.SHOW_BGP_FILENAME_TXT} was not collected"
            )
        with open(show_bgp_path) as fp:
            show_routes = parse_show_ip_bgp_vrf_all_json(fp.read())
        # Batfish's BGP RIB answer has only the paths it selected.
        selected = [
            r for r in show_routes if r.is_valid and (r.is_bestpath or r.is_multipath)
        ]
        return matched_pairs_to_failures(
            match_pairs(selected, bgp_routes, _diff_bgp_routes_cost)
        )

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        show_interfaces = [
            i for i in self._show_interfaces() if i.name not in HOST_ONLY_INTERFACES
        ]
        diffs = self._compare_all_interfaces(show_interfaces, batfish_interfaces)
        return {kind: found for kind, found in diffs.items() if found}

    def _parse_routes(self) -> Sequence[FrrIpRoute]:
        with open(
            path.join(self.device_path, CumulusFrrValidator.SHOW_ROUTE_FILENAME_TXT)
        ) as fp:
            return parse_show_ip_route_vrf_all_json_by_vrf(fp.read())

    def _vrf_name(self, route: FrrIpRoute) -> str | None:
        return route.vrf

    def _show_route_processed(
        self, show_routes: Sequence[FrrIpRoute]
    ) -> list[FrrIpRoute]:
        # FRR 10 also lists a "local" /32 for each interface address; Batfish's
        # FRR model does not generate local routes. See
        # https://github.com/batfish/lab-validation/issues/248
        return [
            r
            for r in super()._show_route_processed(show_routes)
            if r.next_hop_int not in HOST_ONLY_INTERFACES and r.protocol != "local"
        ]


def _diff_bgp_routes_cost(
    show_route: FrrBgpRoute, batfish_route: BgpRibRoute
) -> CostResult:
    if show_route.network != batfish_route.network:
        return [("network", math.inf)]
    if show_route.vrf != batfish_route.vrf:
        return [("vrf", math.inf)]

    cost: CostResult = []
    protocol = "ibgp" if show_route.path_from == "internal" else "bgp"
    if protocol != batfish_route.protocol:
        cost.append(("protocol", 1.0))
    if show_route.origin.lower() != batfish_route.origin_type.lower():
        cost.append(("origin_type", 1.0))
    if tuple(show_route.as_path) != tuple(batfish_route.as_path):
        cost.append(("as_path", 1.0))
    if (show_route.med or 0) != batfish_route.metric:
        cost.append(("metric", 1.0))
    # FRR prints locPrf only for paths that carry LOCAL_PREF.
    local_pref = 100 if show_route.local_pref is None else show_route.local_pref
    if local_pref != batfish_route.local_preference:
        cost.append(("local_preference", 1.0))
    if show_route.weight != batfish_route.weight:
        cost.append(("weight", 1.0))
    cost += _bgp_next_hop_cost(show_route, batfish_route.next_hop)
    return cost


def _bgp_next_hop_cost(show_route: FrrBgpRoute, next_hop: NextHop) -> CostResult:
    used = [nh.ip for nh in show_route.next_hops if nh.is_used]
    show_ip = used[0] if used else show_route.next_hops[0].ip
    # FRR shows a path it originated with next hop 0.0.0.0 (or ::); Batfish
    # with discard.
    if show_ip in ("0.0.0.0", "::"):
        return [] if isinstance(next_hop, NextHopDiscard) else [("next_hop", 1.0)]
    if isinstance(next_hop, (NextHopIp, NextHopInterface)) and next_hop.ip == show_ip:
        return []
    return [("next_hop", 1.0)]
