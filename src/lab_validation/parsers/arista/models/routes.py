from collections.abc import Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaIpRoute:
    """Route representing one route in the 'show ip route' command."""

    network: str = attr.ib(converter=normalized_network)
    vrf: str
    protocol: str

    # Next hops
    next_hop_ip: str | None
    vni: int | None
    vtep_ip: str | None

    # Route attributes
    preference: int | None = attr.ib(converter=optional_int_converter)
    next_hop_int: str | None
    metric: int | None = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaBgpRoute:
    vrf: str
    is_active: bool
    is_ecmp: bool
    not_installed_reason: str | None
    network: str = attr.ib(converter=normalized_network)
    next_hop_ip: str | None
    metric: int | None = attr.ib(converter=optional_int_converter)
    local_preference: int | None = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    weight: int | None = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaEvpnRoute:
    vrf: str
    is_active: bool
    network: str = attr.ib(converter=normalized_network)
    next_hop_ip: str | None
    local_preference: int | None = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    as_path_type: str
    weight: int | None
    origin: str

    # Evpn attributes
    route_distinguisher: str
