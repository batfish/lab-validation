import math

import attr
import pytest
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp, NextHopVtep

from lab_validation.parsers.arista.models.interfaces import AristaInterface
from lab_validation.parsers.arista.models.routes import (
    AristaBgpRoute,
    AristaEvpnRoute,
    AristaIpRoute,
)
from lab_validation.validators.AristaValidator import AristaValidator
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import (
    BgpRibRoute,
    EvpnRibRoute,
    MainRibRoute,
)


def test_diff_routes_cost() -> None:
    arista_route = AristaIpRoute(
        network="1.1.1.1",
        protocol="ebgp",
        next_hop_ip="1.1.1.3",
        next_hop_int="iface",
        preference=1,
        metric=2,
        vrf="vrf",
        vni=None,
        vtep_ip=None,
    )

    batfish_route = MainRibRoute(
        network="1.1.1.1",
        protocol="bgp",
        next_hop=NextHopIp(ip="1.1.1.3"),
        admin=1,
        metric=2,
        tag=0,
        vrf="vrf",
    )

    assert AristaValidator._diff_routes_cost(arista_route, batfish_route) == []

    # network mismatch
    assert AristaValidator._diff_routes_cost(
        arista_route, attr.evolve(batfish_route, network="2.2.2.2")
    ) == [("network", math.inf)]

    # vrf mismatch
    assert AristaValidator._diff_routes_cost(
        arista_route, attr.evolve(batfish_route, vrf="other")
    ) == [("vrf", math.inf)]

    # protocol mismatch
    assert AristaValidator._diff_routes_cost(
        arista_route, attr.evolve(batfish_route, protocol="static")
    ) == [("protocol", math.inf)]

    # admin mismatch
    assert AristaValidator._diff_routes_cost(
        attr.evolve(arista_route, preference=5),
        batfish_route,
    ) == [("admin", 2.0)]

    # metric mismatch
    assert AristaValidator._diff_routes_cost(
        attr.evolve(arista_route, metric=20),
        batfish_route,
    ) == [("metric", 1.0)]

    # next hop mismatch
    assert AristaValidator._diff_routes_cost(
        attr.evolve(arista_route, protocol="static"),
        attr.evolve(
            batfish_route,
            protocol="static",
            next_hop=NextHopInterface(interface="ifac", ip="1.1.1.3"),
        ),
    ) == [("nhint", 5.0)]


def test_compute_protocol_cost() -> None:
    # same value
    assert AristaValidator.compute_protocol_cost("ibgp", "ibgp") == []

    # bgp combinations
    assert AristaValidator.compute_protocol_cost("ebgp", "bgp") == []
    assert AristaValidator.compute_protocol_cost("ebgp", "ibgp") == [
        ("bgp subtype", 1.0)
    ]
    assert AristaValidator.compute_protocol_cost("ibgp", "bgp") == [
        ("bgp subtype", 1.0)
    ]

    # ospf
    assert AristaValidator.compute_protocol_cost("ospf", "ospfE1") == [
        ("ospf subtype", 1.0)
    ]

    # disparate
    assert AristaValidator.compute_protocol_cost("ibgp", "ospf") == [
        ("protocol", math.inf)
    ]


