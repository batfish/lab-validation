"""Topology-level validation checks for containerlab labs.

Runs after health-check (routing protocol convergence) to verify that the lab
is actually demonstrating the intended behavior before collection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from lab_builder.device import run_command
from lab_builder.models import NodeInfo


@dataclass
class CheckResult:
    """Result of a single validation check."""

    check_type: str
    node: str
    passed: bool
    detail: str
    description: str = ""


def load_checks(checks_path: Path) -> list[dict[str, Any]]:
    """Load checks from a YAML file."""
    data = yaml.safe_load(checks_path.read_text())
    checks: list[dict[str, Any]] = data.get("checks", [])
    return checks


def _find_node(nodes: list[NodeInfo], name: str) -> NodeInfo | None:
    for n in nodes:
        if n.name == name:
            return n
    return None


# ---------------------------------------------------------------------------
# Junos checks
# ---------------------------------------------------------------------------


def _junos_check_interface_up(node: NodeInfo, interface: str) -> CheckResult:
    """Check that an interface is operationally up with no hardware-down flag.

    For logical interfaces (e.g., irb.100), checks the parent physical
    interface for oper-status and the logical unit for iff-hardware-down.
    """
    parts = interface.split(".")
    phys_name = parts[0]
    unit = parts[1] if len(parts) > 1 else None

    try:
        output = run_command(node, f"show interfaces {phys_name} | display json")
        data = json.loads(output)
    except Exception as e:
        return CheckResult("interface_up", node.name, False, f"command failed: {e}")

    phys_list = data.get("interface-information", [{}])[0].get("physical-interface", [])
    if not phys_list:
        return CheckResult(
            "interface_up", node.name, False, f"{phys_name}: not found in output"
        )

    phys = phys_list[0]
    oper = phys.get("oper-status", [{}])[0].get("data", "")
    if oper != "up":
        return CheckResult(
            "interface_up", node.name, False, f"{phys_name}: oper-status={oper}"
        )

    if unit is None:
        return CheckResult(
            "interface_up", node.name, True, f"{phys_name}: oper-status=up"
        )

    for li in phys.get("logical-interface", []):
        li_name = li.get("name", [{}])[0].get("data", "")
        if li_name == interface:
            flags = li.get("if-config-flags", [{}])
            if isinstance(flags, list):
                flags = flags[0] if flags else {}
            if "iff-hardware-down" in flags:
                return CheckResult(
                    "interface_up",
                    node.name,
                    False,
                    f"{interface}: iff-hardware-down",
                )
            return CheckResult(
                "interface_up", node.name, True, f"{interface}: up, no hardware-down"
            )

    return CheckResult(
        "interface_up", node.name, False, f"{interface}: logical unit not found"
    )


def _junos_check_route_exists(node: NodeInfo, table: str, prefix: str) -> CheckResult:
    """Check that a route exists in a specific routing table."""
    try:
        output = run_command(
            node, f"show route table {table} {prefix} exact | display json"
        )
        data = json.loads(output)
    except Exception as e:
        return CheckResult("route_exists", node.name, False, f"command failed: {e}")

    tables = data.get("route-information", [{}])[0].get("route-table", [])
    for t in tables:
        tname = t.get("table-name", [{}])[0].get("data", "")
        if tname == table:
            routes = t.get("rt", [])
            if routes:
                return CheckResult(
                    "route_exists",
                    node.name,
                    True,
                    f"{prefix} in {table}: found ({len(routes)} entries)",
                )

    return CheckResult(
        "route_exists", node.name, False, f"{prefix} in {table}: not found"
    )


def _junos_check_bgp_peer(node: NodeInfo, neighbor: str) -> CheckResult:
    """Check that a specific BGP peer is in Established state."""
    try:
        output = run_command(node, "show bgp neighbor | display json")
        data = json.loads(output)
    except Exception as e:
        return CheckResult(
            "bgp_peer_established", node.name, False, f"command failed: {e}"
        )

    for peer in data.get("bgp-information", [{}])[0].get("bgp-peer", []):
        addr = peer.get("peer-address", [{}])[0].get("data", "")
        addr_clean = addr.split("+")[0]
        if addr_clean == neighbor:
            state = peer.get("peer-state", [{}])[0].get("data", "")
            if state == "Established":
                return CheckResult(
                    "bgp_peer_established",
                    node.name,
                    True,
                    f"{neighbor}: Established",
                )
            return CheckResult(
                "bgp_peer_established",
                node.name,
                False,
                f"{neighbor}: {state}",
            )

    return CheckResult(
        "bgp_peer_established", node.name, False, f"{neighbor}: peer not found"
    )


# ---------------------------------------------------------------------------
# Arista EOS checks
# ---------------------------------------------------------------------------


def _arista_check_interface_up(node: NodeInfo, interface: str) -> CheckResult:
    """Check that an interface is operationally up on Arista EOS."""
    try:
        output = run_command(node, f"show interfaces {interface} | json")
        data = json.loads(output)
    except Exception as e:
        return CheckResult("interface_up", node.name, False, f"command failed: {e}")

    interfaces = data.get("interfaces", {})
    if interface not in interfaces:
        return CheckResult(
            "interface_up", node.name, False, f"{interface}: not found in output"
        )

    intf = interfaces[interface]
    line_status = intf.get("lineProtocolStatus", "")
    intf_status = intf.get("interfaceStatus", "")
    if line_status == "up" and intf_status == "connected":
        return CheckResult(
            "interface_up", node.name, True, f"{interface}: connected/up"
        )
    return CheckResult(
        "interface_up",
        node.name,
        False,
        f"{interface}: interfaceStatus={intf_status}, lineProtocol={line_status}",
    )


def _arista_check_route_exists(node: NodeInfo, table: str, prefix: str) -> CheckResult:
    """Check that a route exists in a VRF routing table on Arista EOS.

    The 'table' parameter uses Junos-style names (e.g., 'Tenant_A.inet.0').
    For Arista, we extract the VRF name (part before '.inet.0') and query
    'show ip route vrf <vrf> <prefix> | json'.
    """
    vrf = table.split(".")[0] if "." in table else table
    try:
        output = run_command(node, f"show ip route vrf {vrf} {prefix} | json")
        data = json.loads(output)
    except Exception as e:
        return CheckResult("route_exists", node.name, False, f"command failed: {e}")

    vrfs = data.get("vrfs", {})
    vrf_info = vrfs.get(vrf, {})
    routes = vrf_info.get("routes", {})
    if prefix in routes:
        return CheckResult("route_exists", node.name, True, f"{prefix} in {vrf}: found")

    return CheckResult(
        "route_exists", node.name, False, f"{prefix} in {vrf}: not found"
    )


def _arista_check_bgp_peer(node: NodeInfo, neighbor: str) -> CheckResult:
    """Check that a specific BGP peer is in Established state on Arista EOS."""
    try:
        output = run_command(node, "show ip bgp summary | json")
        data = json.loads(output)
    except Exception as e:
        return CheckResult(
            "bgp_peer_established", node.name, False, f"command failed: {e}"
        )

    for vrf_info in data.get("vrfs", {}).values():
        peers = vrf_info.get("peers", {})
        if neighbor in peers:
            state = peers[neighbor].get("peerState", "")
            if state == "Established":
                return CheckResult(
                    "bgp_peer_established",
                    node.name,
                    True,
                    f"{neighbor}: Established",
                )
            return CheckResult(
                "bgp_peer_established",
                node.name,
                False,
                f"{neighbor}: {state}",
            )

    return CheckResult(
        "bgp_peer_established", node.name, False, f"{neighbor}: peer not found"
    )


# ---------------------------------------------------------------------------
# Junos commit check validation
# ---------------------------------------------------------------------------


def _junos_commit_check(node: NodeInfo, config_lines: list[str]) -> tuple[bool, str]:
    """Load config lines on a Junos device and run 'commit check'.

    Returns (success, output) where success is True if commit check passes.
    Always rolls back after the check so the device stays clean.
    """
    from lab_builder.device import connect

    conn = connect(node)
    try:
        conn.config_mode()
        for line in config_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            conn.send_command_timing(stripped)
        output: str = conn.send_command_timing("commit check")
        conn.send_command_timing("rollback 0")
        conn.exit_config_mode()

        success = "configuration check succeeds" in output.lower()
        return success, output.strip()
    except Exception as e:
        try:
            conn.send_command_timing("rollback 0")
            conn.exit_config_mode()
        except Exception:
            pass
        return False, f"exception: {e}"
    finally:
        conn.disconnect()


def _check_commit_rejects(
    node: NodeInfo, config_lines: list[str], expected_error: str | None
) -> CheckResult:
    """Verify that Junos rejects the given config lines at commit check."""
    success, output = _junos_commit_check(node, config_lines)
    if success:
        return CheckResult(
            "commit_check_rejects",
            node.name,
            False,
            f"expected rejection but commit check succeeded: {output}",
        )
    if expected_error and expected_error.lower() not in output.lower():
        return CheckResult(
            "commit_check_rejects",
            node.name,
            False,
            f"rejected but error text '{expected_error}' not found in: {output}",
        )
    return CheckResult(
        "commit_check_rejects",
        node.name,
        True,
        f"correctly rejected: {output[:120]}",
    )


def _check_commit_accepts(node: NodeInfo, config_lines: list[str]) -> CheckResult:
    """Verify that Junos accepts the given config lines at commit check."""
    success, output = _junos_commit_check(node, config_lines)
    if success:
        return CheckResult(
            "commit_check_accepts",
            node.name,
            True,
            "commit check succeeded",
        )
    return CheckResult(
        "commit_check_accepts",
        node.name,
        False,
        f"expected acceptance but commit check failed: {output}",
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def check_interface_up(node: NodeInfo, interface: str) -> CheckResult:
    if node.profile.name == "arista":
        return _arista_check_interface_up(node, interface)
    return _junos_check_interface_up(node, interface)


def check_route_exists(node: NodeInfo, table: str, prefix: str) -> CheckResult:
    if node.profile.name == "arista":
        return _arista_check_route_exists(node, table, prefix)
    return _junos_check_route_exists(node, table, prefix)


def check_bgp_peer_established(node: NodeInfo, neighbor: str) -> CheckResult:
    if node.profile.name == "arista":
        return _arista_check_bgp_peer(node, neighbor)
    return _junos_check_bgp_peer(node, neighbor)


CHECK_FUNCTIONS = {
    "interface_up": lambda node, spec: check_interface_up(node, spec["interface"]),
    "route_exists": lambda node, spec: check_route_exists(
        node, spec["table"], spec["prefix"]
    ),
    "bgp_peer_established": lambda node, spec: check_bgp_peer_established(
        node, spec["neighbor"]
    ),
    "commit_check_rejects": lambda node, spec: _check_commit_rejects(
        node, spec["config_lines"], spec.get("expected_error")
    ),
    "commit_check_accepts": lambda node, spec: _check_commit_accepts(
        node, spec["config_lines"]
    ),
}


def run_checks(
    nodes: list[NodeInfo], checks: list[dict[str, Any]]
) -> list[CheckResult]:
    """Run all checks and return results."""
    results = []
    for spec in checks:
        check_type = spec["type"]
        node_name = spec["node"]
        description = spec.get("description", "")

        node = _find_node(nodes, node_name)
        if node is None:
            results.append(CheckResult(check_type, node_name, False, "node not found"))
            continue

        fn = CHECK_FUNCTIONS.get(check_type)
        if fn is None:
            results.append(
                CheckResult(
                    check_type, node_name, False, f"unknown check type: {check_type}"
                )
            )
            continue

        result = fn(node, spec)
        result.description = description
        results.append(result)

    return results
