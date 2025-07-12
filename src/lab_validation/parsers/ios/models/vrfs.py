# coding: utf-8
from typing import Optional, Sequence, Text

import attr


@attr.s(frozen=True)
class Vrf(object):
    """Represents one vrf in the 'show vrfs' command."""

    name = attr.ib(type=Text, kw_only=True)
    default_rd = attr.ib(type=Optional[Text], kw_only=True)
    protocols = attr.ib(type=Sequence[Text], kw_only=True, factory=list)
    interfaces = attr.ib(type=Sequence[Text], kw_only=True, factory=list)
