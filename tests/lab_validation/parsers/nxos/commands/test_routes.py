from collections.abc import Sequence

import pytest

from lab_validation.parsers.common.exceptions import UnrecognizedLinesError
from lab_validation.parsers.nxos.commands.routes import parse_show_ip_route_vrf_all
from lab_validation.parsers.nxos.models.routes import NxosMainRibRoute


def test_routes_empty() -> None:
    routes = """IP Route Table for VRF "default"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

    """
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == []


def test_routes_error() -> None:
    routes = """IP Route Table for VRF "default"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

        1.1.1.1/32, ubest/mbest: 1/0
            *via 10.10.11.1, [200/0], 03:27:56, bgp-65001, internal, tag 65001
        1.1.1.3/32, ubest/mbest: 2/0, attached
            *via 1.1.1.3, Lo0, [0/0], 03:23:20, protocol-you-never-heard-of
        2.1.1.1/32, ubest/mbest: 1/0
            *via 10.10.11.1, [200/0], 03:27:56, bgp-65001, internal, tag 65001
    """
    with pytest.raises(UnrecognizedLinesError) as _:
        parse_show_ip_route_vrf_all(routes)


def test_null_route() -> None:
    routes = """IP Route Table for VRF "default"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

        10.0.0.0/9, ubest/mbest: 1/0
            *via Null0, [220/0], 03:28:31, bgp-65114, discard, tag 65114
    """
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == [
        NxosMainRibRoute(
            vrf="default",
            network="10.0.0.0/9",
            protocol="bgp",
            next_vrf=None,
            next_hop_ip=None,
            next_hop_int="Null0",
            admin=220,
            metric=0,
            tag=65114,
            evpn=False,
            segid=None,
            tunnelid=None,
        )
    ]


def test_non_best_route() -> None:
    """
    Tests that non-best routes are parsed and ignored
    """
    routes = """IP Route Table for VRF "default"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

        10.0.0.0/9, ubest/mbest: 1/0
            *via 10.198.226.165, [1/0], 28w1d, static, tag 65333 segid: 3002 tunnelid: 0xac6e048 encap: VXLAN

            via 10.198.224.94%default, [20/0], 1y32w, bgp-65333, external, tag 65011 (evpn) segid: 3002 tunnelid: 0xac6e05e encap: VXLAN
    """
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == [
        NxosMainRibRoute(
            vrf="default",
            network="10.0.0.0/9",
            protocol="static",
            next_vrf=None,
            next_hop_ip="10.198.226.165",
            next_hop_int=None,
            admin=1,
            metric=0,
            tag=65333,
            evpn=False,
            segid=3002,
            tunnelid="10.198.224.72",
        )
    ]


def test_evpn_route() -> None:
    routes = """IP Route Table for VRF "foo"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

        192.168.20.0/24, ubest/mbest: 1/0
            *via 2.2.2.2%default, [200/0], 1d18h, bgp-65000, internal, tag 65000 (evpn) segid: 100777 tunnelid: 0x2020202 encap: VXLAN"""
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == [
        NxosMainRibRoute(
            vrf="foo",
            network="192.168.20.0/24",
            protocol="ibgp",
            next_vrf="default",
            next_hop_ip="2.2.2.2",
            next_hop_int=None,
            admin=200,
            metric=0,
            tag=65000,
            evpn=True,
            segid=100777,
            tunnelid="2.2.2.2",
        )
    ]


def test_routes_multiple_vrfs() -> None:
    routes = """IP Route Table for VRF "default"
        '*' denotes best ucast next-hop
        '**' denotes best mcast next-hop
        '[x/y]' denotes [preference/metric]
        '%<string>' in via output denotes VRF <string>

        1.1.1.1/32, ubest/mbest: 1/0
            *via 10.10.11.1, [200/0], 03:27:56, bgp-65001, internal, tag 65001
        1.1.1.3/32, ubest/mbest: 2/0, attached
            *via 1.1.1.3, Lo0, [0/0], 03:23:20, local
            *via 1.1.1.3, Lo0, [0/0], 03:23:20, direct
            *via 10.13.21.1, Eth1/1, [170/2585856], 01:32:31, eigrp-1, external
            *via 10.13.21.2, Eth1/2, [90/130816], 01:32:30, eigrp-1, internal
            *via 10.15.41.2, Eth1/4, [110/41], 00:05:10, ospf-1, intra
            *via 10.12.11.2, [1/0], 03:16:08, static

     IP Route Table for VRF "vrf1"
    '*' denotes best ucast next-hop
    '**' denotes best mcast next-hop
    '[x/y]' denotes [preference/metric]
    '%<string>' in via output denotes VRF <string>

    192.168.10.0/24, ubest/mbest: 1/0, attached
        *via 192.168.10.1, Vlan10, [0/0], 03:31:02, direct
    """
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == [
        NxosMainRibRoute(
            network="1.1.1.1/32",
            protocol="ibgp",
            next_vrf=None,
            next_hop_ip="10.10.11.1",
            next_hop_int=None,
            admin=200,
            metric=0,
            tag=65001,
            vrf="default",
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="local",
            next_vrf=None,
            next_hop_ip="1.1.1.3",
            next_hop_int="Loopback0",
            admin=0,
            metric=0,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="direct",
            next_vrf=None,
            next_hop_ip="1.1.1.3",
            next_hop_int="Loopback0",
            admin=0,
            metric=0,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="eigrpEX",
            next_vrf=None,
            next_hop_ip="10.13.21.1",
            next_hop_int="Ethernet1/1",
            admin=170,
            metric=2585856,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="eigrp",
            next_vrf=None,
            next_hop_ip="10.13.21.2",
            next_hop_int="Ethernet1/2",
            admin=90,
            metric=130816,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="ospf",
            next_vrf=None,
            next_hop_ip="10.15.41.2",
            next_hop_int="Ethernet1/4",
            admin=110,
            metric=41,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="1.1.1.3/32",
            protocol="static",
            next_vrf=None,
            next_hop_ip="10.12.11.2",
            next_hop_int=None,
            admin=1,
            metric=0,
            vrf="default",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
        NxosMainRibRoute(
            network="192.168.10.0/24",
            protocol="direct",
            next_vrf=None,
            next_hop_ip="192.168.10.1",
            next_hop_int="Vlan10",
            admin=0,
            metric=0,
            vrf="vrf1",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
    ]


def test_routes_multiple_vrfs_empty_then_present() -> None:
    routes = """IP Route Table for VRF "default"
    '*' denotes best ucast next-hop
    '**' denotes best mcast next-hop
    '[x/y]' denotes [preference/metric]
    '%<string>' in via output denotes VRF <string>


    IP Route Table for VRF "vrf1"
    '*' denotes best ucast next-hop
    '**' denotes best mcast next-hop
    '[x/y]' denotes [preference/metric]
    '%<string>' in via output denotes VRF <string>

    192.168.10.0/24, ubest/mbest: 1/0, attached
        *via 192.168.10.1, Vlan10, [0/0], 03:31:02, direct
    """
    records: Sequence[NxosMainRibRoute] = parse_show_ip_route_vrf_all(routes)
    assert records == [
        NxosMainRibRoute(
            network="192.168.10.0/24",
            protocol="direct",
            next_vrf=None,
            next_hop_ip="192.168.10.1",
            next_hop_int="Vlan10",
            admin=0,
            metric=0,
            vrf="vrf1",
            tag=None,
            evpn=False,
            segid=None,
            tunnelid=None,
        ),
    ]
