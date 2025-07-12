"""
Tests of the common IOS model for show ip route, using IOS show data.
"""
from typing import List, Sequence

import pytest
from pyparsing import OneOrMore

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.iosxr.commands.route import (
    _parse_routes_in_vrf,
    parse_show_route,
    parse_show_route_vrf_all,
)
from lab_validation.parsers.iosxr.grammar.route import single_route
from lab_validation.parsers.iosxr.models.routes import IosXrRoute


def _parse_route_table_only(text: str, vrf: str = "default") -> List[IosXrRoute]:
    """Local utility function to just parse the routes section of a vrf's route table."""
    return _parse_routes_in_vrf(
        OneOrMore(single_route()).parseString(text, parseAll=True), vrf
    )


def test_parse_route() -> None:
    """Test parsing a route with a single next hop."""
    records: Sequence[IosXrRoute] = _parse_route_table_only(
        """B        10.10.20.0/24 [20/0] via 10.10.10.1, 04:02:46"""
    )
    assert records == [
        IosXrRoute(
            network="10.10.20.0/24",
            protocol="bgp",
            next_hop_ip="10.10.10.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        )
    ]


def test_parse_empty() -> None:
    """Test parsing main RIB with no routes (in and out of vrf)."""
    records: Sequence[IosXrRoute] = parse_show_route("""% No matching routes found""")
    assert records == []

    records: Sequence[IosXrRoute] = parse_show_route_vrf_all(
        """VRF: VRFG

        % No matching routes found"""
    )
    assert records == []


def test_parse_route_default_admin_dist() -> None:
    """Test parsing a route with unspecified admin distance."""
    records: Sequence[IosXrRoute] = _parse_route_table_only(
        """S    192.0.2.1/32 is directly connected, 00:08:45, Null0
C        192.168.61.2/32 is directly connected, Loopback0"""
    )
    assert records == [
        IosXrRoute(
            network="192.0.2.1/32",
            protocol="static",
            next_hop_ip=None,
            next_hop_int="Null0",
            next_hop_vrf=None,
            # default admin distance is 1 for static routes
            admin=1,
            metric=0,
        ),
        IosXrRoute(
            network="192.168.61.2/32",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="Loopback0",
            next_hop_vrf=None,
            admin=0,
            metric=0,
        ),
    ]


def test_parse_multiple_routes() -> None:
    """Test parsing show-route output with multiple records."""
    records: Sequence[IosXrRoute] = _parse_route_table_only(
        """C        192.168.61.2/32 is directly connected, Loopback0
B        192.168.61.3/32 [20/0] via 10.10.10.1, 04:00:47"""
    )
    assert records == [
        IosXrRoute(
            network="192.168.61.2/32",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="Loopback0",
            next_hop_vrf=None,
            admin=0,
            metric=0,
        ),
        IosXrRoute(
            network="192.168.61.3/32",
            protocol="bgp",
            next_hop_ip="10.10.10.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        ),
    ]


def test_parse_connected_route() -> None:
    """Test parsing a connected route."""
    input_text = """C        10.10.10.0/24 is directly connected, GigabitEthernet1/0"""
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="10.10.10.0/24",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet1/0",
            next_hop_vrf=None,
            admin=0,
            metric=0,
        )
    ]


def test_parse_local_route() -> None:
    """Test parsing a local route."""
    input_text = """L        10.10.10.2/32 is directly connected, GigabitEthernet1/0"""
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="10.10.10.2/32",
            protocol="local",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet1/0",
            next_hop_vrf=None,
            admin=0,
            metric=0,
        )
    ]


def test_parse_null_route() -> None:
    """Test parsing a null route."""
    input_text = """B 10.100.0.0/16 [200/0], 7w0d, Null0
S 10.100.128.0/24 is directly connected, Null0
"""
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="10.100.0.0/16",
            protocol="bgp",
            next_hop_ip=None,
            next_hop_int="Null0",
            next_hop_vrf=None,
            admin=200,
            metric=0,
        ),
        IosXrRoute(
            network="10.100.128.0/24",
            protocol="static",
            next_hop_ip=None,
            next_hop_int="Null0",
            next_hop_vrf=None,
            admin=1,
            metric=0,
        ),
    ]


