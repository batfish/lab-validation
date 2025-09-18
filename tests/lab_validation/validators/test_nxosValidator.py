import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface
from pybatfish.datamodel.route import NextHopIp, NextHopVtep

from lab_validation.parsers.nxos.models.interfaces import NxosInterface
from lab_validation.parsers.nxos.models.routes import NxosBgpRoute, NxosMainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.NxosValidator import NxosValidator


def test_tag_compatible() -> None:
    assert NxosValidator._tag_compatible(5, 5)
    assert NxosValidator._tag_compatible(None, 0)
    assert NxosValidator._tag_compatible(0, None)
    assert not NxosValidator._tag_compatible(1, None)
    assert not NxosValidator._tag_compatible(None, 1)
    assert not NxosValidator._tag_compatible(0, 1)


def test_compute_protocol_cost() -> None:
    # Anything equal is equal, even if nonsense
    assert NxosValidator.compute_protocol_cost("bar", "bar") == []
    # Direct vs connected
    assert NxosValidator.compute_protocol_cost("direct", "connected") == []
    # BGP is actually distinguished
    assert NxosValidator.compute_protocol_cost("bgp", "bgp") == []
    assert NxosValidator.compute_protocol_cost("bgp", "ibgp") == [("bgp subtype", 1.0)]
    assert NxosValidator.compute_protocol_cost("ibgp", "ibgp") == []
    assert NxosValidator.compute_protocol_cost("ibgp", "bgp") == [("bgp subtype", 1.0)]
    # BGP aggregates are special
    assert NxosValidator.compute_protocol_cost("bgp", "aggregate") == []
    # OSPF is actually distinguished
    assert NxosValidator.compute_protocol_cost("ospfE1", "ospf") == [
        ("ospf subtype", 1.0)
    ]
    # Incompatible protocols are infinite
    assert NxosValidator.compute_protocol_cost("bgp", "ospf") == [
        ("protocol", math.inf)
    ]


def test_compute_bgp_protocol_cost() -> None:
    assert NxosValidator.compute_bgp_protocol_cost("bgp", "bgp") == []
    assert NxosValidator.compute_bgp_protocol_cost("bgp", "ibgp") == [
        ("bgp subtype", 1.0)
    ]
    assert NxosValidator.compute_bgp_protocol_cost("ibgp", "ibgp") == []
    assert NxosValidator.compute_bgp_protocol_cost("ibgp", "bgp") == [
        ("bgp subtype", 1.0)
    ]
    assert NxosValidator.compute_bgp_protocol_cost("bgp_aggregate", "aggregate") == []


def test_compute_next_hop_cost() -> None:
    nxos_route = NxosMainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="direct",
        next_vrf=None,
        next_hop_ip="192.168.122.3",
        next_hop_int="Ethernet1",
        admin=0,
        metric=0,
        tag=0,
        evpn=False,
        segid=None,
        tunnelid=None,
    )
    assert (
        NxosValidator.compute_next_hop_cost(
            nxos_route, NextHopInterface(interface="Ethernet1")
        )
        == []
    )
    # NHINT mismatch
    assert NxosValidator.compute_next_hop_cost(
        attr.evolve(nxos_route, next_hop_int="Ethernet2"),
        NextHopInterface(interface="Ethernet1"),
    ) == [("nhint", 5.0)]
    # NHINT missing from Batfish (static nhint route should have it)
    assert NxosValidator.compute_next_hop_cost(
        attr.evolve(nxos_route, next_hop_int="Ethernet2", protocol="static"),
        NextHopIp(ip="192.168.122.3"),
    ) == [("asymmetric nhint", 5.0)]
    # NHINT missing from Batfish correctly (static nhip route)
    assert (
        NxosValidator.compute_next_hop_cost(
            attr.evolve(nxos_route, next_hop_int=None, protocol="static"),
            NextHopIp(ip="192.168.122.3"),
        )
        == []
    )
    # NHIP present and mismatch
    assert NxosValidator.compute_next_hop_cost(
        nxos_route, NextHopIp(ip="192.168.122.4")
    ) == [("nhip", 1.0)]


