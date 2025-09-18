from collections.abc import Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class A10BgpRoute:
    valid: bool
    best: bool
    network: str = attr.ib(converter=normalized_network)
    next_hop_ip: str
    metric: int
    local_preference: int | None = attr.ib(converter=optional_int_converter)
    weight: int
    type: str | None
    as_path: Sequence[int | Sequence[int]]
    origin_type: str
