from lab_validation.parsers.panos.commands.routes import parse_show_routing_route
from lab_validation.parsers.panos.models.routes import PanosMainRibRoute


def test_show_routing_route() -> None:
    """Based on a real config, with the real crap they left in it."""
    text = """=~=~=~=~=~=~=~=~=~=~=~= PuTTY log 2020.12.24 09:49:15 =~=~=~=~=~=~=~=~=~=~=~=
show routing route

flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf, B:bgp,
       Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2, E:ecmp, M:multicast


VIRTUAL ROUTER: My virtual router (id 2)
  ==========
destination nexthop metric flags age interface next-AS
10.178.143.0/24 10.102.3.7 10 A B 1348860 ae1.100 65256
10.102.142.181/32 10.102.3.24 A B E 621200 ethernet1/22.500 64920
10.102.142.176/32 10.102.3.51 0 A B 1581935 ethernet1/21.500 64920
10.102.139.180/26 10.102.3.45 0 A B E 621193 ethernet1/21.300 64920
10.102.7.118/32 0.0.0.0 1 A ~
10.102.3.68/32 10.102.3.13 0 A B 1351481 ae1.200 65256
10.102.3.38/30 10.102.3.39 0 B 1581935 ethernet1/21.100 64920
10.102.3.38/30 10.102.3.37 0 A C ethernet1/21.100
10.102.3.37/32 0.0.0.0 0 A H
10.102.3.35/30 10.102.3.34 0 B 1581935 ethernet1/21.200 64920
10.102.3.35/30 10.102.3.33 0 A C ethernet1/21.200
10.102.3.33/32 0.0.0.0 0 A H
10.102.72.143/24 10.102.3.7 10000 A B 1350407 ae1.100 65256
total routes shown: 13"""
    routes = parse_show_routing_route(text)
    assert routes == [
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.178.143.0/24",
            next_hop_ip="10.102.3.7",
            metric=10,
            flags={"A", "B"},
            age=1348860,
            next_hop_int="ae1.100",
            next_AS=65256,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.142.181/32",
            next_hop_ip="10.102.3.24",
            metric=None,
            flags={"A", "B", "E"},
            age=621200,
            next_hop_int="ethernet1/22.500",
            next_AS=64920,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.142.176/32",
            next_hop_ip="10.102.3.51",
            metric=0,
            flags={"A", "B"},
            age=1581935,
            next_hop_int="ethernet1/21.500",
            next_AS=64920,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.139.180/26",
            next_hop_ip="10.102.3.45",
            metric=0,
            flags={"A", "B", "E"},
            age=621193,
            next_hop_int="ethernet1/21.300",
            next_AS=64920,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.7.118/32",
            next_hop_ip="0.0.0.0",
            metric=1,
            flags={"A", "~"},
            age=None,
            next_hop_int=None,
            next_AS=None,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.68/32",
            next_hop_ip="10.102.3.13",
            metric=0,
            flags={"A", "B"},
            age=1351481,
            next_hop_int="ae1.200",
            next_AS=65256,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.38/30",
            next_hop_ip="10.102.3.39",
            metric=0,
            flags={"B"},
            age=1581935,
            next_hop_int="ethernet1/21.100",
            next_AS=64920,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.38/30",
            next_hop_ip="10.102.3.37",
            metric=0,
            flags={"A", "C"},
            age=None,
            next_hop_int="ethernet1/21.100",
            next_AS=None,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.37/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            flags={"A", "H"},
            age=None,
            next_hop_int=None,
            next_AS=None,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.35/30",
            next_hop_ip="10.102.3.34",
            metric=0,
            flags={"B"},
            age=1581935,
            next_hop_int="ethernet1/21.200",
            next_AS=64920,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.35/30",
            next_hop_ip="10.102.3.33",
            metric=0,
            flags={"A", "C"},
            age=None,
            next_hop_int="ethernet1/21.200",
            next_AS=None,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.3.33/32",
            next_hop_ip="0.0.0.0",
            metric=0,
            flags={"A", "H"},
            age=None,
            next_hop_int=None,
            next_AS=None,
        ),
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.102.72.0/24",
            next_hop_ip="10.102.3.7",
            metric=10000,
            flags={"A", "B"},
            age=1350407,
            next_hop_int="ae1.100",
            next_AS=65256,
        ),
    ]


def test_show_routing_route_multi_vr() -> None:
    text = """show routing route

flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf, B:bgp,
       Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2, E:ecmp, M:multicast


VIRTUAL ROUTER: My virtual router (id 2)
  ==========
destination nexthop metric flags age interface next-AS
10.178.143.0/24 10.102.3.7 10 A B 1348860 ae1.100 65256
total routes shown: 1

VIRTUAL ROUTER: Another virtual router (id 3)
  ==========
destination nexthop metric flags age interface next-AS
10.102.142.181/32 10.102.3.24 A B E 621200 ethernet1/22.500 64920
total routes shown: 1"""
    routes = parse_show_routing_route(text)
    assert routes == [
        PanosMainRibRoute(
            virtual_router="My virtual router",
            network="10.178.143.0/24",
            next_hop_ip="10.102.3.7",
            metric=10,
            flags={"A", "B"},
            age=1348860,
            next_hop_int="ae1.100",
            next_AS=65256,
        ),
        PanosMainRibRoute(
            virtual_router="Another virtual router",
            network="10.102.142.181/32",
            next_hop_ip="10.102.3.24",
            metric=None,
            flags={"A", "B", "E"},
            age=621200,
            next_hop_int="ethernet1/22.500",
            next_AS=64920,
        ),
    ]


def test_show_routing_route_bgp_without_interface() -> None:
    text = """
flags: A:active, ?:loose, C:connect, H:host, S:static, ~:internal, R:rip, O:ospf, B:bgp,
       Oi:ospf intra-area, Oo:ospf inter-area, O1:ospf ext-type-1, O2:ospf ext-type-2, E:ecmp, M:multicast


VIRTUAL ROUTER: default (id 1)
  ==========
destination                nexthop                                 metric flags      age   interface          next-AS
0.0.0.0/0                  10.2.1.5                                       A?B        13030                    65401
"""
    routes = parse_show_routing_route(text)
    assert routes == [
        PanosMainRibRoute(
            virtual_router="default",
            network="0.0.0.0/0",
            next_hop_ip="10.2.1.5",
            metric=None,
            flags={"A", "?", "B"},
            age=13030,
            next_hop_int=None,
            next_AS=65401,
        ),
    ]
