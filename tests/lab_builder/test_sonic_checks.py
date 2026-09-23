"""Tests for SONiC health and validation check parsing.

Fixtures are real output captured from containerlab sonic-vm nodes
(SONiC.202605, FRR 10.5.4) while building the sonic_ebgp lab, trimmed to
the fields the checks read.
"""

from __future__ import annotations

import pytest

from lab_builder import health, validate
from lab_builder.config import SONIC_VM
from lab_builder.models import NodeInfo

# vtysh -c 'show bgp vrf all summary json' with both peers Established.
BGP_SUMMARY_ESTABLISHED = """\
{
"default":{
"ipv4Unicast":{
  "routerId":"1.1.1.1",
  "as":65001,
  "vrfName":"default",
  "peerCount":2,
  "peers":{
    "192.168.12.1":{
      "hostname":"s2",
      "remoteAs":65002,
      "localAs":65001,
      "pfxRcd":1,
      "state":"Established",
      "peerState":"OK",
      "desc":"s2"
    },
    "192.168.12.3":{
      "hostname":"s2",
      "remoteAs":65002,
      "localAs":65001,
      "pfxRcd":1,
      "state":"Established",
      "peerState":"OK",
      "desc":"s2"
    }
  },
  "totalPeers":2
}
}
}
"""

# Same command on the default (unconfigured) sonic-vm config, whose sample
# neighbors never come up.
BGP_SUMMARY_ACTIVE = """\
{
"default":{
"ipv4Unicast":{
  "routerId":"10.1.0.1",
  "as":65100,
  "vrfName":"default",
  "peerCount":1,
  "peers":{
    "10.0.0.1":{
      "remoteAs":65200,
      "localAs":65100,
      "pfxRcd":0,
      "state":"Active",
      "peerState":"OK",
      "desc":"ARISTA01T2"
    }
  },
  "totalPeers":1
}
}
}
"""

# FRR prints an empty object when no BGP instance exists.
BGP_SUMMARY_NO_BGP = "{}\n"

# vtysh -c 'show ip route vrf default 2.2.2.2/32 json'
ROUTE_PRESENT = """\
{
  "2.2.2.2/32":[
    {
      "prefix":"2.2.2.2/32",
      "protocol":"bgp",
      "vrfName":"default",
      "selected":true,
      "installed":true,
      "nexthops":[
        {"ip":"192.168.12.1", "interfaceName":"Ethernet0", "active":true},
        {"ip":"192.168.12.3", "interfaceName":"Ethernet4", "active":true}
      ]
    }
  ]
}
"""

# Same command for a prefix that is not in the table.
ROUTE_ABSENT = "{}\n"

# show interfaces status Ethernet0
INTERFACE_UP = """\
  Interface        Lanes    Speed    MTU    FEC         Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  -----------  -------  -----  -----  ------------  ------  ------  -------  ------  ----------
  Ethernet0  25,26,27,28      40G   9100    N/A  fortyGigE0/0  routed      up       up     N/A         N/A
"""  # noqa: E501

# show interfaces status Ethernet8 (unwired port)
INTERFACE_DOWN = """\
  Interface        Lanes    Speed    MTU    FEC          Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  -----------  -------  -----  -----  -------------  ------  ------  -------  ------  ----------
  Ethernet8  33,34,35,36      40G   9100    N/A   fortyGigE0/8  routed    down       up     N/A         N/A
"""  # noqa: E501


@pytest.fixture()
def sonic_node() -> NodeInfo:
    return NodeInfo(
        name="s1", kind="sonic-vm", profile=SONIC_VM, management_ip="1.2.3.4"
    )


def _patch_run_command(monkeypatch, module, output: str) -> None:
    monkeypatch.setattr(module, "run_command", lambda *a, **k: output)


class TestSonicHealthBgp:
    def test_established(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_SUMMARY_ESTABLISHED)
        assert health.check_bgp_established(sonic_node) is True

    def test_active(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_SUMMARY_ACTIVE)
        assert health.check_bgp_established(sonic_node) is False

    def test_not_configured(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_SUMMARY_NO_BGP)
        assert health.check_bgp_established(sonic_node) is None


class TestSonicHealthIgp:
    def test_ospf_not_checked(self, sonic_node: NodeInfo) -> None:
        assert health.check_ospf_full(sonic_node) is None

    def test_isis_not_checked(self, sonic_node: NodeInfo) -> None:
        assert health.check_isis_up(sonic_node) is None

    def test_no_platform_warnings(self, sonic_node: NodeInfo) -> None:
        assert health.check_platform_warnings(sonic_node) == []


class TestSonicValidateRouteExists:
    def test_route_present(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_PRESENT)
        result = validate.check_route_exists(sonic_node, "default", "2.2.2.2/32")
        assert result.passed

    def test_route_absent(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_ABSENT)
        result = validate.check_route_exists(sonic_node, "default", "9.9.9.9/32")
        assert not result.passed

    def test_ipv6_uses_ipv6_table(self, monkeypatch, sonic_node: NodeInfo) -> None:
        commands: list[str] = []

        def fake_run(node, command, **kwargs):
            commands.append(command)
            return ROUTE_ABSENT

        monkeypatch.setattr(validate, "run_command", fake_run)
        validate.check_route_exists(sonic_node, "default", "2001:db8::/64")
        assert commands == ["vtysh -c 'show ipv6 route vrf default 2001:db8::/64 json'"]


class TestSonicValidateInterfaceUp:
    def test_up(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, INTERFACE_UP)
        assert validate.check_interface_up(sonic_node, "Ethernet0").passed

    def test_down(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, INTERFACE_DOWN)
        result = validate.check_interface_up(sonic_node, "Ethernet8")
        assert not result.passed
        assert "oper down" in result.detail


class TestSonicValidateBgpPeer:
    def test_established(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_ESTABLISHED)
        result = validate.check_bgp_peer_established(sonic_node, "192.168.12.3")
        assert result.passed

    def test_active(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_ACTIVE)
        result = validate.check_bgp_peer_established(sonic_node, "10.0.0.1")
        assert not result.passed
        assert result.detail == "10.0.0.1: Active"

    def test_not_found(self, monkeypatch, sonic_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_ESTABLISHED)
        result = validate.check_bgp_peer_established(sonic_node, "192.168.12.9")
        assert not result.passed