def test_compute_next_hop_cost_null_routed() -> None:
    nxos_route = NxosMainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="static",
        next_vrf=None,
        next_hop_ip=None,
        next_hop_int="Null0",
        admin=0,
        metric=0,
        tag=0,
        evpn=False,
        segid=None,
        tunnelid=None,
    )

    # Matching null route
    assert NxosValidator.compute_next_hop_cost(nxos_route, NextHopDiscard()) == []

    # Asymmetric null route, both directions
    assert NxosValidator.compute_next_hop_cost(
        nxos_route, NextHopIp(ip="192.168.122.3")
    ) == [("asymmetric null route", 10.0)]
    assert NxosValidator.compute_next_hop_cost(
        attr.evolve(nxos_route, next_hop_int="Ethernet1"), NextHopDiscard()
    ) == [("asymmetric null route", 10.0)]


def test_compute_next_hop_cost_vtep() -> None:
    nxos_route = NxosMainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="bgp",
        next_vrf="default",
        next_hop_ip="2.2.2.2",
        next_hop_int=None,
        admin=0,
        metric=0,
        tag=0,
        evpn=True,
        segid=100777,
        tunnelid="2.2.2.2",
    )

    # Matching vtep route
    assert (
        NxosValidator.compute_next_hop_cost(
            nxos_route, NextHopVtep(vni=100777, vtep="2.2.2.2")
        )
        == []
    )

    # Mismatches inside vtep
    assert NxosValidator.compute_next_hop_cost(
        nxos_route, NextHopVtep(vni=100776, vtep="2.2.2.2")
    ) == [("vni", 1.0)]
    assert NxosValidator.compute_next_hop_cost(
        nxos_route, NextHopVtep(vni=100777, vtep="1.1.1.1")
    ) == [("vtep", 1.0)]

    # Vtep and non-vtep
    assert NxosValidator.compute_next_hop_cost(nxos_route, NextHopDiscard()) == [
        ("asymmetric vtep", 10.0)
    ]
    # Vtep and non-vtep
    assert NxosValidator.compute_next_hop_cost(
        attr.evolve(nxos_route, evpn=False, segid=None, tunnelid=None),
        NextHopVtep(vni=100777, vtep="1.1.1.1"),
    ) == [("asymmetric vtep", 10.0)]


def test_compute_next_hop_cost_static() -> None:
    """
    NXOS static routes that resolve to a tunnel have segid and tunnelid set, but the EVPN field is not set.

    Check that such routes are compared correctly.
    """
    nxos_route = NxosMainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="static",
        next_vrf=None,
        next_hop_ip="2.2.2.2",
        next_hop_int=None,
        admin=1,
        metric=0,
        tag=0,
        evpn=False,
        segid=100777,
        tunnelid="12.12.12.12",
    )

    # BF has matching static route
    assert (
        NxosValidator.compute_next_hop_cost(nxos_route, NextHopIp(ip="2.2.2.2")) == []
    )

    # BF has EVPN route
    assert NxosValidator.compute_next_hop_cost(
        nxos_route, NextHopVtep(vni=100777, vtep="2.2.2.2")
    ) == [("asymmetric vtep", 10.0)]


