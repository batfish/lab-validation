"""
Tests of the common IOS model for show ip route, using IOS show data.
"""
from typing import List, Sequence

import pytest
from pyparsing import OneOrMore

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.ios.commands.route import (
    _parse_routes_in_vrf,
    parse_show_ip_route,
)
from lab_validation.parsers.ios.grammar.route import single_route
from lab_validation.parsers.ios.models.routes import IosIpRoute


def _parse_route_table_only(text: str, vrf: str = "default") -> List[IosIpRoute]:
    """Local utility function to just parse the routes section of a vrf's route table."""
    return _parse_routes_in_vrf(
        OneOrMore(single_route()).parseString(text, parseAll=True), vrf
    )


def test_parse_route() -> None:
    """Test parsing a route with a single next hop."""
    records: Sequence[IosIpRoute] = _parse_route_table_only(
        """10.0.0.0/24 is subnetted, 1 subnets
B        10.10.20.0/24 [20/0] via 10.10.10.1, 04:02:46"""
    )
    assert records == [
        IosIpRoute(
            network="10.10.20.0/24",
            protocol="bgp",
            next_hop_ip="10.10.10.1",
            next_hop_int=None,
            admin=20,
            metric=0,
        )
    ]


def test_parse_multiple_routes() -> None:
    """Test parsing show-route output with multiple records."""
    records: Sequence[IosIpRoute] = _parse_route_table_only(
        """192.168.61.0/24 is subnetted, 1 subnets
C        192.168.61.2 is directly connected, Loopback0
B        192.168.61.3 [20/0] via 10.10.10.1, 04:00:47"""
    )
    assert records == [
        IosIpRoute(
            network="192.168.61.0/24",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="Loopback0",
            admin=0,
            metric=0,
        ),
        IosIpRoute(
            network="192.168.61.0/24",
            protocol="bgp",
            next_hop_ip="10.10.10.1",
            next_hop_int=None,
            admin=20,
            metric=0,
        ),
    ]


def test_parse_connected_route() -> None:
    """Test parsing a connected route."""
    input_text = """10.10.10.0/24 is subnetted, 1 subnets
C        10.10.10.0/24 is directly connected, GigabitEthernet1/0"""
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="10.10.10.0/24",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet1/0",
            admin=0,
            metric=0,
        )
    ]


def test_parse_local_route() -> None:
    """Test parsing a local route."""
    input_text = """10.10.10.0/24 is subnetted, 1 subnets
    L        10.10.10.2/32 is directly connected, GigabitEthernet1/0"""
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="10.10.10.2/32",
            protocol="local",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet1/0",
            admin=0,
            metric=0,
        )
    ]


def test_parse_null_route() -> None:
    """Test parsing a null route."""
    input_text = """      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
B 10.100.0.0/16 [200/0], 7w0d, Null0
S 10.100.128.0/24 is directly connected, Null0
"""
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="10.100.0.0/16",
            protocol="bgp",
            next_hop_ip=None,
            next_hop_int="Null0",
            admin=200,
            metric=0,
        ),
        IosIpRoute(
            network="10.100.128.0/24",
            protocol="static",
            next_hop_ip=None,
            next_hop_int="Null0",
            admin=1,
            metric=0,
        ),
    ]


def test_parse_static_route() -> None:
    """Test parsing a static route."""
    input_text = "S*    0.0.0.0/0 [1/0] via 37.2.2.1"
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="0.0.0.0/0",
            protocol="static",
            next_hop_ip="37.2.2.1",
            next_hop_int=None,
            admin=1,
            metric=0,
        )
    ]


def test_exception_on_unrecognized() -> None:
    """Test parsing raise exception on unrecognized lines"""
    with pytest.raises(UnrecognizedLinesError) as _:
        parse_show_ip_route(
            """Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       + - replicated route, % - next hop override

Gateway of last resort is not set

10.10.10.0/24 is subnetted, 1 subnets
L        10.10.10.2/32 is directly connected, GigabitEthernet1/0
T        192.168.61.2 is directly connected, Loopback0
10.10.10.0/24 is subnetted, 1 subnets
C        10.10.10.0/24 is directly connected, GigabitEthernet1/07"""
        )


def test_parse_ospf_routes() -> None:
    """Test that we can parse OSPF routes, also tests whether subnet is inherited from the 'is subnetted' line"""
    input_text = """
    O*IA  0.0.0.0/0 [110/11] via 14.2.0.1, 00:31:32, Ethernet2/0
    1.1.1.0/24 is subnetted, 1 subnets
    O IA     1.1.1.1 [110/11] via 16.2.7.1, 00:31:33, Ethernet2/7
    O E2     1.1.1.1/31 [110/20] via 13.1.0.2, 00:09:52, Ethernet1/0
    O        10.4.0.0/16 is a summary, 01:05:17, Null0
    """

    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="0.0.0.0/0",
            protocol="ospfIA",
            next_hop_ip="14.2.0.1",
            next_hop_int="Ethernet2/0",
            admin=110,
            metric=11,
        ),
        IosIpRoute(
            network="1.1.1.0/24",
            protocol="ospfIA",
            next_hop_ip="16.2.7.1",
            next_hop_int="Ethernet2/7",
            admin=110,
            metric=11,
        ),
        IosIpRoute(
            network="1.1.1.1/31",
            protocol="ospfE2",
            next_hop_ip="13.1.0.2",
            next_hop_int="Ethernet1/0",
            admin=110,
            metric=20,
        ),
        IosIpRoute(
            network="10.4.0.0/16",
            protocol="ospfIS",
            next_hop_ip=None,
            next_hop_int="Null0",
            admin=0,
            metric=0,
        ),
    ]


