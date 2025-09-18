import attr


@attr.s(frozen=True, auto_attribs=True)
class FrrInterface:
    """Captures runtime properties of an interface."""

    name: str
    bandwidth: int
    mtu: int
    admin: bool
    line: bool | None
