from typing import Optional, Sequence, Text

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class JunosMainRibRoute(object):
    # Route key
    network: Text = attr.ib(converter=normalized_network)
    vrf: Text
    protocol: Text
    next_hop_ip: Optional[Text]

    # Route attributes
    active: bool
    admin: int = attr.ib(converter=int)
    next_hop_int: Optional[Text]
    metric: Optional[int] = attr.ib(converter=optional_int_converter)
    nh_type: Optional[Text]


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class JunosBgpRoute(object):
    vrf: Text
    network: Text = attr.ib(converter=normalized_network)
    is_active: bool
    origin_protocol: Text
    next_hop_ip: Text
    next_hop_int: Text
    preference: int = attr.ib(converter=int)
    metric: Optional[int] = attr.ib(converter=optional_int_converter)
    local_preference: int = attr.ib(converter=int)
    as_path: Sequence[int]
    origin_type: str
