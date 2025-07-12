from pathlib import Path
from typing import Any, Dict, Iterable, Sequence, Text

from lab_validation.parsers.checkpoint.commands.interfaces import parse_show_interfaces
from lab_validation.parsers.checkpoint.models.interfaces import CheckpointInterface
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData

from .vendor_validator import ValidationError, VendorValidator


class CheckpointGaiaValidator(VendorValidator):
    def __init__(self, device_path: Path) -> None:
        self.device_path: Path = device_path

    def get_runtime_data(self) -> NodeRuntimeData:
        """Currently produces empty NodeRuntimeData. Pending show interfaces"""
        return NodeRuntimeData()

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> Dict[Any, Any]:
        """Validating main RIB routes from all VRFs"""
        raise ValidationError("Not implemented")

    def validate_bgp_rib_routes(
        self, batfish_routes: Sequence[BgpRibRoute]
    ) -> Dict[Any, Any]:
        """Validating BGP RIB routes from all VRFs"""
        raise ValidationError("Not implemented")

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> Dict[Any, Any]:
        """Validating interfaces"""
        if_file = self.device_path / "show_interfaces_all.txt"
        cp_ifaces = parse_show_interfaces(if_file.read_text())
        return CheckpointGaiaValidator._compare_all_interfaces(
            cp_ifaces, batfish_interfaces
        )

    @staticmethod
    def _compare_all_interfaces(
        cp_ifaces: Iterable[CheckpointInterface],
        bf_ifaces: Iterable[InterfaceProperties],
    ) -> Dict[Text, Any]:
        diffs: Dict[Text, Any] = {}
        bf_dict = {i.name.lower(): i for i in bf_ifaces}
        cp_dict = {i.name.lower(): i for i in cp_ifaces}

        for name in bf_dict.keys() - cp_dict.keys():
            diffs[name] = f"Extra interface in Batfish: {bf_dict[name]}"
        for name, iface in cp_dict.items():
            if name not in bf_dict:
                diffs[name] = f"Missing interface in Batfish: {cp_dict[name]}"
                continue
            diff = CheckpointGaiaValidator._compare_interfaces(iface, bf_dict[name])
            if diff:
                diffs[name] = diff
        return diffs

    @staticmethod
    def _compare_interfaces(
        iface: CheckpointInterface,
        bf_iface: InterfaceProperties,
    ) -> Dict[Text, Text]:
        diff = {}

        if bf_iface.active != iface.state:
            diff["active"] = f"Batfish: {bf_iface.active}, Checkpoint: {iface.state}"

        # Checkpoint doesn't show speed for bond, vlan, or loopback interfaces
        if bf_iface.speed != iface.speed and iface.type not in {
            "loopback",
            "bond",
            "vlan",
        }:
            diff["speed"] = f"Batfish: {bf_iface.speed}, Checkpoint: {iface.speed}"

        # TODO: compare primary address instead of all prefixes
        if iface.prefix and iface.prefix not in bf_iface.all_prefixes:
            diff[
                "ipv4 address"
            ] = f"Batfish: {bf_iface.all_prefixes}, Checkpoint: {iface.prefix}"

        if bf_iface.mtu != iface.mtu:
            diff["mtu"] = f"Batfish: {bf_iface.mtu}, Checkpoint: {iface.mtu}"

        return diff
