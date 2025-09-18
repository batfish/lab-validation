import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FortiosInterface:
    """Captures runtime properties of an interface."""

    name: str
    mode: str | None
    ip_addr: str | None
    ip_mask: str | None
    status: str
    type: str


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FortiosPhysicalInterface:
    """Captures runtime properties of a physical interface."""

    name: str
    mode: str
    # Addr and mask are either both set or neither is set
    ip_addr: str | None
    ip_mask: str | None
    ipv6_addr: str | None
    status: str
    speed: int | None
    bit_rate_unit: str | None
    duplex: str | None
