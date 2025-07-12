from pybatfish.datamodel import NextHopInterface

from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
    convert_as_path,
)


def test_main_rib_route1() -> None:
    MainRibRoute(
        vrf="vrf",
        network="1.2.3.4/24",
        next_hop=NextHopInterface(interface="peer", ip="1.2.3.5"),
        protocol="connected",
        tag=0,
        metric=1,
        admin=1,
    )


def test_main_rib_route2() -> None:
    MainRibRoute(
        vrf="vrf",
        network="1.2.3.4/24",
        next_hop=NextHopInterface(interface="peer", ip="1.2.3.5"),
        protocol="connected",
        tag=None,
        metric=1,
        admin=1,
    )


def test_main_rib_route3() -> None:
    MainRibRoute(
        vrf="vrf",
        network="1.2.3.4/24",
        next_hop=NextHopInterface(interface="peer", ip="1.2.3.5"),
        protocol="connected",
        tag=0,
        metric=1,
        admin=1,
    )


def test_bgp_rib() -> None:
    BgpRibRoute(
        weight=0,
        vrf="vrf",
        network="1.2.3.4/24",
        next_hop=NextHopInterface(interface="peer", ip="1.2.3.5"),
        next_hop_ip="1.2.3.5",
        next_hop_int="peer",
        protocol="connected",
        tag=0,
        metric=1,
        as_path="1 2",
        local_preference=10,
        communities=["1:2"],
        origin_protocol="protocol",
        origin_type="type",
    )


def test_evpn_rib() -> None:
    EvpnRibRoute(
        vrf="vrf",
        network="1.2.3.4/24",
        next_hop=NextHopInterface(interface="peer", ip="1.2.3.5"),
        next_hop_ip="1.2.3.5",
        next_hop_int="peer",
        protocol="connected",
        tag=0,
        metric=1,
        as_path="1 2",
        local_preference=10,
        communities=["1:2"],
        origin_protocol="protocol",
        origin_type="type",
        route_distinguisher="distinguisher",
    )


def test_convert_as_path() -> None:
    assert convert_as_path("1 2 3") == (1, 2, 3)
    assert convert_as_path("(1 2 3)") == ((1, 2, 3),)
    assert convert_as_path("(1 2) 3") == ((1, 2), 3)
    assert convert_as_path("1 (2 3)") == (1, (2, 3))
    assert convert_as_path("1 (2) 3") == (1, (2,), 3)
    assert convert_as_path("(1 2) (3)") == ((1, 2), (3,))
    assert convert_as_path((1, 2)) == (1, 2)
    assert convert_as_path(((1, 2),)) == ((1, 2),)
    # Probably wouldn't show up in real data, but testing because we're not certain
    assert convert_as_path(" 1 ") == (1,)
    assert convert_as_path("( 1 )") == ((1,),)
    assert convert_as_path("1 ( 2 ) 3") == (1, (2,), 3)
