import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp, NextHopVrf

from lab_validation.parsers.iosxr.models.bgp import IosXrBgpRoute
from lab_validation.parsers.iosxr.models.interfaces import IosXrInterface
from lab_validation.parsers.iosxr.models.routes import IosXrRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.IosXrValidator import IosXrValidator


def test_diff_bgp_routes_cost() -> None:
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.2.0.0/20",
        next_hop=NextHopInterface(interface="Ethernet1", ip="2.2.2.2"),
        next_hop_ip="2.2.2.2",
        next_hop_int="Ethernet1",
        protocol="IBGP",
        as_path="1 2",
        metric=0,
        local_preference=100,
        communities=("1", "2", "3"),
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    xr = IosXrBgpRoute(
        network="1.2.0.0/20",
        next_hop_ip="2.2.2.2",
        best_path=True,
        metric=None,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
    )
    assert IosXrValidator._diff_bgp_routes_cost(("default", xr), bf) == []

    xr_metric_explicit = ("default", attr.evolve(xr, metric=0))
    assert IosXrValidator._diff_bgp_routes_cost(xr_metric_explicit, bf) == []

    xr_vrf_mismatch = ("another-vrf", xr)
    xr_network_mismatch = ("default", attr.evolve(xr, network="1.2.0.0/21"))
    xr_metric_mismatch = ("default", attr.evolve(xr, metric=6))
    xr_loc_pref_mismatch = ("default", attr.evolve(xr, local_preference=101))
    xr_as_path_mismatch = ("default", attr.evolve(xr, as_path=(1, 2, 3)))
    xr_origin_type_mismatch = ("default", attr.evolve(xr, origin_type="i"))
    xr_next_hop_mismatch = ("default", attr.evolve(xr, next_hop_ip="3.3.3.3"))
    xr_next_hop_none = ("default", attr.evolve(xr, next_hop_ip=None))
    xr_weight_mismatch = ("default", attr.evolve(xr, weight=1))
    assert IosXrValidator._diff_bgp_routes_cost(xr_vrf_mismatch, bf) == [
        ("vrf", math.inf)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_network_mismatch, bf) == [
        ("network", math.inf)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_metric_mismatch, bf) == [
        ("metric", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_loc_pref_mismatch, bf) == [
        ("local preference", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_as_path_mismatch, bf) == [
        ("as path", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_origin_type_mismatch, bf) == [
        ("origin type", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_next_hop_mismatch, bf) == [
        ("nhip", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_next_hop_none, bf) == [
        ("nhip/null", 1)
    ]
    assert IosXrValidator._diff_bgp_routes_cost(xr_weight_mismatch, bf) == [
        ("weight", 1)
    ]


def test_difference_matters() -> None:
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.1.1.1/32",
        next_hop=NextHopInterface(interface="Ethernet1", ip="2.2.2.2"),
        next_hop_ip="2.2.2.2",
        next_hop_int="Ethernet1",
        protocol="IBGP",
        as_path="1 2",
        metric=0,
        local_preference=100,
        communities=("1", "2", "3"),
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    xr = IosXrBgpRoute(
        network="1.1.1.1/32",
        next_hop_ip="2.2.2.2",
        best_path=True,
        metric=None,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
    )

    # Leaked routes that only differ in next hop info don't matter
    bf_no_nh_info = attr.evolve(bf, next_hop_ip=None, next_hop_int="dynamic")
    diff = (
        ("default", xr),
        bf_no_nh_info,
        IosXrValidator.compute_bgp_nexthop_cost(xr, bf_no_nh_info),
    )
    show_routes = [
        ("default", xr),
        ("other", xr),
    ]  # indicates xr could have been leaked to VRF default
    assert not IosXrValidator.difference_matters(diff, show_routes)

    # Can't ignore the "leaked" route if it doesn't appear to have been leaked
    assert IosXrValidator.difference_matters(diff, [("default", xr)])

    # Can't ignore the "leaked" route if the BF route has any next hop info
    bf_no_nhip = attr.evolve(bf, next_hop_ip=None)
    diff = (
        ("default", xr),
        bf_no_nhip,
        IosXrValidator.compute_bgp_nexthop_cost(xr, bf_no_nhip),
    )
    assert IosXrValidator.difference_matters(diff, show_routes)
    bf_no_nhint = attr.evolve(bf, next_hop_int="dynamic")
    diff = (
        ("default", xr),
        bf_no_nhint,
        IosXrValidator.compute_bgp_nexthop_cost(xr, bf_no_nhint),
    )
    assert IosXrValidator.difference_matters(diff, show_routes)

    # Can't ignore extra routes or missing routes
    assert IosXrValidator.difference_matters((None, bf, 1.0), [])
    assert IosXrValidator.difference_matters(
        (("default", xr), None, 1.0), [("default", xr)]
    )


def test_could_have_been_leaked() -> None:
    r1 = IosXrBgpRoute(
        network="1.1.1.1/32",
        next_hop_ip="10.10.10.10",
        best_path=True,
        metric=None,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
    )
    r2 = attr.evolve(r1, network="2.2.2.2/32")
    assert not IosXrValidator.could_have_been_leaked(
        ("vrf1", r1), [("vrf1", r1), ("vrf1", r2), ("vrf2", r2)]
    )
    assert IosXrValidator.could_have_been_leaked(
        ("vrf1", r1), [("vrf1", r1), ("vrf1", r2), ("vrf2", r1)]
    )


def test_origin_types() -> None:
    assert IosXrValidator._bgp_origin_type_compatible("igp", "i")
    assert not IosXrValidator._bgp_origin_type_compatible("igp", "e")
    assert not IosXrValidator._bgp_origin_type_compatible("igp", "?")
    assert IosXrValidator._bgp_origin_type_compatible("egp", "e")
    assert not IosXrValidator._bgp_origin_type_compatible("egp", "i")
    assert not IosXrValidator._bgp_origin_type_compatible("egp", "?")
    assert IosXrValidator._bgp_origin_type_compatible("incomplete", "?")
    assert not IosXrValidator._bgp_origin_type_compatible("incomplete", "e")
    assert not IosXrValidator._bgp_origin_type_compatible("incomplete", "i")


def test_interface_props_equal() -> None:
    bf = InterfaceProperties(
        name="GigabitEthernet0/0/0/1.35",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e9),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=int(1e9),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    xr = IosXrInterface(
        name="GigabitEthernet0/0/0/1.35",
        admin_state="up",
        line_protocol="up",
        prefix="1.2.3.4/24",
        mtu=1500,
        bw=1000000,
    )
    assert IosXrValidator._compare_interfaces(xr, bf) == {}


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
    xr = IosXrInterface(
        name="GigabitEthernet0/0/0/1.35",
        admin_state="up",
        line_protocol="up",
        prefix="1.2.3.4/24",
        mtu=1500,
        bw=1000000,
    )
    assert IosXrValidator._compare_interfaces(xr, bf) == {
        "active": "Batfish: False, IOS XR: status=up",
        "bandwidth": "Batfish: 100000000, IOS XR: 1000000000",
        "ipv4 address": "Batfish: ['1.2.3.4/25'], IOS XR: 1.2.3.4/24",
    }


def test_bundle_ether_bandwidth_ignored() -> None:
    bf = InterfaceProperties(
        name="Bundle-Ether99",
        access_vlan=None,
        active=False,
        all_prefixes=["1.2.3.4/24"],
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
    xr = IosXrInterface(
        name="Bundle-Ether99",
        admin_state="down",
        line_protocol="up",
        prefix="1.2.3.4/24",
        mtu=1500,
        bw=0,
    )
    assert IosXrValidator._compare_interfaces(xr, bf) == {}


def test_diff_routes_cost_nhint_dynamic() -> None:
    expected_route = IosXrRoute(
        network="2.2.2.0/24",
        protocol="connected",
        next_hop_ip="3.4.5.6",
        next_hop_int=None,
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("nhip", 1.0)
    ]  # next hop IP


def test_compat_routes_null_next_hop_int() -> None:
    expected_route = IosXrRoute(
        network="2.2.2.0/24",
        protocol="static",
        next_hop_ip=None,
        next_hop_int="Null0",
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_diff_routes_cost_null_int() -> None:
    expected_route = IosXrRoute(
        network="2.2.2.0/24",
        protocol="static",
        next_hop_ip=None,
        next_hop_int="Ethernet1",
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("asymmetric null route", 10.0)
    ]  # only one side null


def test_diff_routes_cost_nhint_ignore() -> None:
    expected_route = IosXrRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int="iface1",  # will be ignored
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_diff_routes_cost_skip_ibgp_comparision() -> None:
    """
    Test skipping when real_data protocol is `bgp` & batfish protocol is `ibgp`
    """
    expected_route = IosXrRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int=None,
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_diff_routes_cost_route_in_multiple_vrf() -> None:
    """
    Test that route in different vrf return math.inf
    """
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="10.34.31.2",
        next_hop_int=None,
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("vrf", math.inf)
    ]


def test_ospf_summary_ignores_ad_and_metric() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="ospfIS",
        next_hop_ip=None,
        next_hop_int="Null0",
        next_hop_vrf=None,
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
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_compute_protocol_cost() -> None:
    # Batfish reports generated routes as aggregate routes
    result = IosXrValidator.compute_protocol_cost("bgp", "aggregate")
    assert result == []

    result = IosXrValidator.compute_protocol_cost("bgp", "ibgp")
    assert result == []

    result = IosXrValidator.compute_protocol_cost("ospf", "ospfE1")
    assert result == [("ospf subtype", 1.0)]

    result = IosXrValidator.compute_protocol_cost("eigrp", "eigrpEX")
    assert result == [("eigrp subtype", 1.0)]

    result = IosXrValidator.compute_protocol_cost("bgp", "ospf")
    assert result == [("protocol", math.inf)]


def test_compute_next_hop_cost() -> None:
    xr_route = IosXrRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="direct",
        next_hop_ip="192.168.122.3",
        next_hop_int="Ethernet1",
        next_hop_vrf=None,
        admin=0,
        metric=0,
    )

    assert (
        IosXrValidator.compute_next_hop_cost(
            xr_route, NextHopInterface(interface="Ethernet1")
        )
        == []
    )
    # NHINT mismatch
    assert IosXrValidator.compute_next_hop_cost(
        attr.evolve(xr_route, next_hop_int="Ethernet2"),
        NextHopInterface(interface="Ethernet1"),
    ) == [("nhint", 5.0)]
    # NHINT missing from Batfish (static nhint route should have it)
    assert IosXrValidator.compute_next_hop_cost(
        attr.evolve(xr_route, next_hop_int="Ethernet2", protocol="static"),
        NextHopIp(ip="192.168.122.3"),
    ) == [("asymmetric nhint", 5.0)]
    # NHINT missing from Batfish correctly (static nhip route)
    assert (
        IosXrValidator.compute_next_hop_cost(
            attr.evolve(xr_route, next_hop_int=None, protocol="static"),
            NextHopIp(ip="192.168.122.3"),
        )
        == []
    )
    # NHIP present and mismatch
    assert IosXrValidator.compute_next_hop_cost(
        xr_route, NextHopIp(ip="192.168.122.4")
    ) == [("nhip", 1.0)]
    # Asymmetric null route, both directions
    assert IosXrValidator.compute_next_hop_cost(xr_route, NextHopDiscard()) == [
        ("asymmetric null route", 10.0)
    ]
    assert IosXrValidator.compute_next_hop_cost(
        attr.evolve(xr_route, next_hop_int="Null0"), NextHopIp(ip="192.168.122.4")
    ) == [("asymmetric null route", 10.0)]

    # VRF leaked route
    assert (
        IosXrValidator.compute_next_hop_cost(
            attr.evolve(xr_route, protocol="bgp", next_hop_vrf="vrf"),
            NextHopVrf(vrf="vrf"),
        )
        == []
    )
    assert IosXrValidator.compute_next_hop_cost(
        attr.evolve(xr_route, protocol="bgp", next_hop_vrf="vrf"),
        NextHopIp(ip="1.1.1.1"),
    ) == [("vrf leak mismatch", 10.0)]


def test_is_local_route() -> None:
    # A local route
    r = IosXrBgpRoute(
        network="1.1.1.0/24",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="e",
    )
    assert IosXrValidator.is_local_route(r)

    # Route must have weight 32768 and next hop IP 0.0.0.0 to be ignored
    assert not IosXrValidator.is_local_route(attr.evolve(r, next_hop_ip="2.2.2.2"))
    assert not IosXrValidator.is_local_route(attr.evolve(r, weight=300))


def test_mgmt_route_skipped() -> None:
    batfish_routes = []
    real_routes = [
        IosXrRoute(
            vrf="default",
            network="192.168.122.0/24",
            protocol="connected",
            next_hop_ip=None,
            admin=0,
            metric=0,
            next_hop_int="MgmtEth0/RP0/CPU0/0",
            next_hop_vrf=None,
        )
    ]
    assert IosXrValidator._validate_main_rib_routes(batfish_routes, real_routes) == {}


def test_leak_interface_route_match() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip=None,
        next_hop_int="Null0",
        next_hop_vrf="v2",
        admin=0,  # not in show output
        metric=0,  # not in show output
        vrf="v1",
    )
    batfish_route = MainRibRoute(
        vrf="v1",
        network="192.168.122.0/24",
        next_hop=NextHopVrf(vrf="v2"),
        protocol="bgp",
        tag=None,
        metric=50,  # arbitrary
        admin=20,  # default for leaked interface route
    )
    # Ignore different admin, metric
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_leak_nhip_route_match() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="1.1.1.1",
        next_hop_int=None,
        next_hop_vrf="v2",
        admin=20,
        metric=50,
        vrf="v1",
    )
    batfish_route = MainRibRoute(
        vrf="v1",
        network="192.168.122.0/24",
        next_hop=NextHopVrf(vrf="v2"),
        protocol="bgp",
        tag=None,
        metric=50,
        admin=20,
    )
    # Ignore missing next_hop_ip
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == []


def test_leak_nhip_route_diff_admin() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="1.1.1.1",
        next_hop_int=None,
        next_hop_vrf="v2",
        admin=20,
        metric=50,
        vrf="v1",
    )
    batfish_route = MainRibRoute(
        vrf="v1",
        network="192.168.122.0/24",
        next_hop=NextHopVrf(vrf="v2"),
        protocol="bgp",
        tag=None,
        metric=50,
        admin=30,
    )
    # Ignore missing next_hop_ip
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("admin", 1.0)
    ]


def test_leak_nhip_route_diff_cost() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="1.1.1.1",
        next_hop_int=None,
        next_hop_vrf="v2",
        admin=20,
        metric=50,
        vrf="v1",
    )
    batfish_route = MainRibRoute(
        vrf="v1",
        network="192.168.122.0/24",
        next_hop=NextHopVrf(vrf="v2"),
        protocol="bgp",
        tag=None,
        metric=100,
        admin=20,
    )
    # Ignore missing next_hop_ip
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("metric", 1.0)
    ]


def test_non_leak_bgp_diff_nhip() -> None:
    expected_route = IosXrRoute(
        network="192.168.122.0/24",
        protocol="bgp",
        next_hop_ip="1.1.1.1",
        next_hop_int=None,
        next_hop_vrf=None,
        admin=20,
        metric=50,
        vrf="v1",
    )
    batfish_route = MainRibRoute(
        vrf="v1",
        network="192.168.122.0/24",
        next_hop=NextHopIp(ip="2.2.2.2"),
        protocol="bgp",
        tag=None,
        metric=50,
        admin=20,
    )
    # Ignore missing next_hop_ip
    assert IosXrValidator._diff_routes_cost(expected_route, batfish_route) == [
        ("nhip", 1.0)
    ]
