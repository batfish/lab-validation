"""Convergence and health checking for containerlab nodes."""

from __future__ import annotations

import json
import re
import time

from lab_builder.device import SshPermanentError, run_command, wait_for_ssh
from lab_builder.models import HealthStatus, NodeInfo

# ---------------------------------------------------------------------------
# Junos health checks
# ---------------------------------------------------------------------------


def _junos_check_bgp(node: NodeInfo) -> bool | None:
    """Check if all BGP neighbors are Established. Returns None if no BGP configured."""
    try:
        output = run_command(node, "show bgp neighbor | display json", timeout=10)
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


def _junos_check_ospf(node: NodeInfo) -> bool | None:
    """Check if all OSPF neighbors are Full. Returns None if no OSPF configured."""
    try:
        output = run_command(node, "show ospf neighbor | display json", timeout=10)
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


def _junos_check_isis(node: NodeInfo) -> bool | None:
    """Check if all ISIS adjacencies are Up. Returns None if no ISIS configured."""
    try:
        output = run_command(node, "show isis adjacency | display json", timeout=10)
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


def _junos_check_platform_warnings(node: NodeInfo) -> list[str]:
    """Check for 'unsupported platform' warnings in the running config.

    Junos silently ignores config blocks that aren't supported on the
    platform (e.g., family ethernet-switching on VMX). These show up as
    '## Warning: configuration block ignored: unsupported platform'
    comments in 'show configuration'.
    """
    try:
        output = run_command(node, "show configuration", timeout=10)
    except Exception:
        return []
    warnings = []
    for line in output.splitlines():
        if "unsupported platform" in line.lower():
            warnings.append(line.strip())
    return warnings


# ---------------------------------------------------------------------------
# Arista EOS health checks
# ---------------------------------------------------------------------------


def _arista_check_bgp(node: NodeInfo) -> bool | None:
    """Check if all BGP peers are Established via 'show ip bgp summary | json'."""
    try:
        output = run_command(node, "show ip bgp summary | json", timeout=10)
        data = json.loads(output)
    except Exception:
        return False

    vrfs = data.get("vrfs", {})
    if not vrfs:
        return None

    found_any = False
    for vrf_info in vrfs.values():
        peers = vrf_info.get("peers", {})
        for peer_info in peers.values():
            found_any = True
            state = peer_info.get("peerState", "")
            if state != "Established":
                return False

    return True if found_any else None


def _arista_check_ospf(node: NodeInfo) -> bool | None:
    """Check if all OSPF neighbors are full via 'show ip ospf neighbor | json'."""
    try:
        output = run_command(node, "show ip ospf neighbor | json", timeout=10)
        data = json.loads(output)
    except Exception:
        return False

    vrfs = data.get("vrfs", {})
    if not vrfs:
        return None

    found_any = False
    for vrf_info in vrfs.values():
        for inst in vrf_info.get("instList", {}).values():
            neighbors = inst.get("ospfNeighborEntries", [])
            for nbr in neighbors:
                found_any = True
                state = nbr.get("adjacencyState", "")
                if state != "full":
                    return False

    return True if found_any else None


def _arista_check_isis(node: NodeInfo) -> bool | None:
    """Check if all ISIS adjacencies are up via 'show isis neighbors | json'."""
    try:
        output = run_command(node, "show isis neighbors | json", timeout=10)
        data = json.loads(output)
    except Exception:
        return False

    vrfs = data.get("vrfs", {})
    if not vrfs:
        return None

    found_any = False
    for vrf_info in vrfs.values():
        for inst in vrf_info.get("isisInstances", {}).values():
            neighbors = inst.get("neighbors", {})
            for nbr_list in neighbors.values():
                for adj in nbr_list.get("adjacencies", []):
                    found_any = True
                    state = adj.get("state", "")
                    if state != "up":
                        return False

    return True if found_any else None


# ---------------------------------------------------------------------------
# NX-OS health checks
# ---------------------------------------------------------------------------


def _nxos_check_bgp(node: NodeInfo) -> bool | None:
    """Check if all BGP neighbors are Established via 'show ip bgp summary'."""
    try:
        output = run_command(node, "show ip bgp summary", timeout=10)
    except Exception:
        return False

    # NX-OS text output: lines with neighbor IPs have state in last column.
    # If numeric, it's a prefix count (Established). Otherwise it's a state name.
    found_any = False
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        # Neighbor lines start with an IP address
        first = parts[0]
        if not all(c.isdigit() or c == "." for c in first) or first.count(".") != 3:
            continue
        found_any = True
        state = parts[-1]
        # A numeric last field means prefix count -> Established
        if not state.isdigit():
            return False

    return True if found_any else None


def _nxos_check_ospf(node: NodeInfo) -> bool | None:
    """Check if all OSPF neighbors are FULL via 'show ip ospf neighbors'."""
    try:
        output = run_command(node, "show ip ospf neighbors", timeout=10)
    except Exception:
        return False

    found_any = False
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        first = parts[0]
        if not all(c.isdigit() or c == "." for c in first) or first.count(".") != 3:
            continue
        found_any = True
        # State field is typically column index 2 (e.g., "FULL/  -" or "FULL/DR")
        state_col = parts[2] if len(parts) > 2 else ""
        if not state_col.upper().startswith("FULL"):
            return False

    return True if found_any else None


