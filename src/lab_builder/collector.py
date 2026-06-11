"""Collect show command outputs from containerlab nodes."""

from __future__ import annotations

import json
from pathlib import Path

from lab_builder.config import DynamicCommandGroup, command_to_filename
from lab_builder.device import run_command
from lab_builder.models import CollectedData, NodeInfo


def collect_node(node: NodeInfo, output_dir: Path) -> CollectedData:
    """Collect all show commands from a single node.

    Saves each command output to a file matching the lab-validation naming convention.
    First runs the profile's static ``show_commands``, then expands any
    ``dynamic_command_groups`` (device-driven per-instance state, e.g. SR OS
    VPRNs) into concrete commands and collects those too.
    """
    node_dir = output_dir / node.name
    node_dir.mkdir(parents=True, exist_ok=True)

    result = CollectedData(node=node.name, output_dir=node_dir)

    for command in node.profile.show_commands:
        _collect_command(node, node_dir, command, result)

    for group in node.profile.dynamic_command_groups:
        for command in _expand_dynamic_group(node, group, result):
            _collect_command(node, node_dir, command, result)

    return result


def _collect_command(
    node: NodeInfo, node_dir: Path, command: str, result: CollectedData
) -> str | None:
    """Run one command, write its output, and record it. Returns the output."""
    filename = command_to_filename(command)
    filepath = node_dir / filename
    try:
        output = run_command(node, command, timeout=60)
        filepath.write_text(output)
        result.files.append(filename)
        print(f"  {node.name}: collected {filename}")
        return output
    except Exception as e:
        error_msg = f"{command}: {e}"
        result.errors.append(error_msg)
        print(f"  {node.name}: FAILED {filename} - {e}")
        return None


def _expand_dynamic_group(
    node: NodeInfo, group: DynamicCommandGroup, result: CollectedData
) -> list[str]:
    """Run a group's discovery command and expand its templates per instance.

    The discovery command's output is saved like any other (so the raw
    enumeration is part of the snapshot), then parsed for instance names. Each
    name is substituted into every command template. A discovery failure or an
    empty/unparseable result yields no expanded commands -- a node with no such
    instances simply collects nothing extra.
    """
    node_dir = result.output_dir
    output = _collect_command(node, node_dir, group.discovery_command, result)
    if output is None:
        return []

    names = _parse_instance_names(output, group)
    if names:
        print(f"  {node.name}: discovered {group.discovery_json_key} {names}")

    commands: list[str] = []
    for name in names:
        for template in group.command_templates:
            commands.append(template.format(name=name))
    return commands


def _parse_instance_names(output: str, group: DynamicCommandGroup) -> list[str]:
    """Extract instance names from a discovery command's JSON output."""
    try:
        obj = json.loads(output)
    except json.JSONDecodeError:
        return []
    entries = obj.get(group.discovery_json_key, []) if isinstance(obj, dict) else []
    names: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and group.name_field in entry:
            names.append(entry[group.name_field])
    return names


def collect_all(nodes: list[NodeInfo], output_dir: Path) -> list[CollectedData]:
    """Collect show commands from all nodes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Collecting show commands into {output_dir}/")

    results = []
    for node in nodes:
        print(f"Collecting from {node.name} ({node.management_ip})...")
        result = collect_node(node, output_dir)
        results.append(result)

    total_files = sum(len(r.files) for r in results)
    total_errors = sum(len(r.errors) for r in results)
    print(f"Collection complete: {total_files} files, {total_errors} errors")

    return results
