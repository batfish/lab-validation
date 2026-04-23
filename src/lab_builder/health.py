"""Convergence and health checking for containerlab nodes."""

from __future__ import annotations

import json
import time

from lab_builder.device import run_command, wait_for_ssh
from lab_builder.models import HealthStatus, NodeInfo


def check_bgp_established(node: NodeInfo) -> bool | None:
    """Check if all BGP neighbors are Established. Returns None if no BGP configured."""
    try:
        output = run_command(node, "show bgp neighbor | display json")
        data = json.loads(output)
    except Exception:
        return False

    neighbors = data.get("bgp-information", [{}])
    if not neighbors:
        return None

    bgp_info = neighbors[0] if isinstance(neighbors, list) else neighbors
    peers = bgp_info.get("bgp-peer", [])
    if not peers:
        return None

    for peer in peers:
        state_entries = peer.get("peer-state", [])
        state = state_entries[0].get("data", "") if state_entries else ""
        if state != "Established":
            return False
    return True


def check_ospf_full(node: NodeInfo) -> bool | None:
    """Check if all OSPF neighbors are Full. Returns None if no OSPF configured."""
    try:
        output = run_command(node, "show ospf neighbor | display json")
        data = json.loads(output)
    except Exception:
        return False

    ospf_info = data.get("ospf-neighbor-information", [{}])
    if not ospf_info:
        return None

    info = ospf_info[0] if isinstance(ospf_info, list) else ospf_info
    neighbors = info.get("ospf-neighbor", [])
    if not neighbors:
        return None

    for nbr in neighbors:
        state_entries = nbr.get("ospf-neighbor-state", [])
        state = state_entries[0].get("data", "") if state_entries else ""
        if state != "Full":
            return False
    return True


def check_isis_up(node: NodeInfo) -> bool | None:
    """Check if all ISIS adjacencies are Up. Returns None if no ISIS configured."""
    try:
        output = run_command(node, "show isis adjacency | display json")
        data = json.loads(output)
    except Exception:
        return False

    isis_info = data.get("isis-adjacency-information", [{}])
    if not isis_info:
        return None

    info = isis_info[0] if isinstance(isis_info, list) else isis_info
    adjs = info.get("isis-adjacency", [])
    if not adjs:
        return None

    for adj in adjs:
        state_entries = adj.get("adjacency-state", [])
        state = state_entries[0].get("data", "") if state_entries else ""
        if state != "Up":
            return False
    return True


def check_platform_warnings(node: NodeInfo) -> list[str]:
    """Check for 'unsupported platform' warnings in the running config.

    Junos silently ignores config blocks that aren't supported on the
    platform (e.g., family ethernet-switching on VMX). These show up as
    '## Warning: configuration block ignored: unsupported platform'
    comments in 'show configuration'.
    """
    try:
        output = run_command(node, "show configuration")
    except Exception:
        return []
    warnings = []
    for line in output.splitlines():
        if "unsupported platform" in line.lower():
            warnings.append(line.strip())
    return warnings


def check_node_health(node: NodeInfo) -> HealthStatus:
    """Run all health checks on a single node."""
    status = HealthStatus(node=node.name)

    status.ssh_reachable = wait_for_ssh(node, timeout=10, interval=5)
    if not status.ssh_reachable:
        status.details = "SSH not reachable"
        return status

    status.bgp_established = check_bgp_established(node)
    status.ospf_full = check_ospf_full(node)
    status.isis_up = check_isis_up(node)

    parts = []
    if status.bgp_established is not None:
        parts.append(f"BGP={'up' if status.bgp_established else 'NOT established'}")
    if status.ospf_full is not None:
        parts.append(f"OSPF={'Full' if status.ospf_full else 'NOT Full'}")
    if status.isis_up is not None:
        parts.append(f"ISIS={'Up' if status.isis_up else 'NOT Up'}")
    if not parts:
        parts.append("no routing protocols detected")
    status.details = ", ".join(parts)

    return status


def wait_for_convergence(
    nodes: list[NodeInfo],
    timeout: int = 600,
    interval: int = 20,
) -> list[HealthStatus]:
    """Wait for all nodes to boot and routing protocols to converge.

    First waits for SSH on all nodes, then polls protocol status.
    """
    print("Waiting for SSH on all nodes...")
    boot_timeout = max(n.profile.boot_timeout_seconds for n in nodes)
    for node in nodes:
        if not wait_for_ssh(node, timeout=boot_timeout, interval=15):
            print(f"  {node.name}: TIMEOUT waiting for SSH")
            return [HealthStatus(node=n.name, details="SSH timeout") for n in nodes]

    print("All nodes reachable. Waiting for routing protocol convergence...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = [check_node_health(node) for node in nodes]
        all_healthy = all(s.healthy for s in statuses)

        for s in statuses:
            print(f"  {s.node}: {'OK' if s.healthy else 'WAITING'} - {s.details}")

        if all_healthy:
            print("All nodes converged. Checking for platform warnings...")
            for node, s in zip(nodes, statuses):
                s.platform_warnings = check_platform_warnings(node)
                for w in s.platform_warnings:
                    print(f"  WARNING {s.node}: {w}")
            return statuses

        remaining = int(deadline - time.time())
        print(f"  Retrying in {interval}s ({remaining}s remaining)...")
        time.sleep(interval)

    print("Convergence timeout reached.")
    return [check_node_health(node) for node in nodes]
