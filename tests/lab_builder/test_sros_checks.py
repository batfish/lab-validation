"""Tests for Nokia SR OS health and validation check parsing.

Fixtures are real ``show`` output captured from a running SR-SIM (SR OS
26.3.R1) while building the srsim-ceos-ebgp lab.
"""

from __future__ import annotations

import pytest

from lab_builder import health, validate
from lab_builder.config import NOKIA_SRSIM
from lab_builder.models import NodeInfo

# Real "show router bgp summary" neighbor block: peer address on its own line,
# then a line whose state column is "1/1/1" (Rcv/Act/Sent) when established.
BGP_SUMMARY_ESTABLISHED = """\
===============================================================================
 BGP Router ID:1.1.1.1          AS:65001       Local AS:65001
===============================================================================
BGP Admin State         : Up          BGP Oper State              : Up
===============================================================================
Neighbor
Description
                   AS PktRcvd InQ  Up/Down   State|Rcv/Act/Sent (Addr Family)
                      PktSent OutQ
-------------------------------------------------------------------------------
10.0.0.1
                65002      10    0 00h02m19s 1/1/1 (IPv4)
                            9    0
-------------------------------------------------------------------------------
"""

# Same format but the peer is still coming up: state column is a word.
BGP_SUMMARY_CONNECT = """\
===============================================================================
Neighbor
                   AS PktRcvd InQ  Up/Down   State|Rcv/Act/Sent (Addr Family)
-------------------------------------------------------------------------------
10.0.0.1
                65002       0    0 00h00m05s Connect
-------------------------------------------------------------------------------
"""

BGP_NOT_CONFIGURED = (
    "MINOR: CLI #2005: Error while processing command - BGP is not configured"
)

ROUTE_TABLE = """\
===============================================================================
Route Table (Router: Base)
===============================================================================
Dest Prefix[Flags]                            Type    Proto     Age        Pref
      Next Hop[Interface Name]                                    Metric
-------------------------------------------------------------------------------
1.1.1.1/32                                    Local   Local     00h02m30s  0
       system                                                       0
2.2.2.2/32                                    Remote  BGP       00h02m14s  170
       10.0.0.1                                                     0
10.0.0.0/31                                   Local   Local     00h02m17s  0
       to-r2                                                        0
-------------------------------------------------------------------------------
"""


@pytest.fixture()
def sros_node() -> NodeInfo:
    return NodeInfo(
        name="r1", kind="nokia_srsim", profile=NOKIA_SRSIM, management_ip="1.2.3.4"
    )


def _patch_run_command(monkeypatch, module, output: str) -> None:
    monkeypatch.setattr(module, "run_command", lambda *a, **k: output)


class TestSrosHealthBgp:
    def test_established(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_SUMMARY_ESTABLISHED)
        assert health.check_bgp_established(sros_node) is True

    def test_not_established(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_SUMMARY_CONNECT)
        assert health.check_bgp_established(sros_node) is False

    def test_not_configured(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, BGP_NOT_CONFIGURED)
        assert health.check_bgp_established(sros_node) is None


class TestSrosValidateBgpPeer:
    def test_established(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_ESTABLISHED)
        result = validate.check_bgp_peer_established(sros_node, "10.0.0.1")
        assert result.passed
        assert "Established" in result.detail

    def test_not_established(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_CONNECT)
        result = validate.check_bgp_peer_established(sros_node, "10.0.0.1")
        assert not result.passed
        assert "Connect" in result.detail

    def test_peer_not_found(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, BGP_SUMMARY_ESTABLISHED)
        result = validate.check_bgp_peer_established(sros_node, "10.9.9.9")
        assert not result.passed
        assert "not found" in result.detail


class TestSrosValidateRouteExists:
    def test_route_present(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_TABLE)
        result = validate.check_route_exists(sros_node, "Base", "2.2.2.2/32")
        assert result.passed

    def test_route_absent(self, monkeypatch, sros_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_TABLE)
        result = validate.check_route_exists(sros_node, "Base", "3.3.3.3/32")
        assert not result.passed
