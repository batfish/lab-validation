import attr


@attr.s(frozen=True, auto_attribs=True)
class AristaInterface(object):
    """Captures runtime properties of an interface."""

    name: str
    bandwidth: int
    mtu: int
    line: bool
