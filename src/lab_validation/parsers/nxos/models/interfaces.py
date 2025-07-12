import re
from typing import Optional, Text

import attr


@attr.s(frozen=True, auto_attribs=True)
class NxosInterface(object):
    """Captures runtime properties of an interface."""

    name: Text
    bandwidth: int
    mtu: int
    admin: bool
    line: Optional[bool]
    mode: Optional[Text]

    def is_physical(self) -> bool:
        return re.fullmatch("Ethernet\\d+(/\\d+)*", self.name) is not None
