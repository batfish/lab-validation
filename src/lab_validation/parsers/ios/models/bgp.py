from collections.abc import Sequence
from typing import Optional

import attr

from ...common.utils import normalized_network


@attr.s(frozen=True)
class IosBgpRoute:
    """One route in one vrf in one address-family in the IOS/XE 'show bgp all' command."""

    network = attr.ib(type=str, kw_only=True, converter=normalized_network)
    next_hop_ip = attr.ib(type=Optional[str], kw_only=True)
    best_path = attr.ib(type=bool, kw_only=True)
    metric = attr.ib(type=int, kw_only=True)
    local_preference = attr.ib(type=int, kw_only=True)
    weight = attr.ib(type=int, kw_only=True)
    # TODO: need show data with as-sets so we can do better parsing
    as_path = attr.ib(type=Sequence[int], kw_only=True)
    origin_type = attr.ib(type=str, kw_only=True)


@attr.s(frozen=True)
class IosBgpVrf:
    """One vrf in one address-family in the IOS/XE 'show bgp all' command."""

    name = attr.ib(type=str, kw_only=True)
    route_distinguisher = attr.ib(type=Optional[str], kw_only=True)
    routes = attr.ib(type=Sequence[IosBgpRoute], kw_only=True)


@attr.s(frozen=True)
class IosBgpAddressFamily:
    """One address-family in the IOS/XE 'show bgp all' command."""

    name = attr.ib(type=str, kw_only=True)
    router_id = attr.ib(type=Optional[str], kw_only=True)
    vrfs = attr.ib(type=Sequence[IosBgpVrf], kw_only=True)
