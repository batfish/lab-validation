"""Topology-level validation checks for containerlab labs.

Runs after health-check (routing protocol convergence) to verify that the lab
is actually demonstrating the intended behavior before collection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

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


def check_interface_up(node: NodeInfo, interface: str) -> CheckResult:
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


def check_route_exists(node: NodeInfo, table: str, prefix: str) -> CheckResult:
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


def check_bgp_peer_established(node: NodeInfo, neighbor: str) -> CheckResult:
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
        # Junos sometimes appends +port to the address
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


CHECK_FUNCTIONS = {
    "interface_up": lambda node, spec: check_interface_up(node, spec["interface"]),
    "route_exists": lambda node, spec: check_route_exists(
        node, spec["table"], spec["prefix"]
    ),
    "bgp_peer_established": lambda node, spec: check_bgp_peer_established(
        node, spec["neighbor"]
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
