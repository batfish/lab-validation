import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.junos.commands.interfaces import _to_bandwidth
from lab_validation.parsers.junos.models.interfaces import (
    JunosInterface,
    JunosInterfaceState,
)
from lab_validation.parsers.junos.models.routes import (
    JunosBgpRoute,
    JunosEvpnRoute,
    JunosMainRibRoute,
)
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
)
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
    assert _routes_cost(junos_route, batfish_route) == []

    # Wrong vrf -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, vrf="vrf2")) == [
        ("vrf", math.inf)
    ]

    # Wrong network -> routes are incompatible
    assert _routes_cost(
        junos_route, attr.evolve(batfish_route, network="1.1.1.1/30")
    ) == [("network", math.inf)]

    # Wrong protocol -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, protocol="ospf")) == [
        ("protocol", math.inf)
    ]

    # Wrong metric -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, metric=5)) == [
        ("metric", 1.0)
    ]

    # Wrong admin -> routes are incompatible
    assert _routes_cost(junos_route, attr.evolve(batfish_route, admin=5)) == [
        ("admin", 1.0)
    ]


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
    # Batfish NHIP routes are compatible with Junos routes that have a resolved NHINT
    assert _compute_nexthop_cost(junos_route, NextHopIp(ip="10.12.1.1")) == []
    # Since Batfish shows protocol NHOP while Junos shows resolved, cannot enforce
    # that they appear equal
    assert _compute_nexthop_cost(junos_route, NextHopIp(ip="10.12.1.2")) == []

    # Also compatible if it's a Batfish NHINT + NHIP route.
    assert (
        _compute_nexthop_cost(
            junos_route, NextHopInterface(interface="xe-0/0/1.0", ip="10.12.1.1")
        )
        == []
    )
    # Incompatible if either NHIP or NHINT is wrong
    assert _compute_nexthop_cost(
        junos_route, NextHopInterface(interface="xe-0/0/1.1", ip="10.12.1.1")
    ) == [("next_hop_int", 5.0)]
    assert _compute_nexthop_cost(
        junos_route, NextHopInterface(interface="xe-0/0/1.0", ip="10.12.1.2")
    ) == [("next_hop_ip", 1.0)]


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
        == []
    )

    # next-hop interface does not match
    assert _compute_nexthop_cost(
        junos_route, NextHopInterface(interface="xe-0/0/1.1", ip="2.2.2.2")
    ) == [("next_hop_int", 5.0)]


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
    assert _compute_nexthop_cost(junos_route, NextHopDiscard()) == []
    # Not a null route -> incompatible
    assert _compute_nexthop_cost(
        junos_route, NextHopInterface(interface="xe-0/1/0.0")
    ) == [("next_hop", 10.0)]


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
    assert _compute_nexthop_cost(junos_route, NextHopDiscard()) == []
    # Not a null route -> incompatible
    assert _compute_nexthop_cost(
        junos_route, NextHopInterface(interface="xe-0/1/0.0")
    ) == [("next_hop", 10.0)]


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
    assert _compute_protocol_cost(junos_static, bf_static) == []
    # Static and not static doesn't
    assert _compute_protocol_cost(
        junos_static, attr.evolve(bf_static, protocol="ospf")
    ) == [("protocol", math.inf)]

    # Direct and connected work
    junos_direct = attr.evolve(junos_static, protocol="Direct")
    assert (
        _compute_protocol_cost(
            junos_direct, attr.evolve(bf_static, protocol="connected")
        )
        == []
    )
    # Direct and static doesn't
    assert _compute_protocol_cost(junos_direct, bf_static) == [("protocol", math.inf)]

    # Local and Local work
    junos_local = attr.evolve(junos_static, protocol="Local")
    assert (
        _compute_protocol_cost(junos_local, attr.evolve(bf_static, protocol="local"))
        == []
    )
    # Local and static doesn't
    assert _compute_protocol_cost(junos_local, bf_static) == [("protocol", math.inf)]

    # Aggregate and aggregate work
    junos_aggregate = attr.evolve(junos_static, protocol="Aggregate")
    assert (
        _compute_protocol_cost(
            junos_aggregate, attr.evolve(bf_static, protocol="aggregate")
        )
        == []
    )
    # Aggregate and static doesn't
    assert _compute_protocol_cost(junos_aggregate, bf_static) == [
        ("protocol", math.inf)
    ]

    # BGP and bgp/ibgp
    junos_bgp = attr.evolve(junos_static, protocol="BGP")
    assert (
        _compute_protocol_cost(junos_bgp, attr.evolve(bf_static, protocol="bgp")) == []
    )
    assert (
        _compute_protocol_cost(junos_bgp, attr.evolve(bf_static, protocol="ibgp")) == []
    )
    # BGP and static doesn't
    assert _compute_protocol_cost(junos_bgp, bf_static) == [("protocol", math.inf)]

    # OSPF and ospf*
    junos_ospf = attr.evolve(junos_static, protocol="OSPF")
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospf"))
        == []
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfIA"))
        == []
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfIS"))
        == []
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfE1"))
        == []
    )
    assert (
        _compute_protocol_cost(junos_ospf, attr.evolve(bf_static, protocol="ospfE2"))
        == []
    )
    # OSPF and static doesn't
    assert _compute_protocol_cost(junos_ospf, bf_static) == [("protocol", math.inf)]


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
    assert len(failures) == 1
    value = next(iter(failures.values()))
    assert "'metric'" in value


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
    assert len(failures) == 1
    value = next(iter(failures.values()))
    assert "'local_preference'" in value


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
    assert len(failures) == 1
    value = next(iter(failures.values()))
    assert "'as_path'" in value


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
    assert len(failures) == 1
    value = next(iter(failures.values()))
    assert "'origin_protocol'" in value


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
    assert len(failures) == 1
    value = next(iter(failures.values()))
    assert "'origin_type'" in value


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
    assert len(failures) == 1
    assert "No_match_found_on_the_left" in next(iter(failures.values()))


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
    assert len(failures) == 1
    assert "No_match_found_on_the_right" in next(iter(failures.values()))


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
    # Batfish reports BGP-best even when the route is inactive in the main
    # RIB, so matching routes (even when device-side inactive) do not flag.
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
    assert result == {}


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

    # /31 to em0.0 is dropped since Batfish deactivates the interface
    assert filter_route(
        JunosMainRibRoute(
            network="10.150.0.100/31",
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

    # All em0 routes are now filtered (Batfish deactivates mgmt interfaces)
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


def test_filter_route_multipath() -> None:
    """Multipath ECMP resolution entries should be filtered."""
    assert filter_route(
        JunosMainRibRoute(
            network="10.99.0.0/31",
            protocol="Multipath",
            next_hop_ip="172.16.254.1",
            next_hop_int="ge-0/0/1.0",
            admin=255,
            metric=0,
            vrf="TENANT-A",
            nh_type=None,
            active=True,
        )
    )


def test_filter_route_fxp0() -> None:
    """fxp0 management interface routes should be filtered, like em0."""
    assert filter_route(
        JunosMainRibRoute(
            network="10.0.0.15/32",
            protocol="Local",
            next_hop_ip=None,
            next_hop_int="fxp0.0",
            admin=0,
            metric=None,
            vrf="default",
            nh_type=None,
            active=True,
        )
    )
    assert filter_route(
        JunosMainRibRoute(
            network="10.0.0.0/24",
            protocol="Direct",
            next_hop_ip=None,
            next_hop_int="fxp0.0",
            admin=0,
            metric=None,
            vrf="default",
            nh_type=None,
            active=True,
        )
    )


def test_filter_route_mgmt_junos_vrf() -> None:
    """Routes in mgmt_junos VRF should be filtered."""
    assert filter_route(
        JunosMainRibRoute(
            network="0.0.0.0/0",
            protocol="Static",
            next_hop_ip="10.0.0.2",
            next_hop_int=None,
            admin=5,
            metric=None,
            vrf="mgmt_junos",
            nh_type=None,
            active=True,
        )
    )


def test_exclude_iface_fxp() -> None:
    """fxp management interfaces should be excluded."""
    assert JunosValidator._exclude_iface("fxp0", set())
    assert JunosValidator._exclude_iface("fxp0.0", set())


def test_compare_interfaces_mgmt_fxp() -> None:
    """fxp management interfaces should skip active and bandwidth checks."""
    real = JunosInterface(
        name="fxp0",
        state=JunosInterfaceState(admin=True, line=True),
        speed=None,
        bandwidth=10000000000,
        mtu=1514,
        interface_type="Physical interface",
    )
    batfish = InterfaceProperties(
        name="fxp0",
        active=False,
        all_prefixes=["10.254.4.1/16"],
        allowed_vlans=None,
        bandwidth=1000000000000.0,
        description=None,
        mtu=1514,
        speed=1000000000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    diff = JunosValidator._compare_interfaces(real, batfish)
    assert diff == {}


def test_compare_interfaces_irb_vni_backed_skips_active() -> None:
    """IRB with VNI backing: skip active mismatch (pre-dataplane)."""
    real = JunosInterface(
        name="irb.200",
        state=JunosInterfaceState(admin=True, line=True),
        speed=None,
        bandwidth=None,
        mtu=1514,
        interface_type="Logical interface",
    )
    batfish = InterfaceProperties(
        name="irb.200",
        active=False,
        all_prefixes=["172.16.200.1/24"],
        allowed_vlans=None,
        bandwidth=0,
        description=None,
        mtu=1514,
        speed=0,
        switchport=False,
        switchport_mode=None,
        vrf="TENANT-A",
    )
    diff = JunosValidator._compare_interfaces(real, batfish, vni_ifaces={"irb.200"})
    assert "active" not in diff


def test_compare_interfaces_irb_no_vni_reports_active() -> None:
    """IRB without VNI backing: report active mismatch."""
    real = JunosInterface(
        name="irb.200",
        state=JunosInterfaceState(admin=True, line=True),
        speed=None,
        bandwidth=None,
        mtu=1514,
        interface_type="Logical interface",
    )
    batfish = InterfaceProperties(
        name="irb.200",
        active=False,
        all_prefixes=["172.16.200.1/24"],
        allowed_vlans=None,
        bandwidth=0,
        description=None,
        mtu=1514,
        speed=0,
        switchport=False,
        switchport_mode=None,
        vrf="TENANT-A",
    )
    diff = JunosValidator._compare_interfaces(real, batfish, vni_ifaces=set())
    assert "active" in diff


def test_compare_interfaces_irb_vni_backed_both_active_no_skip() -> None:
    """IRB with VNI backing but both agree active: no special handling needed."""
    real = JunosInterface(
        name="irb.200",
        state=JunosInterfaceState(admin=True, line=True),
        speed=None,
        bandwidth=None,
        mtu=1514,
        interface_type="Logical interface",
    )
    batfish = InterfaceProperties(
        name="irb.200",
        active=True,
        all_prefixes=["172.16.200.1/24"],
        allowed_vlans=None,
        bandwidth=0,
        description=None,
        mtu=1514,
        speed=0,
        switchport=False,
        switchport_mode=None,
        vrf="TENANT-A",
    )
    diff = JunosValidator._compare_interfaces(real, batfish, vni_ifaces={"irb.200"})
    assert "active" not in diff


def test_is_local_discard_host_route() -> None:
    """Local /32 discard routes should be filtered (deactivated interfaces)."""
    from lab_validation.validators.JunosValidator import _is_local_discard_host_route

    # Should filter: local /32 discard
    assert _is_local_discard_host_route(
        MainRibRoute(
            vrf="default",
            network="10.254.4.1/32",
            next_hop=NextHopDiscard(),
            protocol="local",
            metric=0,
            admin=0,
            tag=None,
        )
    )

    # Should NOT filter: not /32
    assert not _is_local_discard_host_route(
        MainRibRoute(
            vrf="default",
            network="10.254.4.0/24",
            next_hop=NextHopDiscard(),
            protocol="local",
            metric=0,
            admin=0,
            tag=None,
        )
    )

    # Should NOT filter: not local protocol
    assert not _is_local_discard_host_route(
        MainRibRoute(
            vrf="default",
            network="10.254.4.1/32",
            next_hop=NextHopDiscard(),
            protocol="static",
            metric=0,
            admin=5,
            tag=None,
        )
    )

    # Should NOT filter: not NextHopDiscard
    assert not _is_local_discard_host_route(
        MainRibRoute(
            vrf="default",
            network="10.254.4.1/32",
            next_hop=NextHopInterface(interface="fxp0.0"),
            protocol="local",
            metric=0,
            admin=0,
            tag=None,
        )
    )


def _make_real_evpn_route(**kwargs: object) -> JunosEvpnRoute:
    """Helper: builds a JunosEvpnRoute with sensible defaults from the
    junos_evpn_type5 lab (node1-1 bgp.evpn.0 table).
    """
    defaults = dict(
        network="192.168.99.0/24",
        route_distinguisher="172.16.0.100:10000",
        vrf="default",
        protocol="BGP",
        next_hop_ip="172.16.254.1",
        next_hop_int="ge-0/0/1.0",
        active=True,
        admin=170,
        local_preference=100,
        as_path=(65100, 65200),
        origin_type="I",
    )
    defaults.update(kwargs)
    return JunosEvpnRoute(**defaults)


def _make_bf_evpn_route(**kwargs: object) -> EvpnRibRoute:
    """Helper: builds an EvpnRibRoute with sensible defaults matching
    the real route above.
    """
    defaults = dict(
        vrf="default",
        network="192.168.99.0/24",
        route_distinguisher="172.16.0.100:10000",
        next_hop=NextHopIp(ip="172.16.0.100"),
        next_hop_ip="172.16.0.100",
        next_hop_int="dynamic",
        protocol="bgp",
        as_path="65100 65200",
        metric=0,
        local_preference=100,
        communities=(),
        origin_protocol="bgp",
        origin_type="igp",
        tag=0,
    )
    defaults.update(kwargs)
    return EvpnRibRoute(**defaults)


def test_compare_evpn_routes_matching() -> None:
    """Matching routes with correct origin type mapping produce no failures."""
    real = [_make_real_evpn_route()]
    bf = [_make_bf_evpn_route()]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_origin_igp() -> None:
    """Device 'I' maps to Batfish 'igp'."""
    real = [_make_real_evpn_route(origin_type="I")]
    bf = [_make_bf_evpn_route(origin_type="igp")]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_origin_egp() -> None:
    """Device 'E' maps to Batfish 'egp'."""
    real = [_make_real_evpn_route(origin_type="E")]
    bf = [_make_bf_evpn_route(origin_type="egp")]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_origin_incomplete() -> None:
    """Device '?' maps to Batfish 'incomplete'."""
    real = [_make_real_evpn_route(origin_type="?")]
    bf = [_make_bf_evpn_route(origin_type="incomplete")]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_origin_mismatch() -> None:
    """Mismatched origin type produces a failure."""
    real = [_make_real_evpn_route(origin_type="I")]
    bf = [_make_bf_evpn_route(origin_type="egp")]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    assert ("172.16.0.100:10000", "192.168.99.0/24") in failures
    assert "origin_type" in failures[("172.16.0.100:10000", "192.168.99.0/24")]


def test_compare_evpn_routes_as_path_match() -> None:
    """Matching AS paths produce no failures."""
    real = [_make_real_evpn_route(as_path=(65100, 65200))]
    bf = [_make_bf_evpn_route(as_path="65100 65200")]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_as_path_mismatch() -> None:
    """Mismatched AS paths produce a failure."""
    real = [_make_real_evpn_route(as_path=(65100, 65200))]
    bf = [_make_bf_evpn_route(as_path="65100 65300")]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    key = ("172.16.0.100:10000", "192.168.99.0/24")
    assert key in failures
    assert "as_path" in failures[key]


def test_compare_evpn_routes_as_path_empty() -> None:
    """Empty AS paths on both sides produce no failures."""
    real = [_make_real_evpn_route(as_path=())]
    bf = [_make_bf_evpn_route(as_path="")]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_local_preference_match() -> None:
    """Matching local preference produces no failures."""
    real = [_make_real_evpn_route(local_preference=100)]
    bf = [_make_bf_evpn_route(local_preference=100)]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_local_preference_mismatch() -> None:
    """Mismatched local preference produces a failure."""
    real = [_make_real_evpn_route(local_preference=200)]
    bf = [_make_bf_evpn_route(local_preference=100)]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    key = ("172.16.0.100:10000", "192.168.99.0/24")
    assert key in failures
    assert "local_preference" in failures[key]


def test_compare_evpn_routes_local_preference_none_skipped() -> None:
    """When device has no local_preference (e.g., route reflector), skip the check."""
    real = [_make_real_evpn_route(local_preference=None)]
    bf = [_make_bf_evpn_route(local_preference=100)]
    assert JunosValidator._compare_evpn_routes(real, bf) == {}


def test_compare_evpn_routes_missing_in_batfish() -> None:
    """Device has a route that Batfish does not."""
    real = [_make_real_evpn_route()]
    bf: list[EvpnRibRoute] = []
    failures = JunosValidator._compare_evpn_routes(real, bf)
    key = ("172.16.0.100:10000", "192.168.99.0/24")
    assert key in failures
    assert "missing" in failures[key].lower()


def test_compare_evpn_routes_extra_in_batfish() -> None:
    """Batfish has a route that the device does not."""
    real: list[JunosEvpnRoute] = []
    bf = [_make_bf_evpn_route()]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    key = ("172.16.0.100:10000", "192.168.99.0/24")
    assert key in failures
    assert "extra" in failures[key].lower()


def test_compare_evpn_routes_multiple() -> None:
    """Multiple routes: one matching, one extra in Batfish."""
    real = [_make_real_evpn_route()]
    bf = [
        _make_bf_evpn_route(),
        _make_bf_evpn_route(network="10.99.0.0/31"),
    ]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    assert ("172.16.0.100:10000", "192.168.99.0/24") not in failures
    assert ("172.16.0.100:10000", "10.99.0.0/31") in failures


def test_compare_evpn_routes_different_rd() -> None:
    """Same network from different RDs are distinct routes."""
    real = [_make_real_evpn_route(route_distinguisher="10.0.0.1:100")]
    bf = [_make_bf_evpn_route(route_distinguisher="10.0.0.2:100")]
    failures = JunosValidator._compare_evpn_routes(real, bf)
    assert ("10.0.0.1:100", "192.168.99.0/24") in failures
    assert ("10.0.0.2:100", "192.168.99.0/24") in failures


def test_validate_evpn_rib_routes_empty_batfish() -> None:
    """No Batfish EVPN routes -> skip validation (empty result)."""
    result = JunosValidator("")._compare_evpn_routes([], [])
    assert result == {}


def test_validate_evpn_rib_routes_no_batfish_routes() -> None:
    """validate_evpn_rib_routes returns {} when batfish_routes is empty."""
    result = JunosValidator("").validate_evpn_rib_routes([])
    assert result == {}
