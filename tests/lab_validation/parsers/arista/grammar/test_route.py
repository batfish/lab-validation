from lab_validation.parsers.arista.grammar.route import (
    _directly_connected_line,
    _ip_v4_route_line,
    _prefix_via_nhip_line,
    _routes_block_within_subnet,
    show_ip_route_vrf_all,
)


def test_show_ip_route_vrf_all() -> None:
    parsed_data = show_ip_route_vrf_all().parseString(
        """
    VRF: default
Codes: C - connected, S - static, K - kernel,
       O - OSPF, IA - OSPF inter area, E1 - OSPF external type 1,
       E2 - OSPF external type 2, N1 - OSPF NSSA external type 1,
       N2 - OSPF NSSA external type2, B I - iBGP, B E - eBGP,
       R - RIP, I L1 - IS-IS level 1, I L2 - IS-IS level 2,
       O3 - OSPFv3, A B - BGP Aggregate, A O - OSPF Summary,
       NG - Nexthop Group Static Route, V - VXLAN Control Service,
       DH - DHCP client installed default route, M - Martian,
       DP - Dynamic Policy Route

Gateway of last resort is not set

         C      10.10.30.0/24 is directly connected, Ethernet1
        B E    10.10.10.0/24 [200/0] via 10.10.30.1, Ethernet1


VRF: cust10
Codes: C - connected, S - static, K - kernel,
       O - OSPF, IA - OSPF inter area, E1 - OSPF external type 1,
       E2 - OSPF external type 2, N1 - OSPF NSSA external type 1,
       N2 - OSPF NSSA external type2, B I - iBGP, B E - eBGP,
       R - RIP, I L1 - IS-IS level 1, I L2 - IS-IS level 2,
       O3 - OSPFv3, A B - BGP Aggregate, A O - OSPF Summary,
       NG - Nexthop Group Static Route, V - VXLAN Control Service,
       DH - DHCP client installed default route, M - Martian,
       DP - Dynamic Policy Route

Gateway of last resort is not set

 C      1.1.4.10/32 is directly connected, Loopback10
    """
    )
    assert len(parsed_data) == 2

    vrf_table = parsed_data[0]
    assert vrf_table.vrf == "default"
    assert len(vrf_table.v4_routes) == 2
    route = vrf_table.v4_routes[0]
    assert route.protocol == "C"
    assert route.network == "10.10.30.0/24"
    assert route.nh_iface == "Ethernet1"
    route = vrf_table.v4_routes[1]
    assert route.protocol == "B E"
    assert route.network == "10.10.10.0/24"
    assert route.admin == 200
    assert route.metric == 0
    assert route.nh_ip == "10.10.30.1"
    assert route.nh_iface == "Ethernet1"

    vrf_table = parsed_data[1]
    assert vrf_table.vrf == "cust10"
    assert len(vrf_table.v4_routes) == 1
    route = vrf_table.v4_routes[0]
    assert route.protocol == "C"
    assert route.network == "1.1.4.10/32"
    assert route.nh_iface == "Loopback10"


def test_routes_block_within_subnet() -> None:
    parsed_data = _routes_block_within_subnet().parseString(
        """
        C      10.10.30.0/24 is directly connected, Ethernet1
        B E    10.10.10.0/24 [200/0] via 10.10.30.1, Ethernet1
        """
    )
    assert len(parsed_data.v4_routes) == 2
    route = parsed_data.v4_routes[0]
    assert route.protocol == "C"
    assert route.network == "10.10.30.0/24"
    assert route.nh_iface == "Ethernet1"

    route = parsed_data.v4_routes[1]
    assert route.protocol == "B E"
    assert route.network == "10.10.10.0/24"
    assert route.admin == 200
    assert route.metric == 0
    assert route.nh_ip == "10.10.30.1"
    assert route.nh_iface == "Ethernet1"


def test_ip_v4_route_line_direct() -> None:
    parsed_data = _ip_v4_route_line().parseString(
        "C      10.10.30.0/24 is directly connected, Ethernet1"
    )
    assert parsed_data.protocol == "C"
    assert parsed_data.network == "10.10.30.0/24"
    assert parsed_data.nh_iface == "Ethernet1"


def test_ip_v4_route_line_not_direct() -> None:
    parsed_data = _ip_v4_route_line().parseString(
        "B E    10.10.10.0/24 [200/0] via 10.10.30.1, Ethernet1"
    )
    assert parsed_data.protocol == "B E"
    assert parsed_data.network == "10.10.10.0/24"
    assert parsed_data.admin == 200
    assert parsed_data.metric == 0
    assert parsed_data.nh_ip == "10.10.30.1"
    assert parsed_data.nh_iface == "Ethernet1"


def test_directly_connected_line() -> None:
    parsed_data = _directly_connected_line().parseString(
        "is directly connected, Ethernet1"
    )
    assert parsed_data.nh_iface == "Ethernet1"


def test_prefix_via_nhip_line() -> None:
    parsed_data = _prefix_via_nhip_line().parseString(
        "[20/21] via 10.10.10.1, Ethernet1"
    )
    assert parsed_data.admin == 20
    assert parsed_data.metric == 21
    assert parsed_data.nh_ip == "10.10.10.1"
    assert parsed_data.nh_iface == "Ethernet1"