def test_compute_next_hop_cost() -> None:
    arista_route = AristaIpRoute(
        network="1.1.1.1",
        protocol="ebgp",
        next_hop_ip="1.1.1.3",
        next_hop_int="iface",
        preference=1,
        metric=2,
        vrf="vrf",
        vni=None,
        vtep_ip=None,
    )

    assert (
        AristaValidator.compute_next_hop_cost(arista_route, NextHopIp(ip="1.1.1.3"))
        == []
    )

    # both null
    assert (
        AristaValidator.compute_next_hop_cost(
            attr.evolve(arista_route, next_hop_int="Null0"),
            NextHopDiscard(),
        )
        == []
    )

    # Asymmetric null, both directions
    assert AristaValidator.compute_next_hop_cost(
        arista_route,
        NextHopDiscard(),
    ) == [("asymmetric null route", 10.0)]
    assert AristaValidator.compute_next_hop_cost(
        attr.evolve(arista_route, next_hop_int="Null0"), NextHopIp(ip="1.1.1.3")
    ) == [("asymmetric null route", 10.0)]

    #  next hop IP
    assert AristaValidator.compute_next_hop_cost(
        arista_route, NextHopIp(ip="1.1.1.1")
    ) == [("nhip", 1.0)]

    # next hop IP for static routes
    assert (
        AristaValidator.compute_next_hop_cost(
            attr.evolve(arista_route, protocol="static"),
            NextHopIp(ip="1.1.1.1"),
        )
        == []
    )

    # nhint mismatch
    assert AristaValidator.compute_next_hop_cost(
        attr.evolve(arista_route, next_hop_int="Ethernet2"),
        NextHopInterface(interface="Ethernet1", ip="1.1.1.3"),
    ) == [("nhint", 5.0)]

    # nhint missing from Batfish (static nhint route should have it)
    assert (
        AristaValidator.compute_next_hop_cost(
            attr.evolve(arista_route, next_hop_int="Ethernet2", protocol="static"),
            NextHopIp(ip="1.1.1.3"),
        )
        == []
    )

    # nhint missing from Arista
    assert AristaValidator.compute_next_hop_cost(
        attr.evolve(arista_route, next_hop_int=None),
        NextHopInterface(interface="Ethernet1"),
    ) == [("asymmetric nhint", 5.0)]


def test_compute_next_hop_cost_vtep() -> None:
    arista_route = AristaIpRoute(
        vrf="default",
        network="10.3.255.6/32",
        next_hop_int=None,
        next_hop_ip="",
        protocol="eBGP",
        preference=200,
        metric=0,
        vni=50301,
        vtep_ip="192.168.254.6",
    )

    assert (
        AristaValidator.compute_next_hop_cost(
            arista_route, NextHopVtep(vni=50301, vtep="192.168.254.6")
        )
        == []
    )

    # mismatch
    assert AristaValidator.compute_next_hop_cost(
        arista_route, NextHopVtep(vni=5030, vtep="192.168.254.6")
    ) == [("vni", 1.0)]
    assert AristaValidator.compute_next_hop_cost(
        arista_route, NextHopVtep(vni=50301, vtep="192.168.254.7")
    ) == [("vtep", 1.0)]
    assert AristaValidator.compute_next_hop_cost(
        arista_route, NextHopVtep(vni=5030, vtep="192.168.254.7")
    ) == [("vni", 1.0), ("vtep", 1.0)]

    # incompat
    assert AristaValidator.compute_next_hop_cost(
        arista_route,
        NextHopDiscard(),
    ) == [("asymmetric vtep", 10.0)]
    assert AristaValidator.compute_next_hop_cost(
        attr.evolve(arista_route, vni=None, vtep_ip=""),
        NextHopVtep(vni=50301, vtep="192.168.254.6"),
    ) == [("asymmetric vtep", 10.0)]


def test_diff_bgp_routes_cost() -> None:
    arista_route = AristaBgpRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        is_active=True,
        is_ecmp=False,
        not_installed_reason=None,
        next_hop_ip="2.2.2.2",
        metric=0,
        local_preference=100,
        as_path=(1,),
        weight=1,
    )
    batfish_route = BgpRibRoute(
        weight=1,
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
        origin_type="type",
        tag=0,
    )

    assert AristaValidator._diff_bgp_routes_cost(arista_route, batfish_route) == []

    # network mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        arista_route, attr.evolve(batfish_route, network="2.2.2.2")
    ) == [("network", math.inf)]

    # vrf mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        arista_route, attr.evolve(batfish_route, vrf="other")
    ) == [("vrf", math.inf)]

    # metric mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        attr.evolve(arista_route, metric=20),
        batfish_route,
    ) == [("metric", 1.0)]

    # local preference mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        attr.evolve(arista_route, local_preference=20),
        batfish_route,
    ) == [("local preference", 1.0)]

    # as path mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        attr.evolve(arista_route, as_path=(1, 2)),
        batfish_route,
    ) == [("as path", 1.0)]

    # weight mismatch
    assert AristaValidator._diff_bgp_routes_cost(
        attr.evolve(arista_route, weight=10),
        batfish_route,
    ) == [("weight", 1.0)]


