import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SrosInterface:
    """Runtime properties of an SR OS router interface.

    Parsed from ``info json /state router "Base" interface``. SR OS router
    interfaces are L3 interfaces (the analog of an IOS/Arista interface that has
    an IP); ``oper-state`` is the operational up/down. ``primary_address`` is the
    operational IPv4 primary address (the prefix length is not in the interface
    state tree, so it is not modeled here).
    """

    name: str
    oper_up: bool
    ipv4_up: bool
    primary_address: str | None
