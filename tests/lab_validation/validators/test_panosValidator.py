import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.panos.models.routes import PanosMainRibRoute
from lab_validation.validators.batfish_models.routes import MainRibRoute
from lab_validation.validators.PanosValidator import PanosValidator


def test_diff_routes_cost_nhint_ignore() -> None:
    expected_route = PanosMainRibRoute(
        virtual_router="vrf",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        metric=0,
        flags={"B"},
        age=None,
        next_hop_int="iface1",  # will be ignored
        next_AS=None,
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
    assert PanosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_diff_routes_cost_skip_ibgp_comparision() -> None:
    """
    Test skipping when real_data protocol is generic bgp & batfish protocol is `ibgp`
    """
    expected_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        metric=0,
        flags={"B"},
        age=None,
        next_hop_int=None,
        next_AS=None,
    )
    batfish_route = MainRibRoute(
        vrf="default",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="ibgp",
        tag=None,
        metric=0,
        admin=1,
    )
    assert PanosValidator._diff_routes_cost(expected_route, batfish_route) == 0


def test_diff_routes_cost_route_in_multiple_vrf() -> None:
    """
    Test that route in different vrf return math.inf
    """
    expected_route = PanosMainRibRoute(
        virtual_router="vrf1",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        metric=0,
        flags={"B"},
        age=None,
        next_hop_int=None,
        next_AS=None,
    )
    batfish_route = MainRibRoute(
        vrf="vrf2",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="bgp",
        tag=None,
        metric=0,
        admin=1,
    )
    assert PanosValidator._diff_routes_cost(expected_route, batfish_route) == math.inf


def test_compute_protocol_cost() -> None:
    result = PanosValidator.compute_protocol_cost("bgp", "ibgp")
    assert result == 0.0

    result = PanosValidator.compute_protocol_cost("bgp", "ospf")
    assert result == math.inf


def test_compute_nexthop_cost_local() -> None:
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.2/32",
        next_hop_ip="0.0.0.0",
        next_hop_int=None,
        metric=0,
        flags={"A", "H"},
        age=None,
        next_AS=None,
    )
    # compatible_nh: local
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopInterface(interface="ethernet1/1")
    )
    assert result == 0.0


def test_compute_nexthop_cost_connected() -> None:
    # compatible_nh: connected
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        next_hop_int="ethernet1/1",
        metric=0,
        flags={"A", "C"},
        age=None,
        next_AS=None,
    )
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopInterface(interface="ethernet1/1")
    )
    assert result == 0.0

    # not compatible_nh: connected
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopInterface(interface="ethernet1/2")
    )
    assert result == 1.0


def test_compute_nexthop_cost_static_null() -> None:
    # compatible_nh: static null
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="discard",
        next_hop_int=None,
        metric=0,
        flags={"A", "S"},
        age=None,
        next_AS=None,
    )
    result = PanosValidator.compute_nexthop_cost(real_route, NextHopDiscard())
    assert result == 0.0

    # not compatible_nh: static null
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopInterface(interface="ethernet2/2", ip="11.22.33.44")
    )
    assert result == 10.0


def test_compute_nexthop_cost_static() -> None:
    # compatible_nh: static
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        next_hop_int="ethernet1/1",
        metric=0,
        flags={"A", "S"},
        age=None,
        next_AS=None,
    )
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopInterface(interface="ethernet1/1", ip="1.2.3.4")
    )
    assert result == 0.0

    # compatible_nh: static route using next_hop ip
    result = PanosValidator.compute_nexthop_cost(
        real_route,
        NextHopIp(ip="1.2.3.4"),
    )
    assert result == 0.0

    # not compatible_nh: static
    result = PanosValidator.compute_nexthop_cost(
        real_route,
        NextHopInterface(interface="ethernet2/2", ip="11.22.33.44"),
    )
    assert result == 2.0


def test_compute_nexthop_cost_bgp() -> None:
    # compatible_nh: bgp
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        next_hop_int=None,
        metric=0,
        flags={"A", "B"},
        age=None,
        next_AS=None,
    )
    result = PanosValidator.compute_nexthop_cost(real_route, NextHopIp(ip="1.2.3.4"))
    assert result == 0.0

    # not compatible_nh: bgp
    result = PanosValidator.compute_nexthop_cost(
        real_route, NextHopIp(ip="11.22.33.44")
    )
    assert result == 1.0


def test_diff_routes_cost_metric_none() -> None:
    # test metric real = none & batfish = 0
    real_route = PanosMainRibRoute(
        virtual_router="default",
        network="2.2.2.0/24",
        next_hop_ip="1.2.3.4",
        next_hop_int=None,
        metric=None,
        flags={"A", "?", "B"},
        age=None,
        next_AS=None,
    )
    bf_route = MainRibRoute(
        vrf="default",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="bgp",
        tag=None,
        metric=0,
        admin=20,
    )
    assert PanosValidator._diff_routes_cost(real_route, bf_route) == 0.0

    # test metric real = none & batfish = 10
    assert (
        PanosValidator._diff_routes_cost(real_route, attr.evolve(bf_route, metric=10))
        == 1.0
    )
