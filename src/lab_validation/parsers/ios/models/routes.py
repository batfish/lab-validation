# coding: utf-8
from typing import Optional, Text

import attr

from ...common.utils import normalized_network


@attr.s(frozen=True, kw_only=True)
class IosIpRoute(object):
    """Route representing one route in the 'show ip route' command."""

    # Route Key
    vrf = attr.ib(type=Optional[Text], default="default")
    network = attr.ib(type=Text, converter=normalized_network)
    protocol = attr.ib(type=Text)
    next_hop_ip = attr.ib(type=Optional[Text])

    # Route attributes
    admin = attr.ib(type=int, converter=attr.converters.optional(int))
    metric = attr.ib(type=int, converter=attr.converters.optional(int))
    next_hop_int = attr.ib(type=Optional[Text])
