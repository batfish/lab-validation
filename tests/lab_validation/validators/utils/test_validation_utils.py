import math

import attr
from pybatfish.datamodel import NextHopInterface, NextHopIp

from lab_validation.parsers.ios.models.routes import IosIpRoute
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.IosValidator import IosValidator
from lab_validation.validators.utils.validation_utils import (
    match_pairs,
    matched_pairs_to_failures,
    preprocess_batfish_bgp_route,
)


def test_preprocess_batfish_bgp_route() -> None:
    r = BgpRibRoute(
        weight=0,
        vrf="vrf",
        network="10.10.0.0/16",
        next_hop=NextHopIp(ip="192.168.0.1"),
        next_hop_ip="192.168.0.1",
        next_hop_int="dynamic",
        protocol="bgp",
        as_path="65100",
        metric=100,
        local_preference=101,
        communities=["comm1"],
        origin_protocol="ospf",
        origin_type="type",
        tag=102,
    )
    # Should be no-op
    assert r == preprocess_batfish_bgp_route(r)

    r_nh_ip_auto_none = attr.evolve(r, next_hop_ip="AUTO/NONE(-1l)")
    r_nh_ip_none = attr.evolve(r, next_hop_ip=None)
    # Should convert Batfish AUTO/NONE string into a proper python None
    assert r_nh_ip_none == preprocess_batfish_bgp_route(r_nh_ip_auto_none)


def test_match_pairs_same_count() -> None:
    left = [
        IosIpRoute(
            network="1.1.1.0/24",
            protocol="bgp",
            next_hop_ip="3.4.5.6",
            next_hop_int="iface2",
            metric=0,
            admin=1,
            vrf="vrf",
        ),
        IosIpRoute(
            network="2.2.2.0/24",
            protocol="bgp",
            next_hop_ip="6.5.4.3",
            next_hop_int="iface1",
            metric=2,
            admin=3,
            vrf="vrf",
        ),
    ]

    right = [
        MainRibRoute(
            vrf="vrf",
            network="2.2.2.0/24",
            next_hop=NextHopInterface(interface="iface1", ip="6.5.4.3"),
            protocol="bgp",
            tag=None,
            metric=1,
            admin=1,
        ),
        MainRibRoute(
            vrf="vrf",
            network="3.3.3.0/24",
            next_hop=NextHopInterface(interface="iface2", ip="2.3.5.6"),
            protocol="static",
            tag=None,
            metric=4,
            admin=3,
        ),
    ]
    matched_pairs = match_pairs(left, right, IosValidator._diff_routes_cost)
    assert matched_pairs == [
        (left[0], None, math.inf),
        (left[1], right[0], 2),  # metric and admin
        (None, right[1], math.inf),
    ]


def test_match_pairs_more_in_left() -> None:
    left = [
        IosIpRoute(
            network="1.1.1.0/24",
            protocol="bgp",
            next_hop_ip="3.4.5.6",
            next_hop_int="iface2",
            metric=0,
            admin=1,
            vrf="vrf",
        ),
        IosIpRoute(
            network="1.1.1.0/24",
            protocol="bgp",
            next_hop_ip="6.5.4.3",
            next_hop_int="iface1",
            metric=1,
            admin=2,
            vrf="vrf",
        ),
    ]

    right = [
        MainRibRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopInterface(interface="iface1", ip="6.5.4.3"),
            protocol="bgp",
            tag=None,
            metric=0,
            admin=1,
        )
    ]
    matched_pairs = match_pairs(left, right, IosValidator._diff_routes_cost)

    assert matched_pairs == [
        (
            left[0],
            right[0],
            2.0,
        ),  # cost 2 (for next hop IP and interface)
        (left[1], None, math.inf),
    ]


