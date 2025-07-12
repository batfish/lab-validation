import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.junos.commands.interfaces import _to_bandwidth
from lab_validation.parsers.junos.models.interfaces import (
    JunosInterface,
    JunosInterfaceState,
)
from lab_validation.parsers.junos.models.routes import JunosBgpRoute, JunosMainRibRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.batfish_models.runtime_data import InterfaceRuntimeData
from lab_validation.validators.JunosValidator import (
    JunosValidator,
    _compute_nexthop_cost,
    _compute_protocol_cost,
    _routes_cost,
    filter_route,
)


def test_routes_cost() -> None:
    junos_route = JunosMainRibRoute(
        network="1.1.1.1/32",
        protocol="BGP",
        next_hop_ip="1.1.1.2",
        next_hop_int="iface",
        admin=1,
        metric=2,
        vrf="vrf",
        nh_type=None,
        active=True,
    )
    batfish_route = MainRibRoute(
        network="1.1.1.1/32",
        protocol="ibgp",
        next_hop=NextHopIp(ip="1.1.1.2"),
        admin=1,
        metric=2,
        tag=0,
        vrf="vrf",
    )
    # Routes are compatible
    assert _routes_cost(junos_route, batfish_route) == 0.0

    # Wrong vrf -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, vrf="vrf2")) == math.inf

    # Wrong network -> routes are incompatible
    assert (
        _routes_cost(junos_route, attr.evolve(batfish_route, network="1.1.1.1/30"))
        == math.inf
    )

    # Wrong protocol -> routes are incompatible
    assert (
        _routes_cost(junos_route, attr.evolve(batfish_route, protocol="ospf"))
        == math.inf
    )

    # Wrong metric -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, metric=5)) == 1.0

    # Wrong admin -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, admin=5)) == 1.0


def test_nexthop_cost_static_routes() -> None:
    """Test next-hop costs for different types of static next-hop routes."""
    junos_route = JunosMainRibRoute(
        vrf="default",
        network="0.0.0.0/0",
        protocol="Static",
        admin=5,
        metric=0,
        next_hop_ip="10.12.1.1",
        next_hop_int="xe-0/0/1.0",
        nh_type=None,
        active=True,
    )
    # Batfish NHIP routes are compatible with JunOS routes that have a resolved NHINT
    assert _compute_nexthop_cost(junos_route, NextHopIp(ip="10.12.1.1")) == 0.0
    # Since Batfish shows protocol NHOP while JunOS shows resolved, cannot enforce
    # that they appear equal
    assert _compute_nexthop_cost(junos_route, NextHopIp(ip="10.12.1.2")) == 0.0

    # Also compatible if it's a Batfish NHINT + NHIP route.
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.0", ip="10.12.1.1")
        )
        == 0.0
    )
    # Incompatible if either NHIP or NHINT is wrong
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.1", ip="10.12.1.1")
        )
        == 5.0
    )
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.0", ip="10.12.1.2")
        )
        == 1.0
    )


def test_nexthop_cost_ospf_routes() -> None:
    """Test next-hop costs for different types of interface next-hop routes."""
    junos_route = JunosMainRibRoute(
        vrf="default",
        network="1.1.1.1/32",
        protocol="OSPF",
        admin=10,
        metric=2,
        next_hop_ip="2.2.2.2",
        next_hop_int="xe-0/0/1.0",
        nh_type=None,
        active=True,
    )
    # next-hop interface matches
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.0", ip="2.2.2.2")
        )
        == 0.0
    )

    # next-hop interface does not match
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.1", ip="2.2.2.2")
        )
        == 5.0
    )


def test_nexthop_cost_discard() -> None:
    """Test next-hop costs for null routes."""
    junos_route = JunosMainRibRoute(
        vrf="default",
        network="0.0.0.0/0",
        protocol="Static",
        admin=5,
        metric=0,
        next_hop_ip=None,
        next_hop_int=None,
        nh_type="Discard",
        active=True,
    )
    # Batfish null routes are compatible with junos null routes
    assert _compute_nexthop_cost(junos_route, NextHopDiscard()) == 0.0
    # Not a null route -> incompatible
    assert (
        _compute_nexthop_cost(junos_route, NextHopInterface(interface="xe-0/1/0.0"))
        == 10.0
    )


