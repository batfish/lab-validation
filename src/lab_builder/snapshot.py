"""Package collected data into a lab-validation snapshot."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml

from lab_builder.config import command_to_filename
from lab_builder.models import NodeInfo


def build_snapshot(
    name: str,
    nodes: list[NodeInfo],
    collected_dir: Path,
    snapshots_dir: Path,
    topology_file: Path | None = None,
) -> Path:
    """Build a lab-validation snapshot from collected data.

    Creates the standard directory structure:
        snapshots/<name>/
        ├── configs/<hostname>/show_configuration_|_display_set.txt
        ├── show/host_nos.txt
        ├── show/<hostname>/<show_command>.txt
        ├── batfish/layer1_topology.json  (if topology_file provided)
        └── validation/

    Returns the path to the created snapshot directory.
    """
    snapshot_dir = snapshots_dir / name
    configs_dir = snapshot_dir / "configs"
    show_dir = snapshot_dir / "show"
    validation_dir = snapshot_dir / "validation"

    for d in [configs_dir, show_dir, validation_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Build host_nos.txt
    host_nos = {node.name: node.profile.name for node in nodes}
    (show_dir / "host_nos.txt").write_text(json.dumps(host_nos))
    print(f"Created host_nos.txt: {host_nos}")

    for node in nodes:
        config_filename = command_to_filename(node.profile.config_command)

        src_node_dir = collected_dir / node.name
        if not src_node_dir.exists():
            print(f"Warning: no collected data for {node.name}")
            continue

        # Copy config file to configs/<hostname>/
        config_src = src_node_dir / config_filename
        if config_src.exists():
            config_dest_dir = configs_dir / node.name
            config_dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_src, config_dest_dir / config_filename)
            print(f"  {node.name}: config -> configs/{node.name}/")

        # Copy show command outputs to show/<hostname>/
        show_node_dir = show_dir / node.name
        show_node_dir.mkdir(parents=True, exist_ok=True)

        for filepath in sorted(src_node_dir.iterdir()):
            if not filepath.is_file():
                continue
            # Skip the config file in the show directory
            if filepath.name == config_filename:
                continue
            shutil.copy2(filepath, show_node_dir / filepath.name)

        file_count = len(list(show_node_dir.iterdir()))
        print(f"  {node.name}: {file_count} show files -> show/{node.name}/")

    # Generate layer1_topology.json from containerlab topology
    if topology_file is not None:
        _generate_layer1_topology(topology_file, nodes, snapshot_dir)

    print(f"Snapshot created at: {snapshot_dir}")
    return snapshot_dir


def _eth_to_vendor_interface(eth_name: str, profile: NodeInfo) -> str:
    """Convert containerlab ethN name to vendor interface name.

    eth1 maps to <prefix><offset>, eth2 to <prefix><offset+1>, etc.
    """
    match = re.match(r"eth(\d+)", eth_name)
    if not match:
        return eth_name
    eth_num = int(match.group(1))
    vendor_num = eth_num - 1 + profile.profile.interface_offset
    prefix = profile.profile.interface_prefix
    return f"{prefix}{vendor_num}"


def _generate_layer1_topology(
    topology_file: Path, nodes: list[NodeInfo], snapshot_dir: Path
) -> None:
    """Generate batfish/layer1_topology.json from containerlab topology links."""
    topo = yaml.safe_load(topology_file.read_text())
    links = topo.get("topology", {}).get("links", [])
    if not links:
        return

    nodes_by_name = {n.name: n for n in nodes}
    edges = []
    for link in links:
        endpoints = link.get("endpoints", [])
        if len(endpoints) != 2:
            continue
        parts = [ep.split(":", 1) for ep in endpoints]
        if any(len(p) != 2 for p in parts):
            continue
        node1_name, eth1 = parts[0]
        node2_name, eth2 = parts[1]
        node1 = nodes_by_name.get(node1_name)
        node2 = nodes_by_name.get(node2_name)
        if node1 is None or node2 is None:
            continue
        iface1 = _eth_to_vendor_interface(eth1, node1)
        iface2 = _eth_to_vendor_interface(eth2, node2)
        edges.append(
            {
                "node1": {"hostname": node1_name, "interfaceName": iface1},
                "node2": {"hostname": node2_name, "interfaceName": iface2},
            }
        )

    if edges:
        batfish_dir = snapshot_dir / "batfish"
        batfish_dir.mkdir(parents=True, exist_ok=True)
        l1_file = batfish_dir / "layer1_topology.json"
        l1_file.write_text(json.dumps({"edges": edges}, indent=4) + "\n")
        print(f"  Generated layer1_topology.json with {len(edges)} edges")
