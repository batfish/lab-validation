from collections.abc import Sequence
from os import path
from typing import AbstractSet, Any

from lab_validation.parsers.frr.commands.routes import (
    parse_show_ip_route_vrf_all_json_by_vrf,
)
from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.parsers.sonic.commands.interfaces import (
    parse_show_interfaces_status,
)
from lab_validation.parsers.sonic.models.interfaces import SonicInterfaceStatus
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .CumulusFrrValidator import CumulusFrrValidator

# Linux interfaces outside SONiC's config_db: the management port and the
# docker bridge. Batfish does not model them.
HOST_ONLY_INTERFACES = frozenset({"eth0", "docker0"})


class SonicValidator(CumulusFrrValidator):
    """SONiC routing runs in FRR, so routes come from the host vtysh.

    Front-panel port state comes from SONiC's own 'show interfaces status'
    rather than FRR, whose kernel view of a sonic-vs port reports the veth
    speed instead of the configured port speed.
    """

    SHOW_INTERFACES_STATUS_FILENAME = "show_interfaces_status.txt"

    def get_runtime_data(self) -> NodeRuntimeData:
        # sonic_bgp_lab was collected before 'show interfaces status' was.
        status_path = path.join(
            self.device_path, SonicValidator.SHOW_INTERFACES_STATUS_FILENAME
        )
        if not path.isfile(status_path):
            return NodeRuntimeData()
        return NodeRuntimeData(
            interfaces={
                iface.name: InterfaceRuntimeData(
                    bandwidth=iface.speed, lineUp=iface.oper_up, speed=iface.speed
                )
                for iface in self._show_interfaces_status()
            }
        )

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        diffs: dict[Any, Any] = {
            "batfish_extra": {},
            "batfish_missing": {},
            "batfish_mismatch": {},
        }
        show_index = {i.name: i for i in self._show_interfaces_status()}
        # 'show interfaces status' lists only front-panel ports.
        batfish_index = {
            i.name: i for i in batfish_interfaces if i.name.startswith("Ethernet")
        }
        for name in batfish_index.keys() - show_index.keys():
            diffs["batfish_extra"][name] = batfish_index[name]
        for name, show_iface in show_index.items():
            if name not in batfish_index:
                diffs["batfish_missing"][name] = show_iface
                continue
            mismatch = _compare_interface(show_iface, batfish_index[name])
            if mismatch:
                diffs["batfish_mismatch"][name] = mismatch
        return {kind: found for kind, found in diffs.items() if found}

    def _show_interfaces_status(self) -> Sequence[SonicInterfaceStatus]:
        status_path = path.join(
            self.device_path, SonicValidator.SHOW_INTERFACES_STATUS_FILENAME
        )
        with open(status_path) as fp:
            return parse_show_interfaces_status(fp.read())

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
        return [
            r
            for r in super()._show_route_processed(show_routes)
            if r.next_hop_int not in HOST_ONLY_INTERFACES
        ]


def _compare_interface(
    show_iface: SonicInterfaceStatus, batfish_iface: InterfaceProperties
) -> dict[str, str]:
    diff = {}
    show_active = show_iface.admin_up and show_iface.oper_up
    if batfish_iface.active != show_active:
        diff["active"] = f"Batfish: {batfish_iface.active}, show_data: {show_active}"
    if batfish_iface.bandwidth != show_iface.speed:
        diff["bandwidth"] = (
            f"Batfish: {batfish_iface.bandwidth}, show_data: {show_iface.speed}"
        )
    if batfish_iface.mtu != show_iface.mtu:
        diff["mtu"] = f"Batfish: {batfish_iface.mtu}, show_data: {show_iface.mtu}"
    return diff
