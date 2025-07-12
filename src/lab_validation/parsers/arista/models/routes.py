from typing import Optional, Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaIpRoute(object):
    """Route representing one route in the 'show ip route' command."""

    network: str = attr.ib(converter=normalized_network)
    vrf: str
    protocol: str

    # Next hops
    next_hop_ip: Optional[str]
    vni: Optional[int]
    vtep_ip: Optional[str]

    # Route attributes
    preference: Optional[int] = attr.ib(converter=optional_int_converter)
    next_hop_int: Optional[str]
    metric: Optional[int] = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaBgpRoute(object):
    vrf: str
    is_active: bool
    is_ecmp: bool
    not_installed_reason: Optional[str]
    network: str = attr.ib(converter=normalized_network)
    next_hop_ip: Optional[str]
    metric: Optional[int] = attr.ib(converter=optional_int_converter)
    local_preference: Optional[int] = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    weight: Optional[int] = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class AristaEvpnRoute(object):
    vrf: str
    is_active: bool
    network: str = attr.ib(converter=normalized_network)
    next_hop_ip: Optional[str]
    local_preference: Optional[int] = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    as_path_type: str
    weight: Optional[int]
    origin: str

    # Evpn attributes
    route_distinguisher: str
