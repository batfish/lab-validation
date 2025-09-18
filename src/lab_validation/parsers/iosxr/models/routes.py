from typing import Optional

import attr

from ...common.utils import normalized_network


@attr.s(frozen=True, kw_only=True)
class IosXrRoute:
    """Route representing one route in the XR 'show route' command."""

    # Route Key
    vrf = attr.ib(type=Optional[str], default="default")
    network = attr.ib(type=str, converter=normalized_network)
    protocol = attr.ib(type=str)
    next_hop_ip = attr.ib(type=Optional[str])

    # Route attributes
    admin = attr.ib(type=int, converter=attr.converters.optional(int))
    metric = attr.ib(type=int, converter=attr.converters.optional(int))
    next_hop_int = attr.ib(type=Optional[str])
    next_hop_vrf = attr.ib(type=Optional[str])

    backup = attr.ib(type=bool, default=False)
