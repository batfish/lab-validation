import math

from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.frr.models.interfaces import FrrInterface
from lab_validation.parsers.frr.models.routes import FrrIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import MainRibRoute
from lab_validation.validators.CumulusFrrValidator import (
    CumulusFrrValidator,
    compute_protocol_cost,
)
from lab_validation.validators.utils.validation_utils import match_pairs


def test_compare_interface_equal() -> None:
    show_interfaces = [
        FrrInterface(name="swp1", bandwidth=int(1e5), mtu=1500, admin=True, line=True)
    ]
    batfish_interfaces = [
        InterfaceProperties(
            name="swp1",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/24"],
            allowed_vlans=None,
            bandwidth=int(1e5),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    results = CumulusFrrValidator._compare_all_interfaces(
        show_interfaces, batfish_interfaces
    )
    assert results == {
        "batfish_extra": {},
        "batfish_mismatch": {},
        "batfish_missing": {},
    }


def test_compare_interface_batfish_mismatch() -> None:
    """Test that mismatched parameters of an interface"""
    show_interfaces = [
        FrrInterface(name="swp1", bandwidth=int(1e5), mtu=1500, admin=False, line=False)
    ]
    batfish_interfaces = [
        InterfaceProperties(
            name="swp1",
            access_vlan=None,
            active=False,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e6),
            description=None,
            native_vlan=None,
            mtu=1501,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    results = CumulusFrrValidator._compare_all_interfaces(
        show_interfaces, batfish_interfaces
    )
    assert results["batfish_mismatch"] == {
        "swp1": {
            "bandwidth": "Batfish: 1000000, show_data: " "100000",
            "mtu": "Batfish: 1501, show_data: 1500",
        }
    }


def test_compare_interfaces_batfish_missing() -> None:
    show_interfaces = [
        FrrInterface(name="swp1", bandwidth=int(1e5), mtu=1500, admin=True, line=True)
    ]
    batfish_interfaces = []

    results = CumulusFrrValidator._compare_all_interfaces(
        show_interfaces, batfish_interfaces
    )
    assert results["batfish_missing"] == {
        "swp1": FrrInterface(
            name="swp1", bandwidth=100000, mtu=1500, admin=True, line=True
        )
    }


def test_compare_interfaces_batfish_extra() -> None:
    show_interfaces = []
    batfish_interfaces = [
        InterfaceProperties(
            name="swp1",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e6),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]

    results = CumulusFrrValidator._compare_all_interfaces(
        show_interfaces, batfish_interfaces
    )
    assert results["batfish_extra"] == {
        "swp1": InterfaceProperties(
            name="swp1",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=1000000,
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=1000,
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    }


def test_diff_routes_cost_nhint_mismatch() -> None:
    show_route = FrrIpRoute(
        network="10.10.40.0/24",
        protocol="connected",
        next_hop_ip=None,
        next_hop_int="swp1",
        admin_distance=0,
        metric=0,
        vrf="vrf",
        active=True,
        blackhole=False,
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="10.10.40.0/24",
        next_hop=NextHopInterface(interface="swp3"),
        protocol="connected",
        tag=None,
        metric=0,
        admin=0,
    )
    assert CumulusFrrValidator._diff_routes_cost(show_route, batfish_route) == 3.0


def test_diff_routes_cost_blackhole_match() -> None:
    show_route = FrrIpRoute(
        network="10.10.40.0/24",
        protocol="ospf",
        next_hop_ip=None,
        next_hop_int=None,
        admin_distance=0,
        metric=0,
        vrf="vrf",
        active=True,
        blackhole=True,
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="10.10.40.0/24",
        next_hop=NextHopDiscard(),
        protocol="ospfIS",
        tag=None,
        metric=0,
        admin=0,
    )
    assert CumulusFrrValidator._diff_routes_cost(show_route, batfish_route) == 0.0


def test_diff_routes_cost_blackhole_mismatch() -> None:
    show_route = FrrIpRoute(
        network="10.10.40.0/24",
        protocol="ospf",
        next_hop_ip=None,
        next_hop_int=None,
        admin_distance=0,
        metric=0,
        vrf="vrf",
        active=True,
        blackhole=True,
    )
    batfish_route = MainRibRoute(
        vrf="vrf",
        network="10.10.40.0/24",
        next_hop=NextHopInterface(interface="swp1"),
        protocol="ospfIS",
        tag=None,
        metric=0,
        admin=0,
    )
    assert CumulusFrrValidator._diff_routes_cost(show_route, batfish_route) == 10.0


def test_diff_routes_cost_nhint_ignore() -> None:
    show_route = FrrIpRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int="iface1",  # will be ignored
        admin_distance=1,
        metric=0,
        vrf="vrf",
        active=True,
        blackhole=False,
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
    assert CumulusFrrValidator._diff_routes_cost(show_route, batfish_route) == 0.0


def test_show_route_processed_update_vrf() -> None:
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf=None,
            active=True,
            blackhole=False,
        ),
    ]

    assert CumulusFrrValidator("")._show_route_processed(show_route)[0] == FrrIpRoute(
        network="1.2.3.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.1",
        next_hop_int="swp1",
        admin_distance=20,
        metric=0,
        vrf="default",
        active=True,
        blackhole=False,
    )


def test_match_pairs_single_route_equal() -> None:
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp1", ip="1.2.3.1"),
            admin=20,
            metric=0,
            vrf="default",
            tag=None,
        ),
    ]
    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 0
    )


