import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class SonicInterfaceStatus:
    """One row of SONiC 'show interfaces status'."""

    name: str
    speed: float  # bits per second
    mtu: int
    oper_up: bool
    admin_up: bool
