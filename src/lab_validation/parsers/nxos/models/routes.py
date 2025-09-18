from collections.abc import Sequence

import attr

from lab_validation.parsers.common.utils import normalized_network


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class NxosMainRibRoute:
    vrf: str
    network: str = attr.ib(converter=normalized_network)
    protocol: str
    next_hop_ip: str | None
    next_hop_int: str | None
    next_vrf: str | None
    admin: int = attr.ib(converter=int)
    metric: int
    tag: int | None
    evpn: bool
    segid: int | None
    tunnelid: str | None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class NxosBgpRoute:
    vrf: str
    network: str = attr.ib(converter=normalized_network)
    protocol: str
    next_hop_ip: str
    metric: int | None
    local_preference: int
    weight: int
    as_path: Sequence[int]
    best_path: bool
    origin_type: str