def test_match_pairs_single_route_not_equal() -> None:
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="4.5.6.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp1", ip="1.2.3.1"),
            admin=20,
            metric=0,
            vrf="default",
            tag=None,
        ),
    ]

    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == math.inf
    )


def test_match_pairs_single_route_attribute_mismatch() -> None:
    """Changing AD & Metric of batfish_route so mismatch == 2"""
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp1", ip="1.2.3.1"),
            admin=0,  # changed for mismatch
            metric=20,  # changed for mismatch
            vrf="default",
            tag=None,
        ),
    ]

    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 2
    )


def test_match_pairs_ecmp_route_equal() -> None:
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.10",
            next_hop_int="swp10",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp1", ip="1.2.3.1"),
            admin=20,
            metric=0,
            vrf="default",
            tag=None,
        ),
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp10", ip="1.2.3.10"),
            admin=20,
            metric=0,
            vrf="default",
            tag=None,
        ),
    ]
    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 0
    )
    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            1
        ][2]
        == 0
    )


def test_match_pairs_ecmp_route_not_equal() -> None:
    show_route = [
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.1",
            next_hop_int="swp1",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
        FrrIpRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop_ip="1.2.3.10",
            next_hop_int="swp10",
            admin_distance=20,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp1", ip="1.2.3.1"),
            admin=120,
            metric=10,
            vrf="default",
            tag=None,
        ),
        MainRibRoute(
            network="1.2.3.0/24",
            protocol="bgp",
            next_hop=NextHopInterface(interface="swp10", ip="1.2.3.10"),
            admin=220,
            metric=20,
            vrf="default",
            tag=None,
        ),
    ]
    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 2
    )
    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            1
        ][2]
        == 2
    )


def test_match_pairs_static_route_ip() -> None:
    """Changing AD & Metric of batfish_route so mismatch == 2"""
    show_route = [
        FrrIpRoute(
            network="1.2.3.4/32",
            protocol="static",
            next_hop_ip="10.10.40.1",
            next_hop_int="swp1",
            admin_distance=1,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.4/32",
            protocol="static",
            next_hop=NextHopIp(ip="10.10.40.1"),
            admin=1,
            metric=0,
            vrf="default",
            tag=None,
        ),
    ]

    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 0
    )


def test_match_pairs_static_route_interface() -> None:
    """Changing AD & Metric of batfish_route so mismatch == 2"""
    show_route = [
        FrrIpRoute(
            network="1.2.3.4/32",
            protocol="static",
            next_hop_ip=None,
            next_hop_int="swp1",
            admin_distance=1,
            metric=0,
            vrf="default",
            active=True,
            blackhole=False,
        ),
    ]

    batfish_route = [
        MainRibRoute(
            network="1.2.3.4/32",
            protocol="static",
            next_hop=NextHopInterface(interface="swp1"),
            admin=1,
            metric=0,
            vrf="default",
            tag=None,
        ),
    ]

    assert (
        match_pairs(show_route, batfish_route, CumulusFrrValidator._diff_routes_cost)[
            0
        ][2]
        == 0
    )


def test_compute_protocol_cost() -> None:
    """Test the custom protocol differ."""
    assert compute_protocol_cost("connected", "connected") == 0

    assert compute_protocol_cost("static", "static") == 0

    assert compute_protocol_cost("bgp", "bgp") == 0
    assert compute_protocol_cost("bgp", "ibgp") == 0

    assert compute_protocol_cost("ospf", "ospf") == 0
    assert compute_protocol_cost("ospf", "ospfIA") == 0
    assert compute_protocol_cost("ospf", "ospfE1") == 0
    assert compute_protocol_cost("ospf", "ospfE2") == 0
    assert compute_protocol_cost("ospf", "ospfIS") == 0

    assert compute_protocol_cost("ospf", "bgp") == math.inf
    assert compute_protocol_cost("connected", "static") == math.inf
