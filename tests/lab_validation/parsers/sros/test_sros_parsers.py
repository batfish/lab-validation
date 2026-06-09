"""Unit tests for the SR OS state-tree JSON parsers, against captured lab data.

Each parser has a "full model" test that takes the raw captured state file and
asserts the *entire* parsed model (every field of every object, by whole-object
equality), plus targeted tests for the non-obvious bits (attr-set join, as-path
flattening, optional/empty containers).
"""

from pathlib import Path

from lab_validation.parsers.sros.commands.bgp_routes import (
    _parse_as_path,
    parse_bgp_rib_json,
)
from lab_validation.parsers.sros.commands.interfaces import parse_interface_state_json
from lab_validation.parsers.sros.commands.routes import parse_route_table_json
from lab_validation.parsers.sros.models.interfaces import SrosInterface
from lab_validation.parsers.sros.models.routes import SrosBgpRoute, SrosIpRoute

# The captured r1 (SR-SIM) state from the sros_ceos_ebgp lab.
_R1_SHOW = (
    Path(__file__).resolve().parents[4] / "snapshots" / "sros_ceos_ebgp" / "show" / "r1"
)


def _read(name: str) -> str:
    return (_R1_SHOW / name).read_text()


# --- interfaces -----------------------------------------------------------------


def test_parse_interfaces_full_model() -> None:
    """Whole-object equality of every interface parsed from the captured state."""
    ifaces = parse_interface_state_json(
        _read("info_json_state_router_Base_interface.txt")
    )
    assert ifaces == [
        SrosInterface(
            name="system",
            oper_up=True,
            ipv4_up=True,
            primary_address="1.1.1.1",
            if_index=1,
            mtu=1500,
        ),
        SrosInterface(
            name="to-r2",
            oper_up=True,
            ipv4_up=True,
            primary_address="10.0.0.0",
            if_index=2,
            mtu=8922,
        ),
    ]


def test_parse_interfaces_no_ipv4_container() -> None:
    """An interface with no ipv4/primary container parses with no address (ipv4 down)."""
    text = """{
      "nokia-state:interface": [
        {"interface-name": "bare", "oper-state": "up"}
      ]
    }"""
    assert parse_interface_state_json(text) == [
        SrosInterface(name="bare", oper_up=True, ipv4_up=False, primary_address=None)
    ]


# --- route table ----------------------------------------------------------------


def test_parse_route_table_full_model() -> None:
    """Whole-object equality of every route parsed from the captured route-table.

    Passes the if-index -> name map (system=1, to-r2=2) so connected-route
    next-hop interfaces resolve; the learned BGP route keeps its next-hop IP.
    """
    routes = parse_route_table_json(
        _read("info_json_state_router_Base_route-table.txt"),
        "default",
        {1: "system", 2: "to-r2"},
    )
    assert routes == [
        SrosIpRoute(
            network="1.1.1.1/32",
            vrf="default",
            protocol="local",
            next_hop_ip=None,
            next_hop_interface="system",
            preference=0,
            metric=0,
        ),
        SrosIpRoute(
            network="2.2.2.2/32",
            vrf="default",
            protocol="bgp",
            next_hop_ip="10.0.0.1",
            next_hop_interface=None,
            preference=170,
            metric=0,
        ),
        SrosIpRoute(
            network="10.0.0.0/31",
            vrf="default",
            protocol="local",
            next_hop_ip=None,
            next_hop_interface="to-r2",
            preference=0,
            metric=0,
        ),
    ]


def test_parse_route_table_ipv6_skipped() -> None:
    """Only the ipv4-unicast table is modeled; an ipv6 sibling is ignored, not crashed."""
    text = """{
      "nokia-state:unicast": {
        "ipv4": {"route": [
          {"ipv4-prefix": "5.5.5.5/32", "protocol": "static", "preference": 5,
           "nexthop": [{"nexthop-ip": "1.2.3.4", "metric": 7}]}
        ]},
        "ipv6": {"route": [{"ipv6-prefix": "::/0"}]}
      }
    }"""
    assert parse_route_table_json(text, "default") == [
        SrosIpRoute(
            network="5.5.5.5/32",
            vrf="default",
            protocol="static",
            next_hop_ip="1.2.3.4",
            preference=5,
            metric=7,
        )
    ]


# --- BGP RIB --------------------------------------------------------------------


def test_parse_bgp_rib_full_model() -> None:
    """Whole-object equality of every BGP RIB route (attrs joined from attr-sets)."""
    routes = parse_bgp_rib_json(
        _read("info_json_state_router_Base_bgp_rib.txt"), "default"
    )
    assert routes == [
        SrosBgpRoute(
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
        ),
        SrosBgpRoute(
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
        ),
        SrosBgpRoute(
            network="10.0.0.0/31",
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
        ),
    ]


def test_parse_bgp_rib_med_join() -> None:
    """A route whose attr-set carries a MED gets it joined onto the route."""
    text = """{
      "nokia-state:ipv4-unicast": {"local-rib": {"routes": [
        {"prefix": "7.7.7.7/32", "neighbor": "10.0.0.1", "owner": "bgp", "attr-id": "3",
         "used-route": true, "valid-route": true, "best-route": false}
      ]}},
      "nokia-state:attr-sets": {"attr-set": [
        {"index": "3", "origin": "incomplete", "next-hop": "10.0.0.1", "med": 50}
      ]}
    }"""
    assert parse_bgp_rib_json(text, "default") == [
        SrosBgpRoute(
            network="7.7.7.7/32",
            vrf="default",
            owner="bgp",
            neighbor="10.0.0.1",
            next_hop_ip="10.0.0.1",
            origin_type="incomplete",
            med=50,
            as_path=[],
            used=True,
            valid=True,
            best=False,
        )
    ]


def test_parse_bgp_rib_missing_attr_set() -> None:
    """A route referencing an absent attr-id degrades to empty attributes, not a crash."""
    text = """{
      "nokia-state:ipv4-unicast": {"local-rib": {"routes": [
        {"prefix": "8.8.8.8/32", "neighbor": "0.0.0.0", "owner": "local", "attr-id": "99",
         "used-route": true, "valid-route": false, "best-route": true}
      ]}},
      "nokia-state:attr-sets": {"attr-set": []}
    }"""
    assert parse_bgp_rib_json(text, "default") == [
        SrosBgpRoute(
            network="8.8.8.8/32",
            vrf="default",
            owner="local",
            neighbor="0.0.0.0",
            next_hop_ip=None,
            origin_type="",
            med=None,
            as_path=[],
            used=True,
            valid=False,
            best=True,
        )
    ]


def test_parse_as_path_multi_segment() -> None:
    """The nested segment/as-numbers structure flattens to an ordered ASN list."""
    as_path = {
        "segment": [
            {
                "type": "as-sequence",
                "as-numbers": [
                    {"as-number": 65001},
                    {"as-number": 65002},
                ],
            },
            {"type": "as-sequence", "as-numbers": [{"as-number": 65003}]},
        ]
    }
    assert _parse_as_path(as_path) == [65001, 65002, 65003]
    assert _parse_as_path(None) == []
    assert _parse_as_path({}) == []
