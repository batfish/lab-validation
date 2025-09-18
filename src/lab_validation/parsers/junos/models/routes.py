from collections.abc import Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class JunosMainRibRoute:
    # Route key
    network: str = attr.ib(converter=normalized_network)
    vrf: str
    protocol: str
    next_hop_ip: str | None

    # Route attributes
    active: bool
    admin: int = attr.ib(converter=int)
    next_hop_int: str | None
    metric: int | None = attr.ib(converter=optional_int_converter)
    nh_type: str | None


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class JunosBgpRoute:
    vrf: str
    network: str = attr.ib(converter=normalized_network)
    is_active: bool
    origin_protocol: str
    next_hop_ip: str
    next_hop_int: str
    preference: int = attr.ib(converter=int)
    metric: int | None = attr.ib(converter=optional_int_converter)
    local_preference: int = attr.ib(converter=int)
    as_path: Sequence[int]
    origin_type: str
