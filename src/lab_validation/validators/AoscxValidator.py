"""Validation of collected Aruba AOS-CX CLI output."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Any

from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import (
    InterfaceRuntimeData,
    NodeRuntimeData,
)

from .utils.validation_utils import CostResult, match_pairs, matched_pairs_to_failures
from .vendor_validator import VendorValidator


@dataclass(frozen=True)
class _Interface:
    name: str
    active: bool
    prefixes: tuple[str, ...]
    mtu: int | None


@dataclass(frozen=True)
class _Route:
    network: str
    nexthop: str | None
    interface: str
    protocol: str


_INTERFACE_BLOCK = re.compile(
    r"(?ms)^Interface (?P<name>.+?) is (?P<state>up|down) .+?(?=^Interface |\Z)"
)
_PREFIX = re.compile(r"^\s*IPv4 address (?P<prefix>\S+)", re.MULTILINE)
_MTU = re.compile(r"^\s*MTU (?P<mtu>\d+)", re.MULTILINE)
_ROUTE = re.compile(
    r"^(?P<network>\S+)\s+(?P<nexthop>\S+)\s+"
    r"(?P<interface>\S+)\s+\S+\s+(?P<protocol>[A-Z]+)\s+"
    r"\[(?P<admin>\d+)/(?P<metric>\d+)\]",
    re.MULTILINE,
)


class AoscxValidator(VendorValidator):
    """Compare AOS-CX interface and IPv4 route state with Batfish."""

    def __init__(self, device_path: str | Path) -> None:
        self.device_path = Path(device_path)

    def get_runtime_data(self) -> NodeRuntimeData:
        return NodeRuntimeData(
            interfaces={
                interface.name: InterfaceRuntimeData(lineUp=interface.active)
                for interface in self._interfaces()
            }
        )

    def validate_interface_properties(
        self,
        batfish_interfaces: Sequence[InterfaceProperties],
        vni_ifaces: AbstractSet[str],
    ) -> dict[Any, Any]:
        actual = {interface.name.lower(): interface for interface in self._interfaces()}
        differences: dict[Any, Any] = {}
        for expected in batfish_interfaces:
            if expected.name.lower() == "mgmt":
                continue
            interface = actual.get(expected.name.lower())
            if interface is None:
                differences[expected.name] = "Missing interface in AOS-CX output"
                continue
            if expected.active != interface.active:
                differences[expected.name] = (
                    f"Batfish active={expected.active}, "
                    f"AOS-CX active={interface.active}"
                )
            if interface.mtu is not None and expected.mtu != interface.mtu:
                differences[expected.name] = (
                    f"Batfish MTU={expected.mtu}, AOS-CX MTU={interface.mtu}"
                )
            if sorted(expected.all_prefixes) != sorted(interface.prefixes):
                differences[expected.name] = (
                    f"Batfish prefixes={expected.all_prefixes}, "
                    f"AOS-CX prefixes={interface.prefixes}"
                )
        return differences

    def validate_main_rib_routes(
        self, batfish_routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        expected_routes = [route for route in batfish_routes if route.vrf == "default"]
        return matched_pairs_to_failures(
            match_pairs(self._routes(), expected_routes, self._route_cost)
        )

    def validate_bgp_rib_routes(self, routes: Sequence[BgpRibRoute]) -> dict[Any, Any]:
        return {}

    def _interfaces(self) -> list[_Interface]:
        text = (self.device_path / "show_interface.txt").read_text()
        interfaces = []
        for match in _INTERFACE_BLOCK.finditer(text):
            block = match.group(0)
            mtu = _MTU.search(block)
            interfaces.append(
                _Interface(
                    name=match.group("name"),
                    active=match.group("state") == "up"
                    and "Admin state is up" in block,
                    prefixes=tuple(_PREFIX.findall(block)),
                    mtu=int(mtu.group("mtu")) if mtu else None,
                )
            )
        return interfaces

    def _routes(self) -> list[_Route]:
        text = (self.device_path / "show_ip_route.txt").read_text()
        return [
            _Route(
                network=match.group("network"),
                nexthop=None
                if match.group("nexthop") == "-"
                else match.group("nexthop"),
                interface=match.group("interface"),
                protocol=self._protocol(match.group("protocol")),
            )
            for match in _ROUTE.finditer(text)
        ]

    @staticmethod
    def _protocol(protocol: str) -> str:
        return {"C": "connected", "L": "connected", "S": "static"}.get(
            protocol, protocol
        )

    @staticmethod
    def _route_cost(actual: _Route, expected: MainRibRoute) -> CostResult:
        if actual.network != expected.network:
            return [("network", math.inf)]
        if actual.protocol != expected.protocol:
            return [("protocol", math.inf)]
        if hasattr(expected.next_hop, "ip"):
            if actual.nexthop != expected.next_hop.ip:
                return [("next_hop_ip", math.inf)]
        elif hasattr(expected.next_hop, "interface"):
            if actual.interface != expected.next_hop.interface:
                return [("next_hop_interface", math.inf)]
        elif actual.nexthop is not None:
            return [("next_hop", math.inf)]
        return []
