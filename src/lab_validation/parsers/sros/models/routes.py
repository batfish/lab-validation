from collections.abc import Sequence

import attr

from ...common.utils import normalized_network, optional_int_converter


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SrosIpRoute:
    """One route from ``info json /state router "Base" route-table`` (FIB/RTM).

    SR OS reports the active route per prefix in the route table. ``protocol`` is
    the SR OS owner string (e.g. ``local``, ``bgp``, ``static``, ``isis``,
    ``ospf``); ``next_hop_ip`` is the (possibly indirect) next-hop IP, or ``None``
    for a local/connected route whose next-hop is an interface.
    """

    network: str = attr.ib(converter=normalized_network)
    vrf: str
    protocol: str
    next_hop_ip: str | None
    # Egress interface name of the next-hop, resolved from the route's nexthop
    # if-index against the interface state. Present for connected/local routes
    # and for resolved static/IGP routes (which carry both an if-index and a
    # nexthop-ip); None for a blackhole or an unresolved next-hop.
    next_hop_interface: str | None = None
    preference: int | None = attr.ib(converter=optional_int_converter)
    metric: int | None = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SrosBgpRoute:
    """One best route from the BGP local RIB (``info json /state router "Base"
    bgp rib``), with attributes joined in from the rib's attribute-set table.

    ``owner`` is ``local`` (locally originated) or ``bgp`` (learned from a peer).
    """

    network: str = attr.ib(converter=normalized_network)
    vrf: str
    owner: str
    neighbor: str
    next_hop_ip: str | None
    origin_type: str
    med: int | None = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    used: bool
    valid: bool
    best: bool