def test_diff_routes_cost() -> None:
    nxos_route = NxosMainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        protocol="direct",
        next_vrf=None,
        next_hop_ip="192.168.122.3",
        next_hop_int="Ethernet1",
        admin=0,
        metric=0,
        tag=0,
        evpn=False,
        segid=None,
        tunnelid=None,
    )
    batfish_route = MainRibRoute(
        vrf="default",
        network="192.168.122.0/24",
        next_hop=NextHopInterface(interface="Ethernet1"),
        protocol="connected",
        metric=0,
        admin=0,
        tag=0,
    )
    assert NxosValidator._diff_routes_cost(batfish_route, nxos_route) == []
    # admin mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, admin=5)
    ) == [("admin", 2.0)]
    # metric mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, metric=5)
    ) == [("metric", 1.0)]
    # tag mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, tag=5)
    ) == [("tag", 1.0)]
    # next-hop mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, next_hop_int="Ethernet2")
    ) == [("nhint", 5.0)]
    # protocol mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, protocol="bgp")
    ) == [("protocol", math.inf)]
    # network mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, network="0.0.0.0/0")
    ) == [("network", math.inf)]
    # vrf mismatch
    assert NxosValidator._diff_routes_cost(
        batfish_route, attr.evolve(nxos_route, vrf="vrf")
    ) == [("vrf", math.inf)]


def test_bgp_equal() -> None:
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopInterface(interface="Ethernet1"),
        next_hop_ip="removeme",
        next_hop_int="removeme",
        protocol="ibgp",
        as_path="1 2",
        metric=5,
        local_preference=100,
        communities=("1", "2", "3"),
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=5,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
        protocol="ibgp",
    )
    assert NxosValidator._diff_bgp_routes_cost(bf, nxos) == []


def test_bgp_non_best_path() -> None:
    # Non-best-path show route should be ignored
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="2.2.2.2",
        best_path=False,
        metric=5,
        local_preference=100,
        weight=0,
        as_path=(1, 2),
        origin_type="e",
        protocol="bgp",
    )
    assert NxosValidator._validate_bgp_rib_routes([nxos], []) == {}


def test_bgp_compare_local_routes() -> None:
    # This batfish route should be interpreted as a local route
    bf = BgpRibRoute(
        weight=32768,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopDiscard(),
        next_hop_ip="AUTO/NONE(-1l)",
        next_hop_int="null_interface",
        protocol="bgp",
        as_path="",
        metric=0,
        local_preference=100,
        communities=(),
        origin_protocol="STATIC",
        origin_type="incomplete",
        tag=None,
    )
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
        protocol="bgp",
    )
    assert NxosValidator._diff_bgp_routes_cost(bf, nxos) == []


def test_diff_bgp_next_hop_cost_discard() -> None:
    nh = NextHopDiscard()
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
        protocol="bgp",
    )
    assert NxosValidator._diff_bgp_next_hop_cost(nh, nxos) == []

    mismatch_ip = attr.evolve(nxos, next_hop_ip="1.1.1.1")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_ip) == [("nhip", 2.0)]


def test_diff_bgp_next_hop_cost_ip() -> None:
    nh = NextHopIp("1.1.1.1")
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="1.1.1.1",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
        protocol="bgp",
    )
    assert NxosValidator._diff_bgp_next_hop_cost(nh, nxos) == []

    mismatch_ip = attr.evolve(nxos, next_hop_ip="2.2.2.2")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_ip) == [("nhip", 1.0)]

    mismatch_discard = attr.evolve(nxos, next_hop_ip="0.0.0.0")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_discard) == [
        ("nhip", 2.0)
    ]


def test_diff_bgp_next_hop_cost_interface() -> None:
    nh = NextHopInterface("Ethernet0")
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
        protocol="bgp",
    )
    assert NxosValidator._diff_bgp_next_hop_cost(nh, nxos) == []

    mismatch_ip = attr.evolve(nxos, next_hop_ip="1.1.1.1")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_ip) == [("nhip", 2.0)]


def test_diff_bgp_next_hop_cost_vtep() -> None:
    nh = NextHopVtep(1, "1.1.1.1")
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="1.1.1.1",
        best_path=True,
        metric=0,
        local_preference=100,
        weight=32768,
        as_path=(),
        origin_type="?",
        protocol="bgp",
    )
    assert NxosValidator._diff_bgp_next_hop_cost(nh, nxos) == []

    mismatch_ip = attr.evolve(nxos, next_hop_ip="2.2.2.2")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_ip) == [("nhip", 1.0)]

    mismatch_discard = attr.evolve(nxos, next_hop_ip="0.0.0.0")
    assert NxosValidator._diff_bgp_next_hop_cost(nh, mismatch_discard) == [
        ("nhip", 2.0)
    ]


