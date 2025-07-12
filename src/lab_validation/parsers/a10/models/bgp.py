from typing import Optional, Sequence, Text, Union

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class A10BgpRoute(object):
    valid: bool
    best: bool
    network: Text = attr.ib(converter=normalized_network)
    next_hop_ip: Text
    metric: int
    local_preference: Optional[int] = attr.ib(converter=optional_int_converter)
    weight: int
    type: Optional[Text]
    as_path: Sequence[Union[int, Sequence[int]]]
    origin_type: Text
