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
    """One route from a BGP RIB view (``info json /state router "Base" bgp rib``),
    with path attributes joined in from the rib's attribute-set table.

    The bgp-rib state has several views, each with its own attr-sets: ``local-rib``
    (the local RIB), ``rib-in-pre``/``rib-in-post`` (received from a peer, before/
    after import policy), and ``rib-out-post`` (advertised to a peer, after export
    policy). ``rib_view`` records which view this route came from. ``owner`` is
    ``local`` (locally originated) or ``bgp`` (learned). ``communities`` are the
    standard communities on the attr-set; extended/large communities and other
    advanced attributes are available in the same attr-set and can be added here.
    """

    network: str = attr.ib(converter=normalized_network)
    vrf: str
    owner: str
    neighbor: str
    next_hop_ip: str | None
    origin_type: str
    med: int | None = attr.ib(converter=optional_int_converter)
    as_path: Sequence[int]
    communities: Sequence[str] = ()
    used: bool = False
    valid: bool = False
    best: bool = False
    # Which RIB view this route came from: "local-rib", "rib-in-post", "rib-out-post", etc.
    rib_view: str = "local-rib"
