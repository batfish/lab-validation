from typing import Optional, Text

import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class CheckpointInterface(object):
    """Captures runtime properties of an interface."""

    name: Text
    state: bool
    type: Text
    # TODO Worth parsing link-state? When is link-state different from overall state?
    mtu: int
    # Speed in bits/sec
    speed: Optional[int]
    prefix: Optional[Text]
