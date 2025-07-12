from typing import Optional, Text, Union

import attr


def _optional_bw(x: Optional[Text]) -> Optional[Union[int, Text]]:
    if x is None:
        return None
    if x == "Unlimited":
        return "Unlimited"
    return int(x)


@attr.s(frozen=True, auto_attribs=True)
class JunosInterfaceState(object):
    """Runtime interface state."""

    admin: bool
    line: bool


@attr.s(frozen=True, auto_attribs=True)
class JunosInterface(object):
    """Captures runtime properties of an interface."""

    name: Text
    state: JunosInterfaceState
    speed: Optional[int]
    bandwidth: Optional[int]  # in bits per second
    mtu: Optional[Union[int, Text]] = attr.ib(converter=_optional_bw)  # in bytes
    interface_type: Text
