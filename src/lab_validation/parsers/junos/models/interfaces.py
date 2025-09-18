import attr


def _optional_bw(x: str | None) -> int | str | None:
    if x is None:
        return None
    if x == "Unlimited":
        return "Unlimited"
    return int(x)


@attr.s(frozen=True, auto_attribs=True)
class JunosInterfaceState:
    """Runtime interface state."""

    admin: bool
    line: bool


@attr.s(frozen=True, auto_attribs=True)
class JunosInterface:
    """Captures runtime properties of an interface."""

    name: str
    state: JunosInterfaceState
    speed: int | None
    bandwidth: int | None  # in bits per second
    mtu: int | str | None = attr.ib(converter=_optional_bw)  # in bytes
    interface_type: str
