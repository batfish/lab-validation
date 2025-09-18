"""Interface properties data model."""

from typing import Any

import attr


def optional_int_converter(val: Any) -> int | None:
    """Convert value to int if not None."""
    return int(val) if val is not None else None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class InterfaceProperties:
    """Network interface properties from Batfish interfaceProperties query."""

    name: str
    access_vlan: int | None = attr.ib(converter=optional_int_converter, default=None)
    active: bool
    all_prefixes: list[str]
    allowed_vlans: str | None
    bandwidth: int
    description: str | None
    native_vlan: int | None = attr.ib(converter=optional_int_converter, default=None)
    mtu: int
    speed: int
    switchport: bool
    switchport_mode: str | None
    vrf: str
