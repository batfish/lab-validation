"""Tests for Cisco NX-OS health and validation check parsing.

Fixtures are real ``show`` output captured from a running Cisco N9Kv
(NX-OS 10.3.9.M) while building the nxos_isis lab.
"""

from __future__ import annotations

import pytest

from lab_builder import health, validate
from lab_builder.config import CISCO_N9KV
from lab_builder.models import NodeInfo

# Real "show isis adjacency" with one established (UP) adjacency.
ISIS_ADJACENCY_UP = """\
IS-IS process: UNDERLAY VRF: default
IS-IS adjacency database:
Legend: '!': No AF level connectivity in given topology-subnet
System ID       SNPA            Level  State  Hold Time  Interface
r2              N/A             2      UP     00:00:29   Ethernet1/1
"""

# Same instance but the neighbor is still initializing.
ISIS_ADJACENCY_INIT = """\
IS-IS process: UNDERLAY VRF: default
IS-IS adjacency database:
System ID       SNPA            Level  State  Hold Time  Interface
r2              N/A             2      INIT   00:00:27   Ethernet1/1
"""

# No IS-IS instance configured / no adjacencies.
ISIS_NO_PROCESS = "% IS-IS is not enabled\n"

# "show ip route <prefix> vrf default" output for an IS-IS-learned loopback.
ROUTE_PRESENT = """\
IP Route Table for VRF "default"
'*' denotes best ucast next-hop
'**' denotes best mcast next-hop
'[x/y]' denotes [preference/metric]
'%<string>' in via output denotes VRF <string>

2.2.2.2/32, ubest/mbest: 1/0
    *via 10.0.0.1, Eth1/1, [115/40], 00:01:23, isis-UNDERLAY, L2
"""

ROUTE_ABSENT = """\
% Route not found
"""


@pytest.fixture()
def nxos_node() -> NodeInfo:
    return NodeInfo(
        name="r1", kind="cisco_n9kv", profile=CISCO_N9KV, management_ip="1.2.3.4"
    )


def _patch_run_command(monkeypatch, module, output: str) -> None:
    monkeypatch.setattr(module, "run_command", lambda *a, **k: output)


class TestNxosHealthIsis:
    def test_up(self, monkeypatch, nxos_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, ISIS_ADJACENCY_UP)
        assert health.check_isis_up(nxos_node) is True

    def test_init(self, monkeypatch, nxos_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, ISIS_ADJACENCY_INIT)
        assert health.check_isis_up(nxos_node) is False

    def test_not_configured(self, monkeypatch, nxos_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, health, ISIS_NO_PROCESS)
        assert health.check_isis_up(nxos_node) is None


class TestNxosValidateRouteExists:
    def test_route_present(self, monkeypatch, nxos_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_PRESENT)
        result = validate.check_route_exists(nxos_node, "default", "2.2.2.2/32")
        assert result.passed

    def test_route_absent(self, monkeypatch, nxos_node: NodeInfo) -> None:
        _patch_run_command(monkeypatch, validate, ROUTE_ABSENT)
        result = validate.check_route_exists(nxos_node, "default", "3.3.3.3/32")
        assert not result.passed
