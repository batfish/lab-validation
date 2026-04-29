"""Tests for lab_builder.snapshot, focused on layer1_topology generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lab_builder.config import ARISTA_CEOS, VJUNOS_ROUTER
from lab_builder.models import NodeInfo
from lab_builder.snapshot import _eth_to_vendor_interface, _generate_layer1_topology


@pytest.fixture()
def arista_node() -> NodeInfo:
    return NodeInfo(
        name="r1", kind="arista_ceos", profile=ARISTA_CEOS, management_ip="1.2.3.4"
    )


@pytest.fixture()
def junos_node() -> NodeInfo:
    return NodeInfo(
        name="r2",
        kind="juniper_vjunosrouter",
        profile=VJUNOS_ROUTER,
        management_ip="1.2.3.5",
    )


class TestEthToVendorInterface:
    def test_arista_eth1(self, arista_node: NodeInfo) -> None:
        assert _eth_to_vendor_interface("eth1", arista_node) == "Ethernet1"

    def test_arista_eth3(self, arista_node: NodeInfo) -> None:
        assert _eth_to_vendor_interface("eth3", arista_node) == "Ethernet3"

    def test_junos_eth1(self, junos_node: NodeInfo) -> None:
        assert _eth_to_vendor_interface("eth1", junos_node) == "ge-0/0/0"

    def test_junos_eth3(self, junos_node: NodeInfo) -> None:
        assert _eth_to_vendor_interface("eth3", junos_node) == "ge-0/0/2"

    def test_passthrough(self, arista_node: NodeInfo) -> None:
        assert _eth_to_vendor_interface("Loopback0", arista_node) == "Loopback0"


class TestGenerateLayer1Topology:
    def test_basic(self, tmp_path: Path, arista_node: NodeInfo) -> None:
        topo = tmp_path / "topology.clab.yml"
        topo.write_text(
            """
name: test
topology:
  nodes:
    r1:
      kind: arista_ceos
      image: ceos:4.36.0.1F
    r2:
      kind: arista_ceos
      image: ceos:4.36.0.1F
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
"""
        )
        r2 = NodeInfo(
            name="r2", kind="arista_ceos", profile=ARISTA_CEOS, management_ip="1.2.3.5"
        )
        snapshot_dir = tmp_path / "snapshot"
        snapshot_dir.mkdir()
        _generate_layer1_topology(topo, [arista_node, r2], snapshot_dir)

        l1 = json.loads((snapshot_dir / "batfish" / "layer1_topology.json").read_text())
        assert len(l1["edges"]) == 1
        edge = l1["edges"][0]
        assert edge["node1"] == {"hostname": "r1", "interfaceName": "Ethernet1"}
        assert edge["node2"] == {"hostname": "r2", "interfaceName": "Ethernet1"}

    def test_mixed_vendors(
        self, tmp_path: Path, arista_node: NodeInfo, junos_node: NodeInfo
    ) -> None:
        topo = tmp_path / "topology.clab.yml"
        topo.write_text(
            """
name: test
topology:
  nodes:
    r1:
      kind: arista_ceos
    r2:
      kind: juniper_vjunosrouter
  links:
    - endpoints: ["r1:eth1", "r2:eth1"]
    - endpoints: ["r1:eth2", "r2:eth2"]
"""
        )
        snapshot_dir = tmp_path / "snapshot"
        snapshot_dir.mkdir()
        _generate_layer1_topology(topo, [arista_node, junos_node], snapshot_dir)

        l1 = json.loads((snapshot_dir / "batfish" / "layer1_topology.json").read_text())
        assert len(l1["edges"]) == 2
        assert l1["edges"][0]["node1"]["interfaceName"] == "Ethernet1"
        assert l1["edges"][0]["node2"]["interfaceName"] == "ge-0/0/0"
        assert l1["edges"][1]["node1"]["interfaceName"] == "Ethernet2"
        assert l1["edges"][1]["node2"]["interfaceName"] == "ge-0/0/1"

    def test_no_links(self, tmp_path: Path, arista_node: NodeInfo) -> None:
        topo = tmp_path / "topology.clab.yml"
        topo.write_text(
            """
name: test
topology:
  nodes:
    r1:
      kind: arista_ceos
"""
        )
        snapshot_dir = tmp_path / "snapshot"
        snapshot_dir.mkdir()
        _generate_layer1_topology(topo, [arista_node], snapshot_dir)
        assert not (snapshot_dir / "batfish" / "layer1_topology.json").exists()
