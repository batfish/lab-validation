"""Collect show command outputs from containerlab nodes."""

from __future__ import annotations

from pathlib import Path

from lab_builder.config import command_to_filename
from lab_builder.device import run_command
from lab_builder.models import CollectedData, NodeInfo


def collect_node(node: NodeInfo, output_dir: Path) -> CollectedData:
    """Collect all show commands from a single node.

    Saves each command output to a file matching the lab-validation naming convention.
    """
    node_dir = output_dir / node.name
    node_dir.mkdir(parents=True, exist_ok=True)

    result = CollectedData(node=node.name, output_dir=node_dir)

    for command in node.profile.show_commands:
        filename = command_to_filename(command)
        filepath = node_dir / filename

        try:
            output = run_command(node, command, timeout=60)
            filepath.write_text(output)
            result.files.append(filename)
            print(f"  {node.name}: collected {filename}")
        except Exception as e:
            error_msg = f"{command}: {e}"
            result.errors.append(error_msg)
            print(f"  {node.name}: FAILED {filename} - {e}")

    return result


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
