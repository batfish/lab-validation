import re

import attr


@attr.s(frozen=True, auto_attribs=True)
class NxosInterface:
    """Captures runtime properties of an interface."""

    name: str
    bandwidth: int
    mtu: int
    admin: bool
    line: bool | None
    mode: str | None

    def is_physical(self) -> bool:
        return re.fullmatch("Ethernet\\d+(/\\d+)*", self.name) is not None
