"""Tests for FRR health and validation check parsing."""

from __future__ import annotations

import pytest

from lab_builder import health, validate
from lab_builder.config import ARISTA_CEOS, FRR
from lab_builder.models import NodeInfo

# vtysh -c 'show ip ospf neighbor json' with both adjacencies Full.
OSPF_NEIGHBORS_FULL = """\
{
  "neighbors":{
    "10.255.0.1":[
      {
        "nbrPriority":1,
        "nbrState":"Full/-",
        "converged":"Full",
        "role":"DROther",
        "ifaceAddress":"10.0.1.1",
        "ifaceName":"eth1:10.0.1.0"
      }
    ],
    "10.255.0.2":[
      {
        "nbrPriority":1,
        "nbrState":"Full/-",
        "converged":"Full",
        "role":"DROther",
        "ifaceAddress":"10.0.2.1",
        "ifaceName":"eth2:10.0.2.0"
      }
    ]
  }
}
"""

# Same command while one adjacency is still exchanging databases.
OSPF_NEIGHBORS_EXSTART = """\
{
  "neighbors":{
    "10.255.0.1":[
      {"nbrState":"Full/-", "ifaceName":"eth1:10.0.1.0"}
    ],
    "10.255.0.2":[
      {"nbrState":"ExStart/-", "ifaceName":"eth2:10.0.2.0"}
    ]
  }
}
"""

# OSPF instance with no adjacency yet.
OSPF_NO_NEIGHBORS = '{\n  "neighbors":{\n  }\n}\n'

# No OSPF instance.
OSPF_NOT_CONFIGURED = "{\n}\n"

# vtysh -c 'show ip route vrf default 10.255.1.1/32 json', via abr2.
ROUTE_VIA_ABR2 = """\
{
  "10.255.1.1/32":[
    {
      "prefix":"10.255.1.1/32",
      "protocol":"ospf",
      "vrfName":"default",
      "selected":true,
      "destSelected":true,
      "distance":110,
      "metric":80000,
      "installed":true,
      "nexthops":[
        {"ip":"10.0.2.1", "afi":"ipv4", "interfaceName":"eth2", "active":true}
      ]
    }
  ]
}
"""

# vtysh -c 'show interface eth1 json'
INTERFACE_UP = """\
{
  "eth1":{
    "administrativeStatus":"up",
    "operationalStatus":"up",
    "mtu":1500
  }
}
"""

INTERFACE_DOWN = """\
{
  "eth3":{
    "administrativeStatus":"up",
    "operationalStatus":"down",
    "mtu":1500
  }
}
"""


@pytest.fixture()
def frr_node() -> NodeInfo:
    return NodeInfo(name="r0", kind="frr", profile=FRR, management_ip="1.2.3.4")


def _patch_run_command(monkeypatch, module, output: str) -> None:
    monkeypatch.setattr(module, "run_command", lambda *a, **k: output)


class TestFrrHealthOspf:
    def test_full(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, OSPF_NEIGHBORS_FULL)
        assert health.check_ospf_full(frr_node) is True

    def test_not_full(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, OSPF_NEIGHBORS_EXSTART)
        assert health.check_ospf_full(frr_node) is False

    def test_no_neighbors(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, OSPF_NO_NEIGHBORS)
        assert health.check_ospf_full(frr_node) is False

    def test_not_configured(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, OSPF_NOT_CONFIGURED)
        assert health.check_ospf_full(frr_node) is None

    def test_ospfd_not_running(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, "ospfd is not running\n")
        assert health.check_ospf_full(frr_node) is None

    def test_isis_not_checked(self, frr_node: NodeInfo) -> None:
        assert health.check_isis_up(frr_node) is None

    def test_no_platform_warnings(self, frr_node: NodeInfo) -> None:
        assert health.check_platform_warnings(frr_node) == []


class TestFrrHealthBgp:
    def test_bgpd_not_running(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, "bgpd is not running\n")
        assert health.check_bgp_established(frr_node) is None

    def test_not_configured(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, "{}\n")
        assert health.check_bgp_established(frr_node) is None


class TestFrrValidateRouteNextHops:
    def test_match(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_VIA_ABR2)
        result = validate.check_route_next_hops(
            frr_node, "default", "10.255.1.1/32", ["10.0.2.1"], 80000
        )
        assert result.passed
        assert result.detail == "10.255.1.1/32: via ['10.0.2.1'], metric 80000"

    def test_wrong_next_hop(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_VIA_ABR2)
        result = validate.check_route_next_hops(
            frr_node, "default", "10.255.1.1/32", ["10.0.1.1"], None
        )
        assert not result.passed

    def test_wrong_metric(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_VIA_ABR2)
        result = validate.check_route_next_hops(
            frr_node, "default", "10.255.1.1/32", ["10.0.2.1"], 20
        )
        assert not result.passed

    def test_absent(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, "{}\n")
        result = validate.check_route_next_hops(
            frr_node, "default", "10.255.1.1/32", ["10.0.2.1"], None
        )
        assert not result.passed
        assert result.detail == "10.255.1.1/32: no selected route"

    def test_unsupported_vendor(self) -> None:
        node = NodeInfo(
            name="r1", kind="arista_ceos", profile=ARISTA_CEOS, management_ip="1.2.3.5"
        )
        result = validate.check_route_next_hops(
            node, "default", "10.255.1.1/32", ["10.0.2.1"], None
        )
        assert not result.passed

    def test_run_checks_dispatch(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_VIA_ABR2)
        [result] = validate.run_checks(
            [frr_node],
            [
                {
                    "type": "route_next_hops",
                    "node": "r0",
                    "table": "default",
                    "prefix": "10.255.1.1/32",
                    "next_hops": ["10.0.2.1"],
                }
            ],
        )
        assert result.passed


class TestFrrValidateInterfaceUp:
    def test_up(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, INTERFACE_UP)
        assert validate.check_interface_up(frr_node, "eth1").passed

    def test_down(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, INTERFACE_DOWN)
        result = validate.check_interface_up(frr_node, "eth3")
        assert not result.passed
        assert result.detail == "eth3: oper down, admin up"

    def test_not_found(self, monkeypatch, frr_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, "{}\n")
        assert not validate.check_interface_up(frr_node, "eth9").passed
