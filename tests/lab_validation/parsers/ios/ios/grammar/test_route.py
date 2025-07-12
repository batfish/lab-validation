from lab_validation.parsers.ios.grammar.route import (
    _directly_connected_line,
    _prefix_is_subnetted_line,
    _prefix_via_nhip_line,
    _routes_block_within_subnet,
    _v4_route,
)


def test_directly_connected_line() -> None:
    """Test if we can parse the directly connected portion of a route line"""
    input_text = "is directly connected, GigabitEthernet1/0"
    parsed_data = _directly_connected_line().parseString(input_text)
    assert parsed_data.nh_iface == "GigabitEthernet1/0"

    """Test directly connected routes in vrf leaking"""
    input_text = "is directly connected, 00:38:55, GigabitEthernet1"
    parsed_data = _directly_connected_line().parseString(input_text)
    assert parsed_data.nh_iface == "GigabitEthernet1"


def test_prefix_via_nhip_line() -> None:
    """Test if we can parse the admin/metric and next hop portion of a route line"""
    parsed_data = _prefix_via_nhip_line().parseString(
        "[20/21] via 10.10.10.1, 00:02:50"
    )
    assert parsed_data.admin == 20
    assert parsed_data.metric == 21
    assert parsed_data.nh_ip == "10.10.10.1"


def test_prefix_subnetted_line() -> None:
    """Test that we can parse subnetted/variably subnetted line"""
    parsed_data = _prefix_is_subnetted_line().parseString(
        "15.0.0.0/24 is subnetted, 1 subnets", parseAll=True
    )
    assert parsed_data.subnet_prefix == "15.0.0.0/24"

    parsed_data = _prefix_is_subnetted_line().parseString(
        "192.168.61.0/24 is variably subnetted, 7 subnets, 2 masks", parseAll=True
    )
    assert parsed_data.subnet_prefix == "192.168.61.0/24"


def test_v4_route_line() -> None:
    """Test single route without subnet block"""
    parsed_data = _v4_route().parseString(
        "B     192.168.122.0/24 [20/0] via 10.12.11.1, 00:03:11", parseAll=True
    )
    assert parsed_data.protocol == "B"
    assert parsed_data.network == "192.168.122.0/24"
    assert parsed_data.admin == 20
    assert parsed_data.metric == 0
    assert parsed_data.nh_ip == "10.12.11.1"


def test_candidate_v4_route() -> None:
    """Test that we can parse a candidate default route line"""
    parsed_data = _v4_route().parseString(
        "O*IA  0.0.0.0/0 [110/11] via 14.2.0.1, 00:31:32, Ethernet2/0", parseAll=True
    )
    assert parsed_data.protocol == "O"
    assert parsed_data.ospf_extensions == "IA"
    assert parsed_data.network == "0.0.0.0/0"
    assert parsed_data.admin == 110
    assert parsed_data.metric == 11
    assert parsed_data.nh_ip == "14.2.0.1"
    assert parsed_data.nh_iface == "Ethernet2/0"


def test_v4_route_ospf_summary() -> None:
    """Test that we can parse an OSPF summary route"""
    parsed_data = _v4_route().parseString(
        "O        10.4.0.0/16 is a summary, 01:05:17, Null0", parseAll=True
    )
    assert parsed_data.protocol == "O"
    assert parsed_data.network == "10.4.0.0/16"
    assert parsed_data.summary
    assert parsed_data.nh_iface == "Null0"


def test_v4_route_normal() -> None:
    """Test that we can parse a normal IP v4 route (which is not candidate default)"""
    parsed_data = _v4_route().parseString(
        "C        192.168.61.0/24 is directly connected, Loopback61", parseAll=True
    )
    route = parsed_data
    assert route.protocol == "C"
    assert route.network == "192.168.61.0/24"
    assert route.nh_iface == "Loopback61"

    parsed_data = _v4_route().parseString(
        "O IA     192.168.61.1/32 [110/11] via 14.2.0.1, 00:31:32, Ethernet2/0",
        parseAll=True,
    )
    route = parsed_data
    assert route.protocol == "O"
    assert route.ospf_extensions == "IA"
    assert route.network == "192.168.61.1/32"
    assert route.admin == 110
    assert route.metric == 11
    assert route.nh_ip == "14.2.0.1"
    assert route.nh_iface == "Ethernet2/0"

    # test eigrp line
    parsed_data = _v4_route().parseString(
        "D        172.16.1.2 [90/130816] via 10.12.11.2, 03:12:43, GigabitEthernet1",
        parseAll=True,
    )
    route = parsed_data
    assert route.protocol == "D"
    assert route.eigrp_extensions == ""
    assert route.network == "172.16.1.2"
    assert route.admin == 90
    assert route.metric == 130816
    assert route.nh_ip == "10.12.11.2"
    assert route.nh_iface == "GigabitEthernet1"

    # test eigrp external line
    parsed_data = _v4_route().parseString(
        "D EX       172.16.1.2 [90/130816] via 10.12.11.2, 03:12:43, GigabitEthernet1",
        parseAll=True,
    )
    route = parsed_data
    assert route.protocol == "D"
    assert route.eigrp_extensions == "EX"
    assert route.network == "172.16.1.2"
    assert route.admin == 90
    assert route.metric == 130816
    assert route.nh_ip == "10.12.11.2"
    assert route.nh_iface == "GigabitEthernet1"


def test_routes_block_within_subnet() -> None:
    """Test that we can parse routes under a subnetted block"""
    parsed_data = _routes_block_within_subnet().parseString(
        """192.168.61.0/24 is variably subnetted, 8 subnets, 2 masks
O IA     192.168.61.3/32 [110/12] via 12.0.0.1, 00:29:31, GigabitEthernet0/0
D EX     192.168.61.4/32 [90/13] via 12.0.0.2, 00:29:31, GigabitEthernet0/1"""
    )

    assert parsed_data.subnet_prefix == "192.168.61.0/24"

    parsed_route = parsed_data.v4_routes_block[0]
    assert parsed_route.protocol == "O"
    assert parsed_route.ospf_extensions == "IA"
    assert parsed_route.admin == 110
    assert parsed_route.metric == 12
    assert parsed_route.network == "192.168.61.3/32"
    assert parsed_route.nh_ip == "12.0.0.1"
    assert parsed_route.nh_iface == "GigabitEthernet0/0"

    parsed_route = parsed_data.v4_routes_block[1]
    assert parsed_route.protocol == "D"
    assert parsed_route.eigrp_extensions == "EX"
    assert parsed_route.admin == 90
    assert parsed_route.metric == 13
    assert parsed_route.network == "192.168.61.4/32"
    assert parsed_route.nh_ip == "12.0.0.2"
    assert parsed_route.nh_iface == "GigabitEthernet0/1"