def test_bgp_not_equal() -> None:
    """Test when the routes don't match."""
    bf = BgpRibRoute(
        weight=0,
        vrf="default",
        network="1.2.3.4/20",
        next_hop=NextHopInterface(interface="Ethernet1"),
        next_hop_ip="removemelater",
        next_hop_int="removemelater",
        protocol="ibgp",
        as_path="1 2",
        metric=5,
        local_preference=100,
        communities=("1", "2", "3"),
        origin_protocol=None,
        origin_type="egp",
        tag=None,
    )
    nxos = NxosBgpRoute(
        vrf="default",
        network="1.2.3.4/20",
        next_hop_ip="0.0.0.0",
        best_path=True,
        metric=6,
        local_preference=101,
        weight=1,
        as_path=(1, 2, 3),
        origin_type="i",
        protocol="bgp",
    )
    assert set(NxosValidator._diff_bgp_routes_cost(bf, nxos)) == {
        ("bgp subtype", 1.0),
        ("as_path", 1.0),
        ("local_preference", 1.0),
        ("origin_type", 1.0),
        ("metric", 1.0),
        ("weight", 1.0),
    }


def test_origin_types() -> None:
    assert NxosValidator._bgp_origin_type_compatible("igp", "i")
    assert not NxosValidator._bgp_origin_type_compatible("igp", "e")
    assert not NxosValidator._bgp_origin_type_compatible("igp", "?")
    assert NxosValidator._bgp_origin_type_compatible("egp", "e")
    assert not NxosValidator._bgp_origin_type_compatible("egp", "i")
    assert not NxosValidator._bgp_origin_type_compatible("egp", "?")
    assert NxosValidator._bgp_origin_type_compatible("incomplete", "?")
    assert not NxosValidator._bgp_origin_type_compatible("incomplete", "e")
    assert not NxosValidator._bgp_origin_type_compatible("incomplete", "i")


def test_interface_equal() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=1500,
        bandwidth=10000000,
        mode=None,
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )

    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {}


def test_interface_equal_switchport_mode() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=1500,
        bandwidth=10000000,
        mode="access",
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode="ACcess",
        vrf="default",
    )

    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {}


def test_interface_not_equal_active() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=1500,
        bandwidth=10000000,
        mode=None,
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=False,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )

    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {
        "active": "Batfish: False, NXOS: admin=True line=True"
    }


def test_interface_not_equal_bandwidth() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=1500,
        bandwidth=1,
        mode=None,
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {
        "bandwidth": "Batfish: 10000000, NXOS: 1"
    }


def test_interface_not_equal_mtu() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=15,
        bandwidth=10000000,
        mode=None,
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {
        "mtu": "Batfish: 1500, NXOS: 15"
    }


def test_interface_not_equal_switchport() -> None:
    nxos_interface = NxosInterface(
        name="Ethernet1/2",
        admin=True,
        line=True,
        mtu=1500,
        bandwidth=10000000,
        mode="access",
    )

    bf_interface = InterfaceProperties(
        name="Ethernet1/2",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/25"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )

    assert NxosValidator._compare_interfaces(nxos_interface, bf_interface) == {
        "switchport_mode": "Batfish: None, NXOS: access"
    }


def test_mgmt_route_skipped() -> None:
    batfish_routes = []
    real_routes = [
        NxosMainRibRoute(
            vrf="default",
            network="192.168.122.0/24",
            protocol="direct",
            next_vrf=None,
            next_hop_ip=None,
            next_hop_int="mgmt0",
            admin=0,
            metric=0,
            tag=0,
            evpn=False,
            segid=None,
            tunnelid=None,
        )
    ]
    assert NxosValidator._validate_main_rib_routes(batfish_routes, real_routes) == {}
