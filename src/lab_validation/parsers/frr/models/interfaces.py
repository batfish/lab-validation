from typing import Optional, Text

import attr


@attr.s(frozen=True, auto_attribs=True)
class FrrInterface(object):
    """Captures runtime properties of an interface."""

    name: Text
    bandwidth: int
    mtu: int
    admin: bool
    line: Optional[bool]
