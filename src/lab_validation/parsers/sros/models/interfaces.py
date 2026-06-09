import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SrosInterface:
    """Runtime properties of an SR OS router interface.

    Parsed from ``info json /state router "Base" interface``. SR OS router
    interfaces are L3 interfaces (the analog of an IOS/Arista interface that has
    an IP); ``oper-state`` is the operational up/down. ``primary_address`` is the
    operational IPv4 primary address (the prefix length is not in the interface
    state tree, so it is not modeled here).

    The interface state tree exposes the IP MTU (``oper-ip-mtu``) but not
    bandwidth/speed/MAC — those live in the separate ``/state port`` tree, which
    this validator does not consume (SR OS L3 router-interfaces are port-less or
    bind a port; the L1 port properties are out of scope for the RIB/L3 checks).
    """

    name: str
    oper_up: bool
    ipv4_up: bool
    primary_address: str | None
    # SR OS interface index; route nexthops reference it by if-index, so it is
    # used to resolve a route's egress interface back to its name.
    if_index: int | None = None
    # Operational IP MTU (oper-ip-mtu).
    mtu: int | None = None