def test_validate_bgp_rib_routes_ignore_non_best() -> None:
    arista_routes = [
        AristaBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=False,
            is_ecmp=False,
            not_installed_reason=None,
            next_hop_ip="2.2.2.2",
            metric=0,
            local_preference=100,
            as_path=(1, 2),
            weight=1,
        )
    ]
    failures = AristaValidator._validate_bgp_rib_routes(arista_routes, [])
    assert failures == {}


def test_is_best_bgp_route() -> None:
    inactive = AristaBgpRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        is_active=False,
        is_ecmp=False,
        not_installed_reason=None,
        next_hop_ip="2.2.2.2",
        metric=0,
        local_preference=100,
        as_path=(1, 2),
        weight=1,
    )
    active = attr.evolve(inactive, is_active=True)
    rib_failure = attr.evolve(inactive, not_installed_reason="routeBestInactive")
    different_reason = attr.evolve(inactive, not_installed_reason="someOtherReason")
    ecmp_best = attr.evolve(inactive, is_ecmp=True)
    assert not AristaValidator.is_best_bgp_route(inactive)
    assert AristaValidator.is_best_bgp_route(active)
    assert AristaValidator.is_best_bgp_route(rib_failure)
    assert not AristaValidator.is_best_bgp_route(different_reason)
    assert AristaValidator.is_best_bgp_route(ecmp_best)


def test_validate_bgp_rib_routes_local() -> None:
    expected_routes = [
        AristaBgpRoute(
            vrf="vrf",
            network="1.1.1.0/24",
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            next_hop_ip=None,
            metric=0,
            local_preference=100,
            as_path=(),
            weight=32768,
        )
    ]
    bf_routes = [
        BgpRibRoute(
            weight=32768,
            vrf="vrf",
            network="1.1.1.0/24",
            next_hop=NextHopDiscard(),
            next_hop_ip="AUTO/NONE(-1l)",
            next_hop_int="null_interface",
            protocol="bgp",
            metric=0,
            communities=(),
            local_preference=100,
            as_path="",
            origin_protocol="bgp",
            origin_type="type",
            tag=0,
        )
    ]
    failures = AristaValidator._validate_bgp_rib_routes(expected_routes, bf_routes)
    assert failures == {}


def test_compare_all_interfaces_equal() -> None:
    expected_interfaces = [
        AristaInterface(name="Ethernet0", bandwidth=int(1e5), mtu=1500, line=True)
    ]
    batfish_interfaces = [
        InterfaceProperties(
            name="Ethernet0",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e8),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {}


def test_compare_all_interfaces_mismatch_active() -> None:
    expected_interfaces = [
        AristaInterface(name="Ethernet0", bandwidth=int(1e5), mtu=1500, line=True)
    ]
    batfish_interfaces = [
        InterfaceProperties(
            name="Ethernet0",
            access_vlan=None,
            active=False,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e8),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {"ethernet0": {"active": "Batfish: False, Arista: True"}}


@pytest.mark.xfail
def test_compare_all_interfaces_mismatch_mtu() -> None:
    expected_interfaces = [
        AristaInterface(name="Ethernet0", bandwidth=int(1e5), mtu=9214, line=True)
    ]
    batfish_interfaces = [
        InterfaceProperties(
            name="Ethernet0",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e8),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {"ethernet0": {"mtu": "Batfish: 1500, Arista: 9214"}}


def test_compare_all_interfaces_missing() -> None:
    expected_interfaces = [
        AristaInterface(name="Ethernet0", bandwidth=int(1e5), mtu=1500, line=True)
    ]
    batfish_interfaces = []

    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {
        "ethernet0": f"Missing interface in Batfish: {expected_interfaces[0]}"
    }


def test_compare_all_interfaces_missing_vlan() -> None:
    expected_interfaces = [
        AristaInterface(name="vlan100", bandwidth=int(1e5), mtu=1500, line=True)
    ]
    batfish_interfaces = []

    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {}


def test_compare_all_interfaces_extra() -> None:
    expected_interfaces = []
    batfish_interfaces = [
        InterfaceProperties(
            name="Ethernet0",
            access_vlan=None,
            active=True,
            all_prefixes=["1.2.3.4/25"],
            allowed_vlans=None,
            bandwidth=int(1e8),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=int(1e3),
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    failures = AristaValidator._compare_all_interfaces(
        expected_interfaces, batfish_interfaces
    )
    assert failures == {
        "ethernet0": f"Extra interface in Batfish: {batfish_interfaces[0]}"
    }


def test_validate_evpn_rib_routes_equal() -> None:
    arista_route = AristaEvpnRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        is_active=True,
        next_hop_ip="2.2.2.2",
        local_preference=100,
        as_path=(1,),
        weight=1,
        as_path_type="internal",
        origin="Igp",
        route_distinguisher="rd",
    )

    batfish_route = EvpnRibRoute(
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
        origin_protocol="connected",
        origin_type="IGP",
        tag=0,
        route_distinguisher="rd",
    )

    assert AristaValidator._diff_evpn_routes_cost(arista_route, batfish_route) == []

    # network mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, network="2.2.2.2")
    ) == [("network", math.inf)]

    # vrf mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, vrf="other")
    ) == [("vrf", math.inf)]

    # route distinguisher mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, route_distinguisher="rdd")
    ) == [("route_distinguisher", math.inf)]

    # next hop ip mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, next_hop_ip="3.3.3.3")
    ) == [("next_hop_ip", 10.0)]

    # local preference mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, local_preference=10)
    ) == [("local_preference", 1.0)]

    # as path mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, as_path=[1, 2])
    ) == [("as_path", 1.0)]

    # origin type mismatch
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, origin_type="EGP")
    ) == [("origin_type", 1.0)]


