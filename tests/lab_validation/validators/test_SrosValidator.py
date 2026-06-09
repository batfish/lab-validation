import math
import shutil
from pathlib import Path

import pytest
from pybatfish.datamodel import NextHopDiscard, NextHopInterface, NextHopIp

from lab_validation.parsers.sros.models.interfaces import SrosInterface
from lab_validation.parsers.sros.models.routes import SrosBgpRoute, SrosIpRoute
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.batfish_models.routes import BgpRibRoute, MainRibRoute
from lab_validation.validators.SrosValidator import SrosValidator


def _iface_props(**kwargs) -> InterfaceProperties:
    base = dict(
        name="to-r2",
        active=True,
        all_prefixes=["10.0.0.0/31"],
        allowed_vlans=None,
        bandwidth=1000000000,
        description=None,
        mtu=1500,
        speed=1000000000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    base.update(kwargs)
    return InterfaceProperties(**base)


def _main_route(**kwargs) -> MainRibRoute:
    base = dict(
        vrf="default",
        network="2.2.2.2/32",
        next_hop=NextHopIp(ip="10.0.0.1"),
        protocol="bgp",
        metric=0,
        admin=170,
        tag=None,
    )
    base.update(kwargs)
    return MainRibRoute(**base)


def _bgp_route(**kwargs) -> BgpRibRoute:
    base = dict(
        vrf="default",
        network="2.2.2.2/32",
        next_hop=NextHopIp(ip="10.0.0.1"),
        protocol="bgp",
        as_path=(65002,),
        metric=0,
        local_preference=100,
        communities=(),
        origin_protocol="bgp",
        origin_type="igp",
        weight=0,
        tag=None,
    )
    base.update(kwargs)
    return BgpRibRoute(**base)


def _sros_iface(**kwargs) -> SrosInterface:
    base = dict(name="to-r2", oper_up=True, ipv4_up=True, primary_address="10.0.0.0")
    base.update(kwargs)
    return SrosInterface(**base)


def _sros_route(**kwargs) -> SrosIpRoute:
    base = dict(
        network="2.2.2.2/32",
        vrf="default",
        protocol="bgp",
        next_hop_ip="10.0.0.1",
        preference=170,
        metric=0,
    )
    base.update(kwargs)
    return SrosIpRoute(**base)


def _sros_bgp_route(**kwargs) -> SrosBgpRoute:
    base = dict(
        network="2.2.2.2/32",
        vrf="default",
        owner="bgp",
        neighbor="10.0.0.1",
        next_hop_ip="10.0.0.1",
        origin_type="igp",
        med=None,
        as_path=[65002],
        used=True,
        valid=True,
        best=True,
    )
    base.update(kwargs)
    return SrosBgpRoute(**base)


# --- protocol mapping -----------------------------------------------------------


def test_protocol_cost() -> None:
    assert SrosValidator._protocol_cost("local", "connected") == []
    assert SrosValidator._protocol_cost("bgp", "bgp") == []
    # SR OS reports both eBGP and iBGP learned routes as "bgp"; Batfish labels an
    # iBGP-learned main-RIB route "ibgp", so SR OS "bgp" must match either.
    assert SrosValidator._protocol_cost("bgp", "ibgp") == []
    assert SrosValidator._protocol_cost("static", "static") == []
    assert SrosValidator._protocol_cost("isis", "isis") == []
    # Incompatible protocols never pair.
    assert SrosValidator._protocol_cost("bgp", "connected") == [("protocol", math.inf)]


# --- main RIB next-hop ----------------------------------------------------------


def test_next_hop_cost_local_route() -> None:
    # A local route (no SR OS next-hop IP) matches a Batfish interface next-hop.
    local = SrosIpRoute(
        network="1.1.1.1/32",
        vrf="default",
        protocol="local",
        next_hop_ip=None,
        preference=0,
        metric=0,
    )
    assert (
        SrosValidator._next_hop_cost(local, NextHopInterface(interface="system")) == []
    )
    assert SrosValidator._next_hop_cost(local, NextHopDiscard()) == []
    # ...but mismatches a Batfish IP next-hop.
    assert SrosValidator._next_hop_cost(local, NextHopIp(ip="10.0.0.1")) == [
        ("asymmetric nhip", 5.0)
    ]


def test_next_hop_cost_bgp_route() -> None:
    bgp = SrosIpRoute(
        network="2.2.2.2/32",
        vrf="default",
        protocol="bgp",
        next_hop_ip="10.0.0.1",
        preference=170,
        metric=0,
    )
    assert SrosValidator._next_hop_cost(bgp, NextHopIp(ip="10.0.0.1")) == []
    assert SrosValidator._next_hop_cost(bgp, NextHopIp(ip="9.9.9.9")) == [("nhip", 1.0)]


def test_next_hop_cost_interface_with_ip() -> None:
    # Batfish models the next-hop as an interface carrying the resolved IP (e.g. a
    # resolved BGP next-hop). It matches the SR OS next-hop IP, else costs nhip.
    route = _sros_route(next_hop_ip="10.0.0.1")
    assert (
        SrosValidator._next_hop_cost(
            route, NextHopInterface(interface="to-r2", ip="10.0.0.1")
        )
        == []
    )
    assert SrosValidator._next_hop_cost(
        route, NextHopInterface(interface="to-r2", ip="9.9.9.9")
    ) == [("nhip", 1.0)]


def test_diff_routes_cost_vrf_mismatch() -> None:
    # Same prefix in a different VRF must never pair (infinite cost).
    sros = _sros_route(network="2.2.2.2/32", vrf="red")
    assert SrosValidator._diff_routes_cost(
        sros, _main_route(network="2.2.2.2/32", vrf="blue")
    ) == [("vrf", math.inf)]


def test_diff_bgp_routes_cost_vrf_mismatch() -> None:
    sros = _sros_bgp_route(network="2.2.2.2/32", vrf="red")
    assert SrosValidator._diff_bgp_routes_cost(
        sros, _bgp_route(network="2.2.2.2/32", vrf="blue")
    ) == [("vrf", math.inf)]


# --- main RIB cost --------------------------------------------------------------


def test_diff_routes_cost_match() -> None:
    sros = SrosIpRoute(
        network="2.2.2.2/32",
        vrf="default",
        protocol="bgp",
        next_hop_ip="10.0.0.1",
        preference=170,
        metric=0,
    )
    assert SrosValidator._diff_routes_cost(sros, _main_route()) == []


def test_diff_routes_cost_network_mismatch() -> None:
    sros = SrosIpRoute(
        network="2.2.2.2/32",
        vrf="default",
        protocol="bgp",
        next_hop_ip="10.0.0.1",
        preference=170,
        metric=0,
    )
    assert SrosValidator._diff_routes_cost(sros, _main_route(network="3.3.3.3/32")) == [
        ("network", math.inf)
    ]


def test_diff_routes_cost_admin_and_metric() -> None:
    sros = SrosIpRoute(
        network="2.2.2.2/32",
        vrf="default",
        protocol="bgp",
        next_hop_ip="10.0.0.1",
        preference=99,
        metric=5,
    )
    cost = SrosValidator._diff_routes_cost(sros, _main_route(admin=170, metric=0))
    assert ("admin", 2.0) in cost
    assert ("metric", 1.0) in cost


# --- BGP RIB cost ---------------------------------------------------------------


def test_diff_bgp_routes_cost_learned_match() -> None:
    sros = SrosBgpRoute(
        network="2.2.2.2/32",
        vrf="default",
        owner="bgp",
        neighbor="10.0.0.1",
        next_hop_ip="10.0.0.1",
        origin_type="igp",
        med=None,
        as_path=[65002],
        used=True,
        valid=True,
        best=True,
    )
    assert SrosValidator._diff_bgp_routes_cost(sros, _bgp_route()) == []


def test_diff_bgp_routes_cost_as_path_mismatch() -> None:
    sros = SrosBgpRoute(
        network="2.2.2.2/32",
        vrf="default",
        owner="bgp",
        neighbor="10.0.0.1",
        next_hop_ip="10.0.0.1",
        origin_type="igp",
        med=None,
        as_path=[65999],
        used=True,
        valid=True,
        best=True,
    )
    assert SrosValidator._diff_bgp_routes_cost(sros, _bgp_route()) == [("as_path", 1.0)]


def test_diff_bgp_routes_cost_local_ignores_next_hop() -> None:
    # A locally-originated route reports 0.0.0.0 in SR OS; we do not compare its
    # next-hop against Batfish's own-address next-hop.
    sros = SrosBgpRoute(
        network="1.1.1.1/32",
        vrf="default",
        owner="local",
        neighbor="0.0.0.0",
        next_hop_ip="0.0.0.0",
        origin_type="igp",
        med=None,
        as_path=[],
        used=True,
        valid=True,
        best=True,
    )
    local_bgp = _bgp_route(network="1.1.1.1/32", next_hop=NextHopDiscard(), as_path=())
    assert SrosValidator._diff_bgp_routes_cost(sros, local_bgp) == []


# --- interface comparison -------------------------------------------------------


def test_compare_interface_match() -> None:
    sros = SrosInterface(
        name="to-r2", oper_up=True, ipv4_up=True, primary_address="10.0.0.0"
    )
    assert SrosValidator._compare_interface(sros, _iface_props()) == {}


def test_compare_interface_active_mismatch() -> None:
    sros = SrosInterface(
        name="to-r2", oper_up=False, ipv4_up=False, primary_address="10.0.0.0"
    )
    diff = SrosValidator._compare_interface(sros, _iface_props(active=True))
    assert "active" in diff


def test_compare_interface_address_mismatch() -> None:
    sros = SrosInterface(
        name="to-r2", oper_up=True, ipv4_up=True, primary_address="10.0.0.0"
    )
    diff = SrosValidator._compare_interface(
        sros, _iface_props(all_prefixes=["192.0.2.1/24"])
    )
    assert "address" in diff


def test_compare_interface_no_address_either_side() -> None:
    # An interface with no IP on either side (e.g. an unnumbered/L2 interface) is a match.
    sros = _sros_iface(primary_address=None)
    assert SrosValidator._compare_interface(sros, _iface_props(all_prefixes=[])) == {}


def test_compare_interface_batfish_has_address_sros_none() -> None:
    sros = _sros_iface(primary_address=None)
    diff = SrosValidator._compare_interface(
        sros, _iface_props(all_prefixes=["10.0.0.0/31"])
    )
    assert "address" in diff


# --- interface set comparison (the orchestration) -------------------------------


def test_compare_all_interfaces_match() -> None:
    sros = [
        _sros_iface(name="system", primary_address="1.1.1.1"),
        _sros_iface(name="to-r2", primary_address="10.0.0.0"),
    ]
    batfish = [
        _iface_props(name="system", all_prefixes=["1.1.1.1/32"]),
        _iface_props(name="to-r2", all_prefixes=["10.0.0.0/31"]),
    ]
    assert SrosValidator._compare_all_interfaces(sros, batfish) == {}


def test_compare_all_interfaces_skips_physical_ports() -> None:
    # Batfish models the L3 router-interface "to-r2" plus its synthetic PHYSICAL port
    # "1/1/c1/1" (the Layer-1 endpoint). The device interface-state tree lists only the
    # L3 interface, so the PHYSICAL port must be ignored, not flagged as "extra".
    sros = [_sros_iface(name="to-r2", primary_address="10.0.0.0")]
    batfish = [
        _iface_props(
            name="to-r2", all_prefixes=["10.0.0.0/31"], interface_type="LOGICAL"
        ),
        _iface_props(name="1/1/c1/1", all_prefixes=[], interface_type="PHYSICAL"),
    ]
    assert SrosValidator._compare_all_interfaces(sros, batfish) == {}


def test_compare_all_interfaces_extra_in_batfish() -> None:
    # Batfish has an interface the device does not report.
    diffs = SrosValidator._compare_all_interfaces(
        [_sros_iface(name="to-r2")],
        [_iface_props(name="to-r2"), _iface_props(name="to-r3")],
    )
    assert set(diffs) == {"to-r3"}
    assert "Extra interface in Batfish" in diffs["to-r3"]


def test_compare_all_interfaces_missing_in_batfish() -> None:
    # Device has an interface Batfish did not create.
    diffs = SrosValidator._compare_all_interfaces(
        [_sros_iface(name="to-r2"), _sros_iface(name="to-r3")],
        [_iface_props(name="to-r2")],
    )
    assert set(diffs) == {"to-r3"}
    assert "Missing interface in Batfish" in diffs["to-r3"]


def test_compare_all_interfaces_case_insensitive() -> None:
    # Names are matched case-insensitively (device "System" vs Batfish "system").
    diffs = SrosValidator._compare_all_interfaces(
        [_sros_iface(name="System", primary_address="1.1.1.1")],
        [_iface_props(name="system", all_prefixes=["1.1.1.1/32"])],
    )
    assert diffs == {}


# --- main RIB validation (filter + match orchestration) -------------------------


def test_validate_main_rib_routes_all_match() -> None:
    sros = [
        _sros_route(
            network="1.1.1.1/32", protocol="local", next_hop_ip=None, preference=0
        ),
        _sros_route(network="2.2.2.2/32", protocol="bgp", next_hop_ip="10.0.0.1"),
    ]
    batfish = [
        _main_route(
            network="1.1.1.1/32",
            protocol="connected",
            next_hop=NextHopInterface(interface="system"),
            admin=0,
        ),
        _main_route(
            network="2.2.2.2/32", protocol="bgp", next_hop=NextHopIp(ip="10.0.0.1")
        ),
    ]
    assert SrosValidator._validate_main_rib_routes(sros, batfish) == {}


def test_validate_main_rib_routes_missing_in_batfish() -> None:
    # Device has a route Batfish does not — must surface, not silently pass.
    sros = [_sros_route(network="2.2.2.2/32"), _sros_route(network="3.3.3.3/32")]
    batfish = [_main_route(network="2.2.2.2/32")]
    failures = SrosValidator._validate_main_rib_routes(sros, batfish)
    assert failures
    assert any("3.3.3.3/32" in k for k in failures)


def test_validate_main_rib_routes_attribute_mismatch() -> None:
    # Same prefix, wrong admin distance -> a non-empty failure with the cost.
    sros = [_sros_route(network="2.2.2.2/32", preference=170)]
    batfish = [_main_route(network="2.2.2.2/32", admin=200)]
    failures = SrosValidator._validate_main_rib_routes(sros, batfish)
    assert failures


# --- BGP RIB validation (the owner=="bgp" grounding decision) -------------------


def test_validate_bgp_rib_routes_filters_local_rib_artifacts() -> None:
    # The SR OS bgp-rib local-RIB over-lists: it includes owner=local connected
    # routes (in-rtm=false) that are NOT in the operational BGP table and NOT in
    # Batfish's BGP RIB. The validator must compare only the learned (owner=="bgp")
    # subset, so those local entries do not show up as missing-in-Batfish failures.
    sros = [
        _sros_bgp_route(
            network="1.1.1.1/32", owner="local", neighbor="0.0.0.0", as_path=[]
        ),
        _sros_bgp_route(
            network="10.0.0.0/31", owner="local", neighbor="0.0.0.0", as_path=[]
        ),
        _sros_bgp_route(network="2.2.2.2/32", owner="bgp", as_path=[65002]),
    ]
    batfish = [_bgp_route(network="2.2.2.2/32", as_path=(65002,))]
    assert SrosValidator._validate_bgp_rib_routes(sros, batfish) == {}


def test_validate_bgp_rib_routes_drops_non_best() -> None:
    # Only best routes are compared; a non-best learned route is ignored.
    sros = [
        _sros_bgp_route(network="2.2.2.2/32", best=True),
        _sros_bgp_route(network="9.9.9.9/32", best=False),
    ]
    batfish = [_bgp_route(network="2.2.2.2/32")]
    assert SrosValidator._validate_bgp_rib_routes(sros, batfish) == {}


def test_validate_bgp_rib_routes_learned_route_missing() -> None:
    # A learned route absent from Batfish must surface as a failure.
    sros = [_sros_bgp_route(network="2.2.2.2/32", owner="bgp")]
    assert SrosValidator._validate_bgp_rib_routes(sros, [])


# --- BGP next-hop cost ----------------------------------------------------------


def test_bgp_next_hop_cost_ip_match() -> None:
    assert SrosValidator._bgp_next_hop_cost("10.0.0.1", NextHopIp(ip="10.0.0.1")) == []


def test_bgp_next_hop_cost_ip_mismatch() -> None:
    assert SrosValidator._bgp_next_hop_cost("10.0.0.1", NextHopIp(ip="9.9.9.9")) == [
        ("nhip", 1.0)
    ]


def test_bgp_next_hop_cost_local_origin_discard() -> None:
    # Locally-originated route: SR OS reports no usable next-hop IP; Batfish uses a
    # discard/own next-hop. Not comparable -> no cost.
    assert SrosValidator._bgp_next_hop_cost(None, NextHopDiscard()) == []


def test_bgp_next_hop_cost_asymmetric() -> None:
    # SR OS has a next-hop IP but Batfish models a non-IP next-hop.
    assert SrosValidator._bgp_next_hop_cost("10.0.0.1", NextHopDiscard()) == [
        ("asymmetric next hop", 5.0)
    ]


def test_diff_bgp_routes_cost_origin_mismatch() -> None:
    sros = _sros_bgp_route(origin_type="egp")
    assert SrosValidator._diff_bgp_routes_cost(sros, _bgp_route(origin_type="igp")) == [
        ("origin_type", 1.0)
    ]


# --- runtime data ---------------------------------------------------------------


def test_get_runtime_data(tmp_path) -> None:
    # get_runtime_data parses the interface state file and reports line status.
    src = (
        Path(__file__).resolve().parents[3]
        / "snapshots"
        / "sros_ceos_ebgp"
        / "show"
        / "r1"
        / "info_json_state_router_Base_interface.txt"
    )
    shutil.copy(src, tmp_path / SrosValidator.INTERFACE_FILENAME)
    rt = SrosValidator(tmp_path).get_runtime_data()
    assert set(rt.interfaces) == {"system", "to-r2"}
    assert rt.interfaces["system"].lineUp is True
    assert rt.interfaces["system"].bandwidth is None


def test_parse_helpers_assert_on_missing_file(tmp_path) -> None:
    # The parse helpers crash (not silently degrade) when a state file is absent.
    v = SrosValidator(tmp_path)
    with pytest.raises(AssertionError):
        v._parse_interfaces()
    with pytest.raises(AssertionError):
        v._parse_routes()
    with pytest.raises(AssertionError):
        v._parse_bgp_routes()
