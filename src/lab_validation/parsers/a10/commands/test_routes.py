import textwrap

import pytest

from lab_validation.parsers.a10.commands.routes import (
    parse_show_ip_route_acos,
    parse_show_ip_route_all,
)
from lab_validation.parsers.a10.models.routes import A10MainRibRoute
from lab_validation.parsers.common.exceptions import UnrecognizedLinesError


def test_parse_show_ip_route_acos() -> None:
    text = textwrap.dedent(
        """\
    Codes: V - VIP, VF - VIP Flagged, N - IP NAT
           NR - IP NAT Range List, F - Floating IP, SN - Static NAT
           N64 - NAT64, LW - LW4o6, NM - NAT Map

    V      10.0.0.1/32
    VF     10.0.0.2/32
    N      10.0.0.3/32
    F      10.0.0.4/32
    """
    )
    routes = parse_show_ip_route_acos(text)
    assert routes == [
        A10MainRibRoute(
            network="10.0.0.1/32",
            next_hop_int=None,
            next_hop_ip=None,
            protocol="V",
            admin=0,
            metric=0,
        ),
        A10MainRibRoute(
            network="10.0.0.2/32",
            next_hop_int=None,
            next_hop_ip=None,
            protocol="VF",
            admin=0,
            metric=0,
        ),
        A10MainRibRoute(
            network="10.0.0.3/32",
            next_hop_int=None,
            next_hop_ip=None,
            protocol="N",
            admin=0,
            metric=0,
        ),
        A10MainRibRoute(
            network="10.0.0.4/32",
            next_hop_int=None,
            next_hop_ip=None,
            protocol="F",
            admin=0,
            metric=0,
        ),
    ]


def test_parse_show_ip_route_acos_unrecognized_line() -> None:
    """Test that parser catches unrecognized lines rather than stop early and silently."""
    text = textwrap.dedent(
        """\
    Codes: V - VIP, VF - VIP Flagged, N - IP NAT
           NR - IP NAT Range List, F - Floating IP, SN - Static NAT
           N64 - NAT64, LW - LW4o6, NM - NAT Map

    V      10.0.0.1/32
    X      10.0.0.2/32
    """
    )
    with pytest.raises(UnrecognizedLinesError):
        parse_show_ip_route_acos(text)


def test_parse_show_ip_route_all() -> None:
    text = textwrap.dedent(
        """\
    Codes: K - kernel, C - connected, S - static, R - RIP, B - BGP
           O - OSPF, IA - OSPF inter area
           N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
           E1 - OSPF external type 1, E2 - OSPF external type 2
           i - IS-IS, L1 - IS-IS level-1, L2 - IS-IS level-2, ia - IS-IS inter area
           * - candidate default

    Gateway of last resort is 10.149.0.169 to network 0.0.0.0

    S*      0.0.0.0/0 [1/0] via 10.149.0.169, ve 55, 02:07:39
    C       10.149.0.168/29 is directly connected, ve 55, 02:07:39
    C       192.168.255.0/30 is directly connected, ve 4094, 02:54:55
    """
    )
    routes = parse_show_ip_route_all(text)
    assert routes == [
        A10MainRibRoute(
            network="0.0.0.0/0",
            next_hop_int="VirtualEthernet55",
            next_hop_ip="10.149.0.169",
            protocol="S",
            admin=1,
            metric=0,
        ),
        A10MainRibRoute(
            network="10.149.0.168/29",
            next_hop_int="VirtualEthernet55",
            next_hop_ip=None,
            protocol="C",
            admin=0,
            metric=0,
        ),
        A10MainRibRoute(
            network="192.168.255.0/30",
            next_hop_int="VirtualEthernet4094",
            next_hop_ip=None,
            protocol="C",
            admin=0,
            metric=0,
        ),
    ]


def test_parse_show_ip_route_all_unrecognized_line() -> None:
    """Test that parser catches unrecognized lines rather than stop early and silently."""
    text = textwrap.dedent(
        """\
    Codes: K - kernel, C - connected, S - static, R - RIP, B - BGP
           O - OSPF, IA - OSPF inter area
           N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
           E1 - OSPF external type 1, E2 - OSPF external type 2
           i - IS-IS, L1 - IS-IS level-1, L2 - IS-IS level-2, ia - IS-IS inter area
           * - candidate default

    Gateway of last resort is 10.149.0.169 to network 0.0.0.0

    S*      0.0.0.0/0 [1/0] via 10.149.0.169, ve 55, 02:07:39
    X       10.149.0.168/29 is directly connected, ve 55, 02:07:39
    """
    )
    with pytest.raises(UnrecognizedLinesError):
        parse_show_ip_route_all(text)