# ---------------------------------------------------------------------------
# Nokia SR OS health checks
#
# SR OS MD-CLI does not support "| display json"; these parse the text output
# of the standard show commands. The BGP summary format is verified against a
# running SR-SIM; OSPF/ISIS parsing follows the documented column formats and
# is refined when a lab exercises those protocols. On unexpected output the
# checks return False (not converged), keeping the poller waiting.
# ---------------------------------------------------------------------------

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _sros_check_bgp(node: NodeInfo) -> bool | None:
    """Check if all BGP neighbors are Established via 'show router bgp summary'.

    SR OS prints each neighbor across two lines: the peer address alone, then a
    line ending in the ``State|Rcv/Act/Sent`` column. An established peer shows
    prefix counts like ``1/1/1`` (optionally followed by ``(IPv4)``); a
    non-established peer shows a state word (``Active``, ``Connect``, etc.).
    """
    try:
        output = run_command(node, "show router bgp summary", timeout=10)
    except Exception:
        return False

    if "BGP is not configured" in output:
        return None

    lines = output.splitlines()
    states: list[str] = []
    for i, line in enumerate(lines):
        if not _IPV4_RE.match(line.strip()):
            continue
        for follow in lines[i + 1 :]:
            tokens = follow.split()
            if not tokens:
                continue
            if tokens[-1].startswith("(") and len(tokens) > 1:
                tokens = tokens[:-1]
            states.append(tokens[-1])
            break

    if not states:
        return None
    for state in states:
        established = "/" in state and all(p.isdigit() for p in state.split("/"))
        if not established:
            return False
    return True


def _sros_check_ospf(node: NodeInfo) -> bool | None:
    """Check if all OSPF neighbors are Full via 'show router ospf neighbor'.

    The neighbor table has a State column whose value is ``Full`` when adjacent.
    """
    try:
        output = run_command(node, "show router ospf neighbor", timeout=10)
    except Exception:
        return False

    found_any = False
    for line in output.splitlines():
        tokens = line.split()
        # Neighbor rows start with the neighbor's router-id (an IP address).
        if not tokens or not _IPV4_RE.match(tokens[0]):
            continue
        found_any = True
        if not any(t.lower().startswith("full") for t in tokens):
            return False
    return True if found_any else None


def _sros_check_isis(node: NodeInfo) -> bool | None:
    """Check if all ISIS adjacencies are Up via 'show router isis adjacency'.

    The adjacency table has a State column whose value is ``Up`` when adjacent.
    """
    try:
        output = run_command(node, "show router isis adjacency", timeout=10)
    except Exception:
        return False

    found_any = False
    for line in output.splitlines():
        tokens = line.split()
        if len(tokens) < 2:
            continue
        # Adjacency rows contain a State token of "Up"/"Down"; skip headers.
        lowered = [t.lower() for t in tokens]
        if "up" in lowered:
            found_any = True
            continue
        if "down" in lowered:
            return False
    return True if found_any else None


# ---------------------------------------------------------------------------
# Dispatch by vendor
# ---------------------------------------------------------------------------


def check_bgp_established(node: NodeInfo) -> bool | None:
    if node.profile.name == "arista":
        return _arista_check_bgp(node)
    if node.profile.name == "nx":
        return _nxos_check_bgp(node)
    if node.profile.name == "sros":
        return _sros_check_bgp(node)
    return _junos_check_bgp(node)


def check_ospf_full(node: NodeInfo) -> bool | None:
    if node.profile.name == "arista":
        return _arista_check_ospf(node)
    if node.profile.name == "nx":
        return _nxos_check_ospf(node)
    if node.profile.name == "sros":
        return _sros_check_ospf(node)
    return _junos_check_ospf(node)


def check_isis_up(node: NodeInfo) -> bool | None:
    if node.profile.name == "arista":
        return _arista_check_isis(node)
    if node.profile.name == "nx":
        return None
    if node.profile.name == "sros":
        return _sros_check_isis(node)
    return _junos_check_isis(node)


def check_platform_warnings(node: NodeInfo) -> list[str]:
    if node.profile.name in ("arista", "nx", "sros"):
        return []
    return _junos_check_platform_warnings(node)


# ---------------------------------------------------------------------------
# Orchestration (unchanged)
# ---------------------------------------------------------------------------


def check_node_health(node: NodeInfo) -> HealthStatus:
    """Run all health checks on a single node."""
    status = HealthStatus(node=node.name)

    try:
        status.ssh_reachable = wait_for_ssh(node, timeout=10, interval=5)
    except SshPermanentError:
        status.ssh_reachable = False
        status.details = "SSH authentication failed"
        return status
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
        try:
            if not wait_for_ssh(node, timeout=boot_timeout, interval=15):
                print(f"  {node.name}: TIMEOUT waiting for SSH")
                return [HealthStatus(node=n.name, details="SSH timeout") for n in nodes]
        except SshPermanentError:
            print(f"  {node.name}: SSH authentication failed persistently")
            return [HealthStatus(node=n.name, details="SSH auth failed") for n in nodes]

    print("All nodes reachable. Waiting for routing protocol convergence...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = []
        for node in nodes:
            print(f"  Checking {node.name}...", end="", flush=True)
            s = check_node_health(node)
            print(f" {'OK' if s.healthy else 'WAITING'} - {s.details}")
            statuses.append(s)
        all_healthy = all(s.healthy for s in statuses)

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
