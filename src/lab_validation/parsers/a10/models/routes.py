import attr

from ...common.utils import normalized_network
from .util import canonicalize_interface_opt


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class A10MainRibRoute:
    """Route representing one route in the 'show ip route all' command."""

    network: str = attr.ib(converter=normalized_network)
    protocol: str
    next_hop_ip: str | None
    next_hop_int: str | None = attr.ib(converter=canonicalize_interface_opt)
    admin: int = attr.ib(converter=int)
    metric: int = attr.ib(converter=int)