def test__parse_routes_block_within_subnet() -> None:
    """Test that we can parse routes under a subnetted block"""
    input_text = """192.168.61.0/24 is variably subnetted, 8 subnets, 2 masks
O IA     192.168.61.3/26 [110/12] via 12.0.0.1, 00:29:31, GigabitEthernet0/0
O E1     192.168.61.4 [115/13] via 12.0.0.2, 00:29:31, Ethernet0/0"""

    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="192.168.61.3/26",
            protocol="ospfIA",
            next_hop_ip="12.0.0.1",
            next_hop_int="GigabitEthernet0/0",
            admin=110,
            metric=12,
        ),
        IosIpRoute(
            network="192.168.61.0/24",
            protocol="ospfE1",
            next_hop_ip="12.0.0.2",
            next_hop_int="Ethernet0/0",
            admin=115,
            metric=13,
        ),
    ]


def test_with_vrf() -> None:
    """Test parsing a full file with a vrf declaration"""
    input_text = """Routing Table: cust10
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       + - replicated route, % - next hop override

Gateway of last resort is not set

      1.0.0.0/32 is subnetted, 1 subnets
C        1.1.2.10 is directly connected, Loopback10"""
    records: Sequence[IosIpRoute] = parse_show_ip_route(input_text)
    assert records == [
        IosIpRoute(
            network="1.1.2.10/32",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="Loopback10",
            admin=0,
            metric=0,
            vrf="cust10",
        )
    ]


def test_route_without_subnet_block() -> None:
    """Test parsing of a route without subnet block"""
    input_text = """
Routing Table: vrf4
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR

Gateway of last resort is not set

B     192.168.122.0/24 [20/0] via 10.12.11.1 (vrf3), 00:03:11
    """
    records: Sequence[IosIpRoute] = parse_show_ip_route(input_text)
    assert records == [
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.12.11.1",
            next_hop_int=None,
            admin=20,
            metric=0,
            vrf="vrf4",
        )
    ]


def test_parse_ecmp() -> None:
    """Test parsing ECMP routes"""
    input_text = """
        1.0.0.0/32 is subnetted, 6 subnets
    B        1.1.1.3 [20/0] via 10.10.101.1, 00:40:12
                     [20/0] via 10.10.100.1, 00:40:12
    """
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.101.1",
            next_hop_int=None,
            admin=20,
            metric=0,
        ),
        IosIpRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.100.1",
            next_hop_int=None,
            admin=20,
            metric=0,
        ),
    ]

    input_text = """
O        10.188.250.32/30 [110/511] via 10.188.250.62, 1d01h, GigabitEthernet3
                          [110/511] via 10.188.250.58, 1d01h, GigabitEthernet2
    """
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="10.188.250.32/30",
            protocol="ospf",
            next_hop_ip="10.188.250.62",
            next_hop_int="GigabitEthernet3",
            admin=110,
            metric=511,
        ),
        IosIpRoute(
            network="10.188.250.32/30",
            protocol="ospf",
            next_hop_ip="10.188.250.58",
            next_hop_int="GigabitEthernet2",
            admin=110,
            metric=511,
        ),
    ]

    input_text = """
        10.10.10.0/24 is subnetted, 6 subnets
    O E2  10.10.10.0 [110/20] via 1.0.2.1, 00:13:26, GigabitEthernet0/0
                     [110/20] via 1.0.1.1, 00:13:21, GigabitEthernet1/0
    """
    records: Sequence[IosIpRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosIpRoute(
            network="10.10.10.0/24",
            protocol="ospfE2",
            next_hop_ip="1.0.2.1",
            next_hop_int="GigabitEthernet0/0",
            admin=110,
            metric=20,
        ),
        IosIpRoute(
            network="10.10.10.0/24",
            protocol="ospfE2",
            next_hop_ip="1.0.1.1",
            next_hop_int="GigabitEthernet1/0",
            admin=110,
            metric=20,
        ),
    ]


def test_route_vrf_leaking() -> None:
    """
    Test vrf leaking routes
    There will be certain properties which will be available only while using `vrf route leaking`. For examle
    - originating vrf
    - directly connected routes tagged with Routing protocol code
    - time associated with directly connected routes
    """
    input_text = """Routing Table: d1_ce
Codes: L - local, C - connected, S - static, R - RIP, M - mobile, B - BGP
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2
       i - IS-IS, su - IS-IS summary, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, * - candidate default, U - per-user static route
       o - ODR, P - periodic downloaded static route, H - NHRP, l - LISP
       a - application route
       + - replicated route, % - next hop override, p - overrides from PfR

Gateway of last resort is not set

      10.0.0.0/8 is variably subnetted, 2 subnets, 2 masks
B        10.10.10.0/24 [20/0] via 10.34.31.2 (d4_shared), 00:38:53
B        10.13.11.0/30 is directly connected, 00:38:55, GigabitEthernet1

"""
    records: Sequence[IosIpRoute] = parse_show_ip_route(input_text)
    assert records == [
        IosIpRoute(
            network="10.10.10.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            admin=20,
            metric=0,
            vrf="d1_ce",
        ),
        IosIpRoute(
            network="10.13.11.0/30",
            protocol="bgp",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet1",
            admin=0,
            metric=0,
            vrf="d1_ce",
        ),
    ]
