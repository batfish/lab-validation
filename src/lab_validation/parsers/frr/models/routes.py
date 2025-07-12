from typing import Optional, Sequence, Text

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrIpRoute(object):
    """Route representing one route in the 'show ip route' command."""

    network: Text = attr.ib(converter=normalized_network)
    vrf: Optional[Text]
    protocol: Text
    next_hop_ip: Optional[Text]
    admin_distance: Optional[int] = attr.ib(converter=optional_int_converter)
    next_hop_int: Optional[Text]
    metric: Optional[int] = attr.ib(converter=optional_int_converter)
    active: Optional[bool]
    blackhole: Optional[bool]


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrBgpRouteNextHop(object):
    """Represents the next hop of a BGP route for FRR."""

    is_used: bool
    ip: Text
    afi: Text
    # populated when afi is ipv6
    scope: Optional[Text]


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FrrBgpRoute(object):
    """Represents BGP route for FRR."""

    vrf: Text
    network: Text = attr.ib(converter=normalized_network)
    is_valid: bool
    is_multipath: bool
    is_bestpath: bool
    origin: Text
    path_from: Text
    peer_id: Text
    next_hops: Sequence[FrrBgpRouteNextHop]
    med: Optional[int] = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    weight: int
