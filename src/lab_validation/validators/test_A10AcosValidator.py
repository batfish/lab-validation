import math

import attr
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.a10.models.bgp import A10BgpRoute
from lab_validation.parsers.a10.models.routes import A10MainRibRoute

from .A10AcosValidator import _bf_kernel_route_tags, _bgp_rib_cost, _main_rib_cost
from .batfish_models.routes import BgpRibRoute, MainRibRoute


def test_bgp_rib_cost() -> None:
    a10_route: A10BgpRoute = A10BgpRoute(
        valid=True,
        best=True,
        network="0.0.0.0/0",
        next_hop_ip="10.139.1.133",
        metric=0,
        local_preference=None,
        weight=0,
        type=None,
        as_path=tuple([65333]),
        origin_type="i",
    )
    bf_route: BgpRibRoute = BgpRibRoute(
        vrf="default",
        network="00.0.0.0/0",
        next_hop=NextHopIp("10.139.1.133"),
        next_hop_ip="10.139.1.133",
        next_hop_int="dynamic",
        protocol="bgp",
        as_path=tuple([65333]),
        metric=0,
        local_preference=100,
        communities=[],
        origin_protocol="connected",
        origin_type="igp",
        weight=0,
        tag=None,
    )
    assert _bgp_rib_cost(a10_route, bf_route) == []

    # netwok does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, network="1.2.3.4/32"), bf_route) == [
        ("network", math.inf)
    ]

    # match for no next hop ip
    assert (
        _bgp_rib_cost(
            attr.evolve(a10_route, next_hop_ip="0.0.0.0"),
            attr.evolve(bf_route, next_hop=NextHopDiscard()),
        )
        == []
    )
    # next hop ip does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, next_hop_ip="1.2.3.4"), bf_route) == [
        ("next_hop_ip", 1)
    ]

    # metric does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, metric=5), bf_route) == [("metric", 1)]

    # explicit local preference match
    assert _bgp_rib_cost(attr.evolve(a10_route, local_preference=100), bf_route) == []
    # local preference does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, local_preference=1), bf_route) == [
        ("local_preference", 1)
    ]

    # weight does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, weight=15), bf_route) == [("weight", 1)]

    # as-path does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, as_path=tuple([])), bf_route) == [
        ("as_path", 1)
    ]

    # other origin type matches
    assert (
        _bgp_rib_cost(
            attr.evolve(a10_route, origin_type="e"),
            attr.evolve(bf_route, origin_type="egp"),
        )
        == []
    )
    assert (
        _bgp_rib_cost(
            attr.evolve(a10_route, origin_type="?"),
            attr.evolve(bf_route, origin_type="incomplete"),
        )
        == []
    )
    # origin type does not match
    assert _bgp_rib_cost(attr.evolve(a10_route, origin_type="e"), bf_route) == [
        ("origin_type", 1)
    ]


def test_main_rib_cost() -> None:
    a10_route: A10MainRibRoute = A10MainRibRoute(
        network="10.0.0.0/8",
        protocol="S",
        next_hop_ip="1.2.3.4",
        next_hop_int="VirtualEthernet55",
        admin=1,
        metric=0,
    )
    bf_route: MainRibRoute = MainRibRoute(
        network="10.0.0.0/8",
        vrf="default",
        protocol="static",
        next_hop=NextHopIp(ip="1.2.3.4"),
        admin=1,
        metric=0,
        tag=None,
    )
    assert _main_rib_cost(a10_route, bf_route) == []
    assert _main_rib_cost(attr.evolve(a10_route, network="1.2.3.4/32"), bf_route) == [
        ("network", math.inf)
    ]
    assert _main_rib_cost(attr.evolve(a10_route, protocol="C"), bf_route) == [
        ("protocol", math.inf)
    ]
    assert _main_rib_cost(
        attr.evolve(a10_route, next_hop_ip="1.2.3.5", admin=2, metric=1), bf_route
    ) == [("nhip", 1.0), ("admin", 1.0), ("metric", 1.0)]

    a10_connected = attr.evolve(a10_route, protocol="C", admin=0)
    bf_connected = attr.evolve(
        bf_route,
        protocol="connected",
        next_hop=NextHopInterface(interface="VirtualEthernet55"),
        admin=0,
    )
    assert _main_rib_cost(a10_connected, bf_connected) == []
    assert _main_rib_cost(
        attr.evolve(a10_connected, next_hop_int="VirtualEthernet53"), bf_connected
    ) == [("nhint", math.inf)]


def test_main_rib_cost_acos() -> None:
    a10_route: A10MainRibRoute = A10MainRibRoute(
        network="10.0.0.0/8",
        protocol="N",
        next_hop_ip=None,
        next_hop_int=None,
        admin=0,
        metric=0,
    )
    bf_route: MainRibRoute = MainRibRoute(
        network="10.0.0.0/8",
        vrf="default",
        protocol="kernel",
        next_hop=NextHopDiscard(),
        admin=0,
        metric=0,
        tag=_bf_kernel_route_tags["N"],
    )
    assert _main_rib_cost(a10_route, bf_route) == []

    # wrong tag, so different protocol
    assert _main_rib_cost(
        a10_route, attr.evolve(bf_route, tag=_bf_kernel_route_tags["V"])
    ) == [("protocol", math.inf)]
    # test all acos routes against correct bf_route tags
    assert (
        _main_rib_cost(
            attr.evolve(a10_route, protocol="V"),
            attr.evolve(bf_route, tag=_bf_kernel_route_tags["V"]),
        )
        == []
    )
    assert (
        _main_rib_cost(
            attr.evolve(a10_route, protocol="VF"),
            attr.evolve(bf_route, tag=_bf_kernel_route_tags["VF"]),
        )
        == []
    )
    assert (
        _main_rib_cost(
            attr.evolve(a10_route, protocol="F"),
            attr.evolve(bf_route, tag=_bf_kernel_route_tags["F"]),
        )
        == []
    )
