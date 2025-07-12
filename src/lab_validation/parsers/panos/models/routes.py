from typing import Optional, Set, Text

import attr

from ...common.utils import normalized_network


# Example:
# destination nexthop metric flags age interface next-AS
# 10.102.7.51/32 10.102.3.39 A B E 621201 ethernet1/21.100 64920
@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class PanosMainRibRoute(object):
    virtual_router: Text
    network: Text = attr.ib(converter=normalized_network)
    next_hop_ip: Text
    metric: Optional[int]
    flags: Set[Text]
    age: Optional[int]
    next_hop_int: Optional[Text]
    next_AS: Optional[int]

    def is_active(self) -> bool:
        return "A" in self.flags

    def get_protocol(self) -> str:
        if "B" in self.flags:
            return "bgp"
        if "C" in self.flags:
            return "connected"
        if "S" in self.flags:
            return "static"
        if "H" in self.flags:
            # TODO: verify
            return "local"
        if "~" in self.flags:
            # TODO: what does this mean?
            return "internal"
        raise ValueError("Unknown protocol for route " + str(self))