def test_parse_static_route() -> None:
    """Test parsing a static route."""
    input_text = "S*    0.0.0.0/0 [1/0] via 37.2.2.1"
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="0.0.0.0/0",
            protocol="static",
            next_hop_ip="37.2.2.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=1,
            metric=0,
        )
    ]


def test_parse_backup_route() -> None:
    """Test parsing a backup route."""
    input_text = "B    0.0.0.0/0 [1/0] via 37.2.2.1 (!)"
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="0.0.0.0/0",
            protocol="bgp",
            next_hop_ip="37.2.2.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=1,
            metric=0,
            backup=True,
        )
    ]


def test_exception_on_unrecognized() -> None:
    """Test parsing raise exception on unrecognized lines"""
    with pytest.raises(UnrecognizedLinesError) as _:
        parse_show_route(
            """Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, (!) - FRR Backup path

Gateway of last resort is not set

L        10.10.10.2/32 is directly connected, GigabitEthernet1/0
T        192.168.61.2 is directly connected, Loopback0
C        10.10.10.0/24 is directly connected, GigabitEthernet1/07"""
        )  # T is not a recognized protocol


def test_parse_ospf_routes() -> None:
    """Test that we can parse OSPF routes"""
    input_text = """
    O*IA  0.0.0.0/0 [110/11] via 14.2.0.1, 00:31:32, Ethernet2/0
    O IA     1.1.1.1/32 [110/11] via 16.2.7.1, 00:31:33, Ethernet2/7
    O E2     2.2.2.2/31 [110/20] via 13.1.0.2, 00:09:52, Ethernet1/0
    O        10.4.0.0/16 is a summary, 01:05:17, Null0
    """

    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="0.0.0.0/0",
            protocol="ospfIA",
            next_hop_ip="14.2.0.1",
            next_hop_int="Ethernet2/0",
            next_hop_vrf=None,
            admin=110,
            metric=11,
        ),
        IosXrRoute(
            network="1.1.1.1/32",
            protocol="ospfIA",
            next_hop_ip="16.2.7.1",
            next_hop_int="Ethernet2/7",
            next_hop_vrf=None,
            admin=110,
            metric=11,
        ),
        IosXrRoute(
            network="2.2.2.2/31",
            protocol="ospfE2",
            next_hop_ip="13.1.0.2",
            next_hop_int="Ethernet1/0",
            next_hop_vrf=None,
            admin=110,
            metric=20,
        ),
        IosXrRoute(
            network="10.4.0.0/16",
            protocol="ospfIS",
            next_hop_ip=None,
            next_hop_int="Null0",
            next_hop_vrf=None,
            admin=0,
            metric=0,
        ),
    ]


def test_with_vrf() -> None:
    """Test parsing a file with a vrf declaration"""
    input_text = """VRF: cust10
Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, (!) - FRR Backup path

Gateway of last resort is not set

C        1.1.2.10/32 is directly connected, Loopback10"""
    records: Sequence[IosXrRoute] = parse_show_route_vrf_all(input_text)
    assert records == [
        IosXrRoute(
            network="1.1.2.10/32",
            protocol="connected",
            next_hop_ip=None,
            next_hop_int="Loopback10",
            next_hop_vrf=None,
            admin=0,
            metric=0,
            vrf="cust10",
        )
    ]


