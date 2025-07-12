from typing import Optional, Text

import attr

from ...common.utils import normalized_network
from .util import canonicalize_interface_opt


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class A10MainRibRoute(object):
    """Route representing one route in the 'show ip route all' command."""

    network: Text = attr.ib(converter=normalized_network)
    protocol: Text
    next_hop_ip: Optional[Text]
    next_hop_int: Optional[Text] = attr.ib(converter=canonicalize_interface_opt)
    admin: int = attr.ib(converter=int)
    metric: int = attr.ib(converter=int)
