"""Route data models."""

from typing import List, Optional, Sequence, Tuple, Union

import attr
from pybatfish.datamodel import NextHop

from lab_validation.parsers.common.utils import (
    normalized_network,
    optional_int_converter,
)


def convert_as_path(
    text: Union[str, Sequence[Union[int, Sequence[int]]]],
) -> Sequence[Union[int, Sequence[int]]]:
    """Convert Batfish AS path string to tuple of AS sets."""
    if not isinstance(text, str):
        return text

    ret: List[Union[int, Tuple[int, ...]]] = []
    text_parts = text.split()
    current_as_set: Optional[List[int]] = None

    for part in text_parts:
        if part.startswith("("):
            assert current_as_set is None
            current_as_set = []

        if part.strip("()"):
            current_as = int(part.strip("()"))
            if current_as_set is not None:
                current_as_set.append(current_as)
            else:
                ret.append(current_as)

        if part.endswith(")"):
            assert current_as_set is not None
            ret.append(tuple(current_as_set))
            current_as_set = None

    assert current_as_set is None
    return tuple(ret)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class MainRibRoute:
    """Main RIB route from Batfish routes query."""

    vrf: str
    network: str = attr.ib(converter=normalized_network)
    next_hop: NextHop
    protocol: str
    metric: int = attr.ib(converter=int)
    admin: int = attr.ib(converter=int)
    tag: Optional[int] = attr.ib(converter=optional_int_converter)


@attr.s(frozen=True, auto_attribs=True)
class BgpRibRoute:
    """BGP RIB route from Batfish routes(rib='bgp') query."""

    vrf: str = attr.ib(kw_only=True)
    network: str = attr.ib(kw_only=True, converter=normalized_network)
    next_hop: NextHop
    next_hop_ip: Optional[str] = attr.ib(kw_only=True)
    next_hop_int: str = attr.ib(kw_only=True)
    protocol: str = attr.ib(kw_only=True)
    as_path: Sequence[Union[int, Sequence[int]]] = attr.ib(
        converter=convert_as_path, kw_only=True
    )
    metric: int = attr.ib(converter=int, kw_only=True)
    local_preference: int = attr.ib(converter=int, kw_only=True)
    communities: Sequence[str] = attr.ib(converter=tuple, kw_only=True)
    origin_protocol: Optional[str] = attr.ib(kw_only=True)
    origin_type: str = attr.ib(kw_only=True)
    weight: int = attr.ib(converter=int, kw_only=True)
    tag: Optional[int] = attr.ib(converter=optional_int_converter, kw_only=True)


@attr.s(frozen=True, auto_attribs=True, kw_only=True)
class EvpnRibRoute:
    """EVPN RIB route from Batfish routes(rib='evpn') query."""

    vrf: str
    network: str = attr.ib(converter=normalized_network)
    route_distinguisher: str
    next_hop: NextHop
    next_hop_ip: str
    next_hop_int: str
    protocol: str
    as_path: Sequence[Union[int, Sequence[int]]] = attr.ib(converter=convert_as_path)
    metric: int = attr.ib(converter=int)
    local_preference: int = attr.ib(converter=int)
    communities: Sequence[str]
    origin_protocol: Optional[str]
    origin_type: str
    tag: Optional[int] = attr.ib(converter=optional_int_converter)