def test_nexthop_cost_reject() -> None:
    """Test next-hop costs for null routes."""
    junos_route = JunosMainRibRoute(
        vrf="default",
        network="0.0.0.0/0",
        protocol="Aggregate",
        admin=5,
        metric=0,
        next_hop_ip=None,
        next_hop_int=None,
        nh_type="Reject",
        active=True,
    )

    # Batfish null aggregates are compatible with junos null routes
    assert _compute_nexthop_cost(junos_route, NextHopDiscard()) == 0.0
    # Not a null route -> incompatible
    assert (
        _compute_nexthop_cost(junos_route, NextHopInterface(interface="xe-0/1/0.0"))
        == 10.0
    )


def test_protocol_cost() -> None:
    junos_static = JunosMainRibRoute(
        vrf="default",
        network="0.0.0.0/0",
        protocol="Static",
        admin=5,
        metric=0,
        next_hop_ip=None,
        next_hop_int=None,
        nh_type="Discard",
        active=True,
    )
    bf_static = MainRibRoute(
        network="0.0.0.0/0",
        protocol="static",
        next_hop=NextHopDiscard(),
        admin=5,
        metric=0,
        tag=0,
        vrf="default",
    )

    # Static and static work
    assert _compute_protocol_cost(junos_static, bf_static) == 0.0
    # Static and not static doesn't
    assert (
        _compute_protocol_cost(junos_static, attr.evolve(bf_static, protocol="ospf"))
        == math.inf
    )

    # Direct and connected work
    junos_direct = attr.evolve(junos_static, protocol="Direct")
    assert (
        _compute_protocol_cost(
            junos_direct, attr.evolve(bf_static, protocol="connected")
        )
        == 0.0
    )
    # Direct and static doesn't
    assert _compute_protocol_cost(junos_direct, bf_static) == math.inf

    # Local and Local work
    junos_local = attr.evolve(junos_static, protocol="Local")
    assert (
        _compute_protocol_cost(junos_local, attr.evolve(bf_static, protocol="local"))
        == 0.0
    )
    # Local and static doesn't
    assert _compute_protocol_cost(junos_local, bf_static) == math.inf

    # Aggregate and aggregate work
    junos_aggregate = attr.evolve(junos_static, protocol="Aggregate")
    assert (
        _compute_protocol_cost(
            junos_aggregate, attr.evolve(bf_static, protocol="aggregate")
        )
        == 0.0
    )
    # Aggregate and static doesn't
    assert _compute_protocol_cost(junos_aggregate, bf_static) == math.inf

    # BGP and bgp/ibgp
    junos_bgp = attr.evolve(junos_static, protocol="BGP")
    assert (
        _compute_protocol_cost(junos_bgp, attr.evolve(bf_static, protocol="bgp")) == 0.0
    )
    assert (
        _compute_protocol_cost(junos_bgp, attr.evolve(bf_static, protocol="ibgp"))
        == 0.0
    )
    # BGP and static doesn't
    assert _compute_protocol_cost(junos_bgp, bf_static) == math.inf

    # OSPF and ospf*
    junos_ospf = attr.evolve(junos_static, protocol="OSPF")
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospf"))
        == 0.0
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfIA"))
        == 0.0
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfIS"))
        == 0.0
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfE1"))
        == 0.0
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfE2"))
        == 0.0
    )
    # OSPF and static doesn't
    assert _compute_protocol_cost(junos_ospf, bf_static) == math.inf


def test_get_interface_runtime_date() -> None:
    interfaces = [
        JunosInterface(
            name="gr-0/0/0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=_to_bandwidth("800mbps"),
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Physical interface",
        ),
        JunosInterface(
            name="bme0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu=2000,
            interface_type="Physical interface",
        ),
        JunosInterface(
            name="bme0.0",
            state=JunosInterfaceState(admin=True, line=None),
            speed=None,
            bandwidth=_to_bandwidth("1000mbps"),
            mtu=1986,
            interface_type="Logical interface",
        ),
    ]
    assert JunosValidator.get_interface_runtime_data(interfaces) == {
        "gr-0/0/0": InterfaceRuntimeData(bandwidth=None, lineUp=True, speed=800000000),
        "bme0": InterfaceRuntimeData(bandwidth=None, lineUp=True, speed=None),
        "bme0.0": InterfaceRuntimeData(bandwidth=1000000000, lineUp=None, speed=None),
    }


