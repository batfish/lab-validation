import ipaddress
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from lab_validation.parsers.fortios.commands.interfaces import (
    parse_get_system_interface,
    parse_get_system_interface_physical,
)
from lab_validation.parsers.fortios.models.interfaces import (
    FortiosInterface,
    FortiosPhysicalInterface,
)
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .vendor_validator import ValidationError, VendorValidator


def _get_speed(speed: int | None, bru: str | None) -> int | None:
    """
    Get speed in bps for specified speed value and bit rate unit.
    If either is None, returns None instead.
    """
    if bru is None or speed is None:
        return None
    bru = bru.lower()
    if bru == "gbps":
        mult = 1e9
    elif bru == "mbps":
        mult = 1e6
    elif bru == "kbps":
        mult = 1e3
    elif bru == "bps":
        mult = 1
    else:
        raise ValueError(f"Unhandled speed bit rate unit: {bru}")
    return speed * int(mult)


def _get_ip_str(addr: str | None, mask: str | None) -> str | None:
    """
    Convert ip address and mask to Batfish-style address with '/' prefix.
    If ip address is 0.0.0.0, returns None instead. Both addr and mask must be specified or both must be None.
    """
    if addr is None or addr == "0.0.0.0":
        return None
    # Addr and mask should either both set or neither is set
    assert mask is not None
    prefixlen = ipaddress.IPv4Network(f"{addr}/{mask}", strict=False).prefixlen
    # Leave host bits alone (ipaddress clobbers these)
    return f"{addr}/{prefixlen}"


def _compare_interfaces(
    iface: FortiosInterface,
    phys_iface: FortiosPhysicalInterface | None,
    bf_iface: InterfaceProperties,
) -> dict[str, str]:
    diff = {}

    if bf_iface.active != (iface.status == "up"):
        diff["active"] = f"Batfish: {bf_iface.active}, Fortios: status={iface.status}"

    ip_str = _get_ip_str(iface.ip_addr, iface.ip_mask)
    if ip_str and ip_str not in bf_iface.all_prefixes:
        diff["ipv4 address"] = f"Batfish: {bf_iface.all_prefixes}, Fortios: {ip_str}"

    if not phys_iface:
        return diff

    fortios_speed = _get_speed(phys_iface.speed, phys_iface.bit_rate_unit)
    if fortios_speed is not None and bf_iface.speed != fortios_speed:
        diff["speed"] = f"Batfish: {bf_iface.speed}, Fortios: {fortios_speed}"

    return diff


class FortiosValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        raise ValidationError("Not implemented")

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        raise ValidationError("Not implemented")

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> dict[Any, Any]:
        """Validating interfaces"""
        fortios_ifaces, fortios_phys_ifaces = self._get_interfaces()
        diffs: dict[Any, Any] = {}

        batfish_ifaces = {i.name.lower(): i for i in batfish_interfaces}
        real_phys_ifaces = {i.name.lower(): i for i in fortios_phys_ifaces}
        real_ifaces = {i.name.lower(): i for i in fortios_ifaces}

        for name in batfish_ifaces.keys() - real_ifaces.keys():
            diffs[name] = f"Extra interface in Batfish: {batfish_ifaces[name]}"
        for name, iface in real_ifaces.items():
            skip_iface = {
                # interface 'fortilink' is management interface to manage L2 fortiswitch
                "fortilink"
            }
            if name in skip_iface:
                continue
            if name not in batfish_ifaces:
                diffs[name] = f"Missing interface in Batfish: {iface}"
                continue
            diff = _compare_interfaces(
                iface, real_phys_ifaces.get(name), batfish_ifaces[name]
            )
            if diff:
                diffs[name] = diff
        return diffs

    def _get_interfaces(
        self,
    ) -> tuple[Sequence[FortiosInterface], Sequence[FortiosPhysicalInterface]]:
        """
        Parses and returns a tuple containing a list of interfaces and a list of physical interfaces.
        The physical interface list should be a subset of the first, full interface list.
        """
        ifaces_path = self.device_path / "get_system_interface.txt"
        ifaces_physical_path = self.device_path / "get_system_interface_physical.txt"
        if not ifaces_path.is_file() or not ifaces_physical_path.is_file():
            raise FileNotFoundError(
                "Interfaces file(s) not found (get_system_interface or get_system_interface_physical)"
            )
        return (
            parse_get_system_interface(ifaces_path.read_text()),
            parse_get_system_interface_physical(ifaces_physical_path.read_text()),
        )
