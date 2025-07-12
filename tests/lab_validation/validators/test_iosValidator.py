import math

from pybatfish.datamodel import NextHopDiscard, NextHopIp

from lab_validation.parsers.ios.models.bgp import IosBgpRoute
from lab_validation.parsers.ios.models.routes import IosIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.IosValidator import IosValidator


def test_bgp_equal() -> None:
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopIp(ip="2.2.2.2"),
        next_hop_ip="2.2.2.2",
        next_hop_int="dynamic",
        protocol="IBGP",
        as_path="1 2",
        metric=5,
        local_preference=100,
        communities=["1", "2", "3"],
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    ios = IosBgpRoute(
        network="1.2.3.4/20",
        next_hop_ip="2.2.2.2",
        best_path=True,
        metric=5,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
    )
    assert IosValidator._diff_bgp_routes_cost(("default", ios), bf) == 0


def test_bgp_equal_local_routes() -> None:
    bf = BgpRibRoute(
        weight=32768,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopDiscard(),
        next_hop_ip=None,
        next_hop_int="null_interface",
        protocol="IBGP",
        as_path="",
        metric=0,
        local_preference=100,
        communities=(),
        origin_protocol="connected",
        origin_type="incomplete",
        tag=None,
    )
    ios = IosBgpRoute(
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
    )
    assert IosValidator._diff_bgp_routes_cost(("default", ios), bf) == 0


def test_bgp_not_equal() -> None:
    """Test when the routes don't match."""
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopIp(ip="2.2.2.2"),
        next_hop_ip="2.2.2.2",
        next_hop_int="dynamic",
        protocol="IBGP",
        as_path="1 2",
        metric=5,
        local_preference=100,
        communities=["1", "2", "3"],
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    ios = IosBgpRoute(
        network="1.2.3.4/20",
        next_hop_ip="2.2.2.2",
        best_path=True,
        metric=6,
        local_preference=101,
        weight=1,
        as_path=(1, 2, 3),
        origin_type="i",
    )
    # Accumulates a difference cost of 4 (AS path, local pref, origin type, metric, weight)
    assert IosValidator._diff_bgp_routes_cost(("default", ios), bf) == 5


def test_origin_types() -> None:
    assert IosValidator._bgp_origin_type_compatible("igp", "i")
    assert not IosValidator._bgp_origin_type_compatible("igp", "e")
    assert not IosValidator._bgp_origin_type_compatible("igp", "?")
    assert IosValidator._bgp_origin_type_compatible("egp", "e")
    assert not IosValidator._bgp_origin_type_compatible("egp", "i")
    assert not IosValidator._bgp_origin_type_compatible("egp", "?")
    assert IosValidator._bgp_origin_type_compatible("incomplete", "?")
    assert not IosValidator._bgp_origin_type_compatible("incomplete", "e")
    assert not IosValidator._bgp_origin_type_compatible("incomplete", "i")


def test_interface_props_equal() -> None:
    bf = InterfaceProperties(
        name="GigabitEthernet0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e9),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000000000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    ios = {
        "arp_timeout": "04:00:00",
        "arp_type": "arpa",
        "auto_negotiate": True,
        "bandwidth": 1000000,
        "delay": 10,
        "duplex_mode": "full",
        "enabled": True,
        "encapsulations": {"encapsulation": "arpa"},
        "flow_control": {"receive": False, "send": False},
        "ipv4": {"1.2.3.4/24": {"ip": "1.2.3.4", "prefix_length": "24"}},
        "keepalive": 10,
        "last_input": "00:00:00",
        "last_output": "00:00:18",
        "line_protocol": "up",
        "link_type": "auto",
        "mac_address": "0cef.e6a2.dd00",
        "media_type": "RJ45",
        "mtu": 1500,
        "oper_status": "up",
        "output_hang": "never",
        "phys_address": "0cef.e6a2.dd00",
        "port_channel": {"port_channel_member": False},
        "port_speed": 1e9,
        "reliability": "255/255",
        "rxload": "1/255",
        "txload": "1/255",
        "type": "CSR vNIC",
    }
    assert IosValidator._compare_interfaces(ios, bf) == {}