def test_match_pairs_duplicate_route_in_different_vrf() -> None:
    left = [
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            metric=0,
            admin=20,
            vrf="d1_ce",
        ),
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            metric=0,
            admin=20,
            vrf="d2_ce",
        ),
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            metric=0,
            admin=20,
            vrf="d4_shared",
        ),
    ]

    right = [
        MainRibRoute(
            vrf="d4_shared",
            network="192.168.122.0/24",
            next_hop=NextHopIp(ip="10.34.31.2"),
            protocol="bgp",
            tag=None,
            metric=0,
            admin=20,
        ),
        MainRibRoute(
            vrf="d2_ce",
            network="192.168.122.0/24",
            next_hop=NextHopIp(ip="10.34.31.3"),
            protocol="bgp",
            tag=None,
            metric=0,
            admin=20,
        ),
        MainRibRoute(
            vrf="d1_ce",
            network="192.168.122.0/24",
            next_hop=NextHopIp(ip="10.34.31.3"),
            protocol="bgp",
            tag=None,
            metric=0,
            admin=20,
        ),
    ]

    matched_pairs = match_pairs(left, right, IosValidator._diff_routes_cost)
    assert matched_pairs == [
        (left[2], right[0], 0.0),
        (left[0], right[2], 1.0),
        (left[1], right[1], 1.0),
    ]


def test_matched_routes_to_failures() -> None:
    ios_route1 = IosIpRoute(
        network="2.2.2.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int="iface1",  # will be ignored
        admin=1,
        metric=0,
        vrf="vrf",
    )
    batfish_route1 = MainRibRoute(
        vrf="vrf",
        network="2.2.2.0/24",
        next_hop=NextHopIp(ip="1.2.3.4"),
        protocol="bgp",
        tag=None,
        metric=0,
        admin=1,
    )
    ios_route2 = IosIpRoute(
        network="1.1.1.0/24",
        protocol="bgp",
        next_hop_ip="1.2.3.4",
        next_hop_int="iface1",  # will be ignored
        admin=1,
        metric=0,
        vrf="vrf",
    )
    batfish_route2 = (
        MainRibRoute(
            vrf="vrf",
            network="2.2.2.0/24",
            next_hop=NextHopIp(ip="1.2.3.4"),
            protocol="connected",
            tag=None,
            metric=0,
            admin=1,
        ),
    )
    matched_routes: list[tuple[IosIpRoute, MainRibRoute, float]] = [
        (ios_route1, batfish_route1, 1.0),
        (ios_route2, None, math.inf),
        (
            None,
            batfish_route2,
            math.inf,
        ),
        (batfish_route1, batfish_route1, 0.0),
        (batfish_route2, batfish_route2, []),
    ]

    failures = matched_pairs_to_failures(matched_routes)
    assert failures == {
        f"Left_element: {ios_route1}": f"Right_element: {batfish_route1} (cost 1.0)",
        f"Left_element: {ios_route2}": "No_match_found_on_the_right",
        f"Right_element: {batfish_route2}": "No_match_found_on_the_left",
    }


def test_match_pairs_perfectly_match_right() -> None:
    left = [
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            metric=0,
            admin=20,
            vrf="vrf",
        ),
        IosIpRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop_ip="10.34.31.2",
            next_hop_int=None,
            metric=100,
            admin=20,
            vrf="vrf",
        ),
    ]

    right = [
        MainRibRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop=NextHopIp(ip="10.34.31.2"),
            metric=100,
            admin=20,
            vrf="vrf",
            tag=None,
        ),
        MainRibRoute(
            network="192.168.122.0/24",
            protocol="bgp",
            next_hop=NextHopIp(ip="10.34.31.2"),
            metric=1000,
            admin=20,
            vrf="vrf",
            tag=None,
        ),
    ]

    matched_pairs = match_pairs(left, right, IosValidator._diff_routes_cost)
    # right[0] should get its perfect match even though it is the best match for left[0]
    assert matched_pairs == [
        (left[1], right[0], 0.0),
        (left[0], right[1], 1.0),
    ]


if __name__ == "__main__":
    test_match_pairs_perfectly_match_right()
