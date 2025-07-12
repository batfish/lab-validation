from typing import Optional, Sequence, Text

import attr

from lab_validation.parsers.common.utils import normalized_network


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class NxosMainRibRoute(object):
    vrf: Text
    network: Text = attr.ib(converter=normalized_network)
    protocol: Text
    next_hop_ip: Optional[Text]
    next_hop_int: Optional[Text]
    next_vrf: Optional[Text]
    admin: int = attr.ib(converter=int)
    metric: int
    tag: Optional[int]
    evpn: bool
    segid: Optional[int]
    tunnelid: Optional[str]


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class NxosBgpRoute(object):
    vrf: Text
    network: Text = attr.ib(converter=normalized_network)
    protocol: Text
    next_hop_ip: Text
    metric: Optional[int]
    local_preference: int
    weight: int
    as_path: Sequence[int]
    best_path: bool
    origin_type: Text