def test_compare_all_bgp_routes_equal() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            origin_protocol="BGP",
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            metric=0,
            local_preference=100,
            as_path=(1, 2),
            origin_type="I",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1 2",
            origin_protocol="bgp",
            origin_type="igp",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {}


def test_compare_all_bgp_routes_mismatch_metric() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            origin_protocol="bgp",
            preference=170,
            metric=10,
            local_preference=100,
            as_path=(1, 2),
            origin_type="E",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1 2",
            origin_protocol="bgp",
            origin_type="egp",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): {"metric": "Batfish: 0, real: 10"}
    }


def test_compare_all_bgp_routes_mismatch_local_pref() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            origin_protocol="bgp",
            metric=0,
            local_preference=0,
            as_path=(1, 2),
            origin_type="I",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1 2",
            origin_protocol="bgp",
            origin_type="igp",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): {"local_preference": "Batfish: 100, real: 0"}
    }


def test_compare_all_bgp_routes_mismatch_local_as_path() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            metric=0,
            local_preference=100,
            origin_protocol="bgp",
            as_path=(1,),
            origin_type="I",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1 2",
            origin_protocol="bgp",
            origin_type="igp",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): {
            "as_path": "Batfish: {}, real: {}".format(
                bf_routes[0].as_path, expected_routes[0].as_path
            )
        }
    }


def test_compare_all_bgp_routes_mismatch_origin_protocol() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            metric=0,
            local_preference=100,
            origin_protocol="connected",
            as_path=(1,),
            origin_type="I",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1",
            origin_protocol="bgp",
            origin_type="igp",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): {
            "origin_protocol": "Batfish: {}, real: {}".format(
                bf_routes[0].origin_protocol, expected_routes[0].origin_protocol
            )
        }
    }


def test_compare_all_bgp_routes_mismatch_origin_type() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            metric=0,
            local_preference=100,
            origin_protocol="bgp",
            as_path=(1,),
            origin_type="I",
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1",
            origin_protocol="bgp",
            origin_type="incomplete",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): {
            "origin_type": "Batfish: incomplete, real: I"
        }
    }


def test_compare_all_bgp_routes_extra() -> None:
    expected_routes = []
    bf_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="1 2",
            origin_protocol="bgp",
            origin_type="type",
            tag=0,
        )
    ]
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): "Batfish has extra route: {}".format(
            {bf_routes[0]}
        )
    }


def test_compare_all_bgp_routes_missing() -> None:
    expected_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            next_hop_ip="2.2.2.2",
            next_hop_int="iface",
            preference=170,
            metric=0,
            origin_protocol="bgp",
            local_preference=100,
            as_path=(1,),
            origin_type="I",
        )
    ]
    bf_routes = []
    failures = JunosValidator("")._compare_all_bgp_routes(expected_routes, bf_routes)
    assert failures == {
        ("vrf", "1.1.1.0/24", "2.2.2.2"): "Batfish is missing route: {}".format(
            {expected_routes[0]}
        )
    }