def test_parse_vrf_leak() -> None:
    """Test VRF leaked route parsing."""
    input_text = """Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, (!) - FRR Backup path

Gateway of last resort is not set

B    10.10.45.180/30 is directly connected, 00:11:58, GigabitEthernet0/0/0/5 (nexthop in vrf VRF1)
B    10.11.0.0/16 [20/0] via 10.10.45.181 (nexthop in vrf VRF2), 00:11:58
    """
    records: Sequence[IosXrRoute] = parse_show_route(input_text)
    assert records == [
        IosXrRoute(
            network="10.10.45.180/30",
            protocol="bgp",
            next_hop_ip=None,
            next_hop_int="GigabitEthernet0/0/0/5",
            next_hop_vrf="VRF1",
            admin=0,
            metric=0,
        ),
        IosXrRoute(
            network="10.11.0.0/16",
            protocol="bgp",
            next_hop_ip="10.10.45.181",
            next_hop_int=None,
            next_hop_vrf="VRF2",
            admin=20,
            metric=0,
        ),
    ]


def test_parse_ecmp() -> None:
    """Test parsing ECMP routes"""
    input_text = """Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, (!) - FRR Backup path

Gateway of last resort is not set

    B        1.1.1.3/32 [20/0] via 10.10.101.1, 00:40:12
                        [20/0] via 10.10.100.1, 00:40:12
                        [20/0] via 10.10.99.1, 00:40:12
                        [20/0] via 10.10.98.1, 00:40:12
    """
    records: Sequence[IosXrRoute] = parse_show_route(input_text)
    assert records == [
        IosXrRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.101.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        ),
        IosXrRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.100.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        ),
        IosXrRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.99.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        ),
        IosXrRoute(
            network="1.1.1.3/32",
            protocol="bgp",
            next_hop_ip="10.10.98.1",
            next_hop_int=None,
            next_hop_vrf=None,
            admin=20,
            metric=0,
        ),
    ]

    input_text = """
    O E2  10.10.10.10/32 [110/20] via 1.0.2.1, 00:13:26, GigabitEthernet0/0
                         [110/20] via 1.0.1.1, 00:13:21, GigabitEthernet1/0
    """
    records: Sequence[IosXrRoute] = _parse_route_table_only(input_text)
    assert records == [
        IosXrRoute(
            network="10.10.10.10/32",
            protocol="ospfE2",
            next_hop_ip="1.0.2.1",
            next_hop_int="GigabitEthernet0/0",
            next_hop_vrf=None,
            admin=110,
            metric=20,
        ),
        IosXrRoute(
            network="10.10.10.10/32",
            protocol="ospfE2",
            next_hop_ip="1.0.1.1",
            next_hop_int="GigabitEthernet1/0",
            next_hop_vrf=None,
            admin=110,
            metric=20,
        ),
    ]


def test_parse_preable_no_gateway() -> None:
    """Test parsing of preamble without the Gateway line"""
    input_text = """
Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, t - Traffic Engineering, (!) - FRR Backup path

B    10.54.99.245/32 [200/0] via 10.169.0.21 (nexthop in vrf default), 2d13h

    """
    records: Sequence[IosXrRoute] = parse_show_route(input_text)
    assert records == [
        IosXrRoute(
            network="10.54.99.245/32",
            protocol="bgp",
            next_hop_ip="10.169.0.21",
            next_hop_int=None,
            next_hop_vrf="default",
            admin=200,
            metric=0,
        )
    ]


def test_bad_preamble() -> None:
    """Test parsing of preamble without the Gateway line"""
    input_text = """
Codes: C - connected, S - static, R - RIP, B - BGP, (>) - Diversion path
       D - EIGRP, EX - EIGRP external, O - OSPF, IA - OSPF inter area
       N1 - OSPF NSSA external type 1, N2 - OSPF NSSA external type 2
       E1 - OSPF external type 1, E2 - OSPF external type 2, E - EGP
       i - ISIS, L1 - IS-IS level-1, L2 - IS-IS level-2
       ia - IS-IS inter area, su - IS-IS summary null, * - candidate default
       U - per-user static route, o - ODR, L - local, G  - DAGR, l - LISP
       A - access/subscriber, a - Application route
       M - mobile route, r - RPL, t - Traffic Engineering, (!) - FRR Backup path

10.54.99.245/32

B    10.54.99.245/32 [200/0] via 10.169.0.21 (nexthop in vrf default), 2d13h

    """
    with pytest.raises(UnrecognizedLinesError) as _:
        parse_show_route(input_text)