def test_interface_props_not_equal() -> None:
    bf = InterfaceProperties(
        name="GigabitEthernet0",
        access_vlan=None,
        active=False,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=int(1e8),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    ios = {
        "arp_timeout": "04:00:00",
        "arp_type": "arpa",
        "auto_negotiate": True,
        "bandwidth": 1000000,
        "delay": 10,
        "duplex_mode": "full",
        "enabled": True,
        "encapsulations": {"encapsulation": "arpa"},
        "flow_control": {"receive": False, "send": False},
        "ipv4": {"1.2.3.4/24": {"ip": "1.2.3.4", "prefix_length": "24"}},
        "keepalive": 10,
        "last_input": "00:00:00",
        "last_output": "00:00:18",
        "line_protocol": "up",
        "link_type": "auto",
        "mac_address": "0cef.e6a2.dd00",
        "media_type": "RJ45",
        "mtu": 1500,
        "oper_status": "up",
        "output_hang": "never",
        "phys_address": "0cef.e6a2.dd00",
        "port_channel": {"port_channel_member": False},
        "port_speed": 1e9,
        "reliability": "255/255",
        "rxload": "1/255",
        "txload": "1/255",
        "type": "CSR vNIC",
    }
    assert IosValidator._compare_interfaces(ios, bf) == {
        "active": "Batfish: False, IOS: True",
        "bandwidth": "Batfish: 100000000, IOS: 1000000000",
        "ipv4 address": "Batfish: ['1.2.3.4/25'], IOS: ['1.2.3.4/24']",
        "speed": "Batfish: 1000, IOS: 1000000000.0",
    }


def test_diff_routes_cost_nhint_dynamic() -> None:
    expected_route = IosIpRoute(
        network="2.2.2.0/24",
        protocol="connected",
        next_hop_ip="3.4.5.6",
        next_hop_int=None,
        admin=1,
        metric=0,
        vrf="vrf",
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="connected",
        tag=None,
        metric=0,
        admin=1,
    )
    assert (
        IosValidator._diff_routes_cost(expected_route, batfish_route) == 1
    )  # next hop IP


def test_compat_routes_null() -> None:
    expected_route = IosIpRoute(
        network="2.2.2.0/24",
        protocol="static",
        next_hop_ip=None,
        next_hop_int="Null0",
        admin=0,
        metric=0,
        vrf="vrf",
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="2.2.2.0/24",
        next_hop=NextHopDiscard(),
        protocol="static",
        tag=None,
        metric=0,
        admin=0,
    )
    assert IosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_diff_routes_cost_null() -> None:
    expected_route = IosIpRoute(
        network="2.2.2.0/24",
        protocol="static",
        next_hop_ip=None,
        next_hop_int="Ethernet1",
        admin=0,
        metric=0,
        vrf="vrf",
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="2.2.2.0/24",
        next_hop=NextHopDiscard(),
        protocol="static",
        tag=None,
        metric=0,
        admin=0,
    )
    assert (
        IosValidator._diff_routes_cost(expected_route, batfish_route) == 10.0
    )  # only one side null


def test_diff_routes_cost_nhint_ignore() -> None:
    expected_route = IosIpRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int="iface1",  # will be ignored
        admin=1,
        metric=0,
        vrf="vrf",
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="bgp",
        tag=None,
        metric=0,
        admin=1,
    )
    assert IosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_diff_routes_cost_skip_ibgp_comparision() -> None:
    """
    Test skipping when real_data protocol is `bgp` & batfish protocol is `ibgp`
    """
    expected_route = IosIpRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int=None,
        admin=200,
        metric=0,
        vrf="default",
    )
    batfish_route = MainRibRoute(
        vrf="default",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="ibgp",
        tag=None,
        metric=0,
        admin=200,
    )
    assert IosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_diff_routes_cost_route_in_multiple_vrf() -> None:
    """
    Test that route in different vrf return math.inf
    """
    expected_route = IosIpRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="10.34.31.2",
        next_hop_int=None,
        admin=20,
        metric=0,
        vrf="d2_ce",
    )
    batfish_route = MainRibRoute(
        vrf="d4_shared",
        network="192.168.122.0/24",
        next_hop=NextHopIp(ip="10.34.31.2"),
        protocol="bgp",
        tag=None,
        metric=0,
        admin=20,
    )
    assert IosValidator._diff_routes_cost(expected_route, batfish_route) == math.inf


def test_ospf_summary_ignores_ad_and_metric() -> None:
    expected_route = IosIpRoute(
        network="192.168.122.0/24",
        protocol="ospfIS",
        next_hop_ip=None,
        next_hop_int="Null0",
        admin=0,
        metric=0,
        vrf="d2_ce",
    )
    batfish_route = MainRibRoute(
        vrf="d2_ce",
        network="192.168.122.0/24",
        next_hop=NextHopDiscard(),
        protocol="ospfIS",
        tag=None,
        metric=7,
        admin=20,
    )
    # Ignore different admin, metric
    assert IosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_compute_protocol_cost() -> None:
    result = IosValidator.compute_protocol_cost("bgp", "ibgp")
    assert result == 0.0

    result = IosValidator.compute_protocol_cost("ospf", "ospfE1")
    assert result == 1.0

    result = IosValidator.compute_protocol_cost("eigrp", "eigrpEX")
    assert result == 1.0

    result = IosValidator.compute_protocol_cost("bgp", "ospf")
    assert result == math.inf
