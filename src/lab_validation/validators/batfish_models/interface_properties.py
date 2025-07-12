"""Interface properties data model."""

from typing import Any, List, Optional

import attr


def optional_int_converter(val: Any) -> Optional[int]:
    """Convert value to int if not None."""
    return int(val) if val is not None else None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class InterfaceProperties:
    """Network interface properties from Batfish interfaceProperties query."""

    name: str
    access_vlan: Optional[int] = attr.ib(converter=optional_int_converter, default=None)
    active: bool
    all_prefixes: List[str]
    allowed_vlans: Optional[str]
    bandwidth: int
    description: Optional[str]
    native_vlan: Optional[int] = attr.ib(converter=optional_int_converter, default=None)
    mtu: int
    speed: int
    switchport: bool
    switchport_mode: Optional[str]
    vrf: str