def test_diff_evpn_routes_cost_special_nhip_cases() -> None:
    arista_route = AristaEvpnRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        is_active=True,
        next_hop_ip=None,
        local_preference=100,
        as_path=(1,),
        weight=1,
        as_path_type="internal",
        origin="Igp",
        route_distinguisher="rd",
    )

    batfish_route = EvpnRibRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        next_hop_ip="AUTO/NONE(-1l)",
        next_hop=NextHopDiscard(),
        next_hop_int="null_interface",
        protocol="bgp",
        metric=0,
        communities=(),
        local_preference=100,
        as_path="1",
        origin_protocol="connected",
        origin_type="IGP",
        tag=0,
        route_distinguisher="rd",
    )

    # Both routes have no NHIP
    assert AristaValidator._diff_evpn_routes_cost(arista_route, batfish_route) == []

    # If Arista route has a NHIP or Batfish route has a NHIP or next hop interface, no match
    assert AristaValidator._diff_evpn_routes_cost(
        attr.evolve(arista_route, next_hop_ip="2.2.2.2"), batfish_route
    ) == [("next_hop_ip", 10.0)]
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, next_hop_ip="2.2.2.2")
    ) == [("next_hop_ip", 10.0)]
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, next_hop_int="eth1")
    ) == [("next_hop_ip", 10.0)]


def test_diff_evpn_routes_cost_special_localpref_cases() -> None:
    arista_route = AristaEvpnRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        is_active=True,
        next_hop_ip="2.2.2.2",
        local_preference=None,
        as_path=(1,),
        weight=1,
        as_path_type="internal",
        origin="Igp",
        route_distinguisher="rd",
    )

    batfish_route = EvpnRibRoute(
        vrf="vrf",
        network="1.1.1.0/24",
        next_hop=NextHopInterface(interface="iface", ip="2.2.2.2"),
        next_hop_ip="2.2.2.2",
        next_hop_int="iface",
        protocol="bgp",
        metric=0,
        communities=(),
        local_preference=0,
        as_path="1",
        origin_protocol="connected",
        origin_type="IGP",
        tag=0,
        route_distinguisher="rd",
    )

    # Arista route with None for local pref indicates it is effectively 0
    assert AristaValidator._diff_evpn_routes_cost(arista_route, batfish_route) == []

    # Arista route has a not-none value for local pref, or batfish has a nonzero value
    assert AristaValidator._diff_evpn_routes_cost(
        attr.evolve(arista_route, local_preference=10), batfish_route
    ) == [("local_preference", 1.0)]
    assert AristaValidator._diff_evpn_routes_cost(
        arista_route, attr.evolve(batfish_route, local_preference=10)
    ) == [("local_preference", 1.0)]