def test_exclude_iface() -> None:
    # test iface with `16386` is being included
    iface_name = "em10"
    missing_in_batfish = {
        "bme0.0",
        "lsi",
        "bme0",
        "xe-0/0/1.16386",
        "dsc",
        "esi",
        "pime",
        "xe-0/0/3",
        "em5",
        "em6",
        "em7",
        "xe-0/0/11.16386",
        "vme",
        "pfe-0/0/0",
        "gr-0/0/0",
        "xe-0/0/11",
        "em4",
        "xe-0/0/5",
        "xe-0/0/4.16386",
        "lo0.16385",
        "xe-0/0/10.16386",
        "pfe-0/0/0.16383",
        "em2",
        "pimd",
        "pfh-0/0/0",
        "xe-0/0/6",
        "jsrv",
        "cbp0",
        "xe-0/0/7.16386",
        "em3",
        "xe-0/0/6.16386",
        "xe-0/0/9.16386",
        "pip0",
        "xe-0/0/10",
        "gre",
        "xe-0/0/9",
        "irb",
        "tap",
        "xe-0/0/1",
        "em4.32768",
        "vtep",
        "xe-0/0/8.16386",
        "pfh-0/0/0.16384",
        "xe-0/0/8",
        "xe-0/0/5.16386",
        "ipip",
        "xe-0/0/3.16386",
        "jsrv.1",
        "pfh-0/0/0.16383",
        "mtun",
        "xe-0/0/7",
        "em2.32768",
        "xe-0/0/2",
        "xe-0/0/2.16386",
        "xe-0/0/4",
    }
    result = JunosValidator("")._exclude_iface(iface_name, missing_in_batfish)
    assert result is True

    iface_name = "gr-0/0/0"
    missing_in_batfish = {
        "bme0.0",
        "lsi",
        "bme0",
        "xe-0/0/1.16386",
        "dsc",
        "esi",
        "pime",
        "xe-0/0/3",
        "em5",
        "em6",
        "em7",
        "xe-0/0/11.16386",
        "vme",
        "pfe-0/0/0",
        "gr-0/0/0",
        "xe-0/0/11",
        "em4",
        "xe-0/0/5",
        "xe-0/0/4.16386",
        "lo0.16385",
        "xe-0/0/10.16386",
        "pfe-0/0/0.16383",
        "em2",
        "pimd",
        "pfh-0/0/0",
        "xe-0/0/6",
        "jsrv",
        "cbp0",
        "xe-0/0/7.16386",
        "em3",
        "xe-0/0/6.16386",
        "xe-0/0/9.16386",
        "pip0",
        "xe-0/0/10",
        "gre",
        "xe-0/0/9",
        "irb",
        "tap",
        "xe-0/0/1",
        "em4.32768",
        "vtep",
        "xe-0/0/8.16386",
        "pfh-0/0/0.16384",
        "xe-0/0/8",
        "xe-0/0/5.16386",
        "ipip",
        "xe-0/0/3.16386",
        "jsrv.1",
        "pfh-0/0/0.16383",
        "mtun",
        "xe-0/0/7",
        "em2.32768",
        "xe-0/0/2",
        "xe-0/0/2.16386",
        "xe-0/0/4",
    }
    result = JunosValidator("")._exclude_iface(iface_name, missing_in_batfish)
    assert result is True

    iface_name = "xe-0/0/8.16386"
    missing_in_batfish = {
        "bme0.0",
        "lsi",
        "bme0",
        "xe-0/0/1.16386",
        "dsc",
        "esi",
        "pime",
        "xe-0/0/3",
        "em5",
        "em6",
        "em7",
        "xe-0/0/11.16386",
        "vme",
        "pfe-0/0/0",
        "gr-0/0/0",
        "xe-0/0/11",
        "em4",
        "xe-0/0/5",
        "xe-0/0/4.16386",
        "lo0.16385",
        "xe-0/0/10.16386",
        "pfe-0/0/0.16383",
        "em2",
        "pimd",
        "pfh-0/0/0",
        "xe-0/0/6",
        "jsrv",
        "cbp0",
        "xe-0/0/7.16386",
        "em3",
        "xe-0/0/6.16386",
        "xe-0/0/9.16386",
        "pip0",
        "xe-0/0/10",
        "gre",
        "xe-0/0/9",
        "irb",
        "tap",
        "xe-0/0/1",
        "em4.32768",
        "vtep",
        "xe-0/0/8.16386",
        "pfh-0/0/0.16384",
        "xe-0/0/8",
        "xe-0/0/5.16386",
        "ipip",
        "xe-0/0/3.16386",
        "jsrv.1",
        "pfh-0/0/0.16383",
        "mtun",
        "xe-0/0/7",
        "em2.32768",
        "xe-0/0/2",
        "xe-0/0/2.16386",
        "xe-0/0/4",
    }
    result = JunosValidator("")._exclude_iface(iface_name, missing_in_batfish)
    assert result is True

    iface_name = "xe-0/0/8.0"
    missing_in_batfish = {
        "bme0.0",
        "lsi",
        "bme0",
        "xe-0/0/1.16386",
        "dsc",
        "esi",
        "pime",
        "xe-0/0/3",
        "em5",
        "em6",
        "em7",
        "xe-0/0/11.16386",
        "vme",
        "pfe-0/0/0",
        "gr-0/0/0",
        "xe-0/0/11",
        "em4",
        "xe-0/0/5",
        "xe-0/0/4.16386",
        "lo0.16385",
        "xe-0/0/10.16386",
        "pfe-0/0/0.16383",
        "em2",
        "pimd",
        "pfh-0/0/0",
        "xe-0/0/6",
        "jsrv",
        "cbp0",
        "xe-0/0/7.16386",
        "em3",
        "xe-0/0/6.16386",
        "xe-0/0/9.16386",
        "pip0",
        "xe-0/0/10",
        "gre",
        "xe-0/0/9",
        "irb",
        "tap",
        "xe-0/0/1",
        "em4.32768",
        "vtep",
        "xe-0/0/8.16386",
        "pfh-0/0/0.16384",
        "xe-0/0/8",
        "xe-0/0/5.16386",
        "ipip",
        "xe-0/0/3.16386",
        "jsrv.1",
        "pfh-0/0/0.16383",
        "mtun",
        "xe-0/0/7",
        "em2.32768",
        "xe-0/0/2",
        "xe-0/0/2.16386",
        "xe-0/0/4",
    }
    result = JunosValidator("")._exclude_iface(iface_name, missing_in_batfish)
    assert result is False


