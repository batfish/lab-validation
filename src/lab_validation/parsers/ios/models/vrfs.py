from collections.abc import Sequence
from typing import Optional

import attr


@attr.s(frozen=True)
class Vrf:
    """Represents one vrf in the 'show vrfs' command."""

    name = attr.ib(type=str, kw_only=True)
    default_rd = attr.ib(type=Optional[str], kw_only=True)
    protocols = attr.ib(type=Sequence[str], kw_only=True, factory=list)
    interfaces = attr.ib(type=Sequence[str], kw_only=True, factory=list)
