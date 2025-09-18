"""Abstract base class for vendor-specific network validation.

This module provides the VendorValidator abstract base class that defines the interface
for validating Batfish network analysis results against real network device data.
"""

from abc import ABC
from collections.abc import Sequence
from typing import Any

from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
)
from lab_validation.validators.batfish_models.runtime_data import NodeRuntimeData


class ValidationError(Exception):
    """The exception we throw when validation fails."""


class VendorValidator(ABC):
    """Abstract class for common vendor validator APIs."""

    def get_runtime_data(self) -> NodeRuntimeData:
        """Returns the runtime data for this node."""
        raise ValidationError("Not implemented")

    def validate_interface_properties(
        self, batfish_interfaces: Sequence[InterfaceProperties]
    ) -> dict[Any, Any]:
        raise ValidationError("Not implemented")

    def validate_main_rib_routes(
        self, routes: Sequence[MainRibRoute]
    ) -> dict[Any, Any]:
        raise ValidationError("Not implemented")

    def validate_bgp_rib_routes(
        self, bgp_routes: Sequence[BgpRibRoute]
    ) -> dict[Any, Any]:
        raise ValidationError("Not implemented")

    def validate_evpn_rib_routes(
        self, evpn_routes: Sequence[EvpnRibRoute]
    ) -> dict[Any, Any]:
        # Batfish does not support EVPN in many vendors and we don't build many labs.
        # As soon as we add a lab for a given vendor, we will have to override this implementation.
        if not evpn_routes:
            return {}
        return {"Problem": "Time to implement EVPN validation"}