def test_compare_interfaces_no_diff() -> None:
    real_iface = JunosInterface(
        name="xe-0/0/0.0",
        state=JunosInterfaceState(admin=True, line=True),
        speed=int(1e10),
        bandwidth=None,
        mtu=1514,
        interface_type="Logical interface",
    )
    bf_iface = InterfaceProperties(
        name="xe-0/0/0.0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e10),
        description=None,
        native_vlan=None,
        mtu=1514,
        speed=int(1e10),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    result = JunosValidator("")._compare_interfaces(real_iface, bf_iface)
    assert result == {}


def test_compare_interfaces_iface_state_mismatch() -> None:
    real_iface = JunosInterface(
        name="xe-0/0/0.0",
        state=JunosInterfaceState(admin=False, line=False),
        speed=int(1e10),
        bandwidth=None,
        mtu=1515,
        interface_type="Logical interface",
    )
    bf_iface = InterfaceProperties(
        name="xe-0/0/0.0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e10),
        description=None,
        native_vlan=None,
        mtu=1514,
        speed=int(1e10),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    result = JunosValidator("")._compare_interfaces(real_iface, bf_iface)
    assert result == {
        "active": "Batfish: True, JUNOS: admin=False line=False",
    }


def test_compare_interfaces_bw_mismatch() -> None:
    real_iface = JunosInterface(
        name="xe-0/0/0.0",
        state=JunosInterfaceState(admin=True, line=True),
        speed=int(1e1),
        bandwidth=None,
        mtu=1515,
        interface_type="Logical interface",
    )
    bf_iface = InterfaceProperties(
        name="xe-0/0/0.0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e10),
        description=None,
        native_vlan=None,
        mtu=1514,
        speed=int(1e10),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    result = JunosValidator("")._compare_interfaces(real_iface, bf_iface)
    assert result == {"bandwidth": "Batfish: 10000000000, JUNOS: 10"}


def test_compare_interfaces_skip_lo0_bw_check_only() -> None:
    # skip bw check for lo0
    real_iface = JunosInterface(
        name="lo0.0",
        state=JunosInterfaceState(admin=True, line=True),
        speed=None,
        bandwidth=None,
        mtu="Unlimited",
        interface_type="Logical interface",
    )
    bf_iface = InterfaceProperties(
        name="lo0.0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e12),
        description=None,
        native_vlan=None,
        mtu=1514,
        speed=int(1e12),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    result = JunosValidator("")._compare_interfaces(real_iface, bf_iface)
    assert result == {}

    # don't skip other checks for lo0
    real_iface = JunosInterface(
        name="lo0.0",
        state=JunosInterfaceState(admin=False, line=False),
        speed=None,
        bandwidth=None,
        mtu="Unlimited",
        interface_type="Logical interface",
    )
    bf_iface = InterfaceProperties(
        name="lo0.0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.2.3.4/24"],
        allowed_vlans=None,
        bandwidth=int(1e12),
        description=None,
        native_vlan=None,
        mtu=1514,
        speed=int(1e12),
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    result = JunosValidator("")._compare_interfaces(real_iface, bf_iface)
    assert result == {"active": "Batfish: True, JUNOS: admin=False line=False"}


def test_compare_routes_skip_inactive_route_bgprib() -> None:
    # Check inactive routes coming from real device is being skipped
    junos_bgp_routes = [
        JunosBgpRoute(
            vrf="vrf",
            network="192.168.123.2/32",
            is_active=True,
            origin_protocol="BGP",
            next_hop_ip="10.12.1.2",
            next_hop_int="xe-0/0/1.0",
            preference=170,
            metric=0,
            local_preference=100,
            as_path=(65001, 65002),
            origin_type="E",
        ),
        JunosBgpRoute(
            vrf="vrf",
            network="192.168.123.2/32",
            is_active=False,
            origin_protocol="BGP",
            next_hop_ip="10.12.2.2",
            next_hop_int="xe-0/0/2.0",
            preference=170,
            metric=0,
            local_preference=100,
            as_path=(65001, 65002),
            origin_type="E",
        ),
    ]
    bf_bgp_routes = [
        BgpRibRoute(
            weight=0,
            vrf="vrf",
            network="192.168.123.2/32",
            next_hop=NextHopInterface(interface="xe-0/0/1.0", ip="10.12.1.2"),
            next_hop_ip="10.12.1.2",
            next_hop_int="xe-0/0/1.0",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="65001 65002",
            origin_protocol="bgp",
            origin_type="egp",
            tag=0,
        )
    ]

    result = JunosValidator("")._compare_all_bgp_routes(junos_bgp_routes, bf_bgp_routes)
    assert result == {}


def test_compare_routes_batfish_inactive_route_bgprib() -> None:
    # Check that batfish have inactive route
    junos_bgp_routes = [
        JunosBgpRoute(
            vrf="default",
            network="192.168.123.2/32",
            is_active=False,
            origin_protocol="BGP",
            next_hop_ip="10.12.2.2",
            next_hop_int="xe-0/0/2.0",
            preference=170,
            metric=0,
            local_preference=100,
            as_path=(65001, 65002),
            origin_type="?",
        )
    ]
    bf_bgp_routes = [
        BgpRibRoute(
            weight=0,
            vrf="default",
            network="192.168.123.2/32",
            next_hop=NextHopInterface(interface="xe=0/0/2.0", ip="10.12.2.2"),
            next_hop_ip="10.12.2.2",
            next_hop_int="xe-0/0/2.0",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="65001 65002",
            origin_protocol="bgp",
            origin_type="incomplete",
            tag=0,
        )
    ]

    result = JunosValidator("")._compare_all_bgp_routes(junos_bgp_routes, bf_bgp_routes)
    assert result == {
        ("default", "192.168.123.2/32", "10.12.2.2"): {
            "Unexpected_inactive_route": f"Batfish: {bf_bgp_routes[0]}"
        },
    }


def test_filter_route() -> None:
    assert filter_route(
        JunosMainRibRoute(
            network="224.0.0.5/32",
            protocol="local",
            next_hop_ip=None,
            next_hop_int="iface",
            admin=0,
            metric=0,
            vrf="default",
            nh_type="MultiRecv",
            active=True,
        )
    )

    assert filter_route(
        JunosMainRibRoute(
            network="10.150.0.100/32",
            protocol="local",
            next_hop_ip=None,
            next_hop_int="em0.0",
            admin=0,
            metric=0,
            vrf="default",
            nh_type="local",
            active=True,
        )
    )

    assert filter_route(
        JunosMainRibRoute(
            network="1.1.1.1/32",
            protocol="BGP",
            next_hop_ip="1.1.1.2",
            next_hop_int="iface",
            admin=1,
            metric=2,
            vrf="vrf",
            nh_type=None,
            active=False,
        )
    )

    assert not (
        filter_route(
            JunosMainRibRoute(
                network="1.1.1.1/32",
                protocol="BGP",
                next_hop_ip="1.1.1.2",
                next_hop_int="iface",
                admin=1,
                metric=2,
                vrf="vrf",
                nh_type=None,
                active=True,
            )
        )
    )
