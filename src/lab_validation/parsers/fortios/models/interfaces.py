from typing import Optional, Text

import attr


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FortiosInterface(object):
    """Captures runtime properties of an interface."""

    name: Text
    mode: Optional[Text]
    ip_addr: Optional[Text]
    ip_mask: Optional[Text]
    status: Text
    type: Text


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class FortiosPhysicalInterface(object):
    """Captures runtime properties of a physical interface."""

    name: Text
    mode: Text
    # Addr and mask are either both set or neither is set
    ip_addr: Optional[Text]
    ip_mask: Optional[Text]
    ipv6_addr: Optional[Text]
    status: Text
    speed: Optional[int]
    bit_rate_unit: Optional[Text]
    duplex: Optional[Text]
