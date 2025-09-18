from collections.abc import Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrIpRoute:
    """Route representing one route in the 'show ip route' command."""

    network: str = attr.ib(converter=normalized_network)
    vrf: str | None
    protocol: str
    next_hop_ip: str | None
    admin_distance: int | None = attr.ib(converter=optional_int_converter)
    next_hop_int: str | None
    metric: int | None = attr.ib(converter=optional_int_converter)
    active: bool | None
    blackhole: bool | None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrBgpRouteNextHop:
    """Represents the next hop of a BGP route for FRR."""

    is_used: bool
    ip: str
    afi: str
    # populated when afi is ipv6
    scope: str | None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrBgpRoute:
    """Represents BGP route for FRR."""

    vrf: str
    network: str = attr.ib(converter=normalized_network)
    is_valid: bool
    is_multipath: bool
    is_bestpath: bool
    origin: str
    path_from: str
    peer_id: str
    next_hops: Sequence[FrrBgpRouteNextHop]
    med: int | None = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    weight: int
