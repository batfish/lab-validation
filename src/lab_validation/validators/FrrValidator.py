from collections.abc import Sequence
from os import path
from typing import AbstractSet, Any

from lab_validation.parsers.frr.commands.routes import (
    parse_show_ip_route_vrf_all_json_by_vrf,
)
from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)

from .CumulusFrrValidator import CumulusFrrValidator

# Linux interfaces outside the device config: the management port and the
# docker bridge. Batfish does not model them.
HOST_ONLY_INTERFACES = frozenset({"eth0", "docker0"})


class FrrValidator(CumulusFrrValidator):
    """FRR 10 on Linux: containerlab FRR nodes, and the routing stack of SONiC.

    FRR 10 keys 'show ip route vrf all json' by VRF name, unlike the FRR
    shipped with Cumulus. Routes and interfaces on the management port, and
    local routes, are excluded.
    """

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
