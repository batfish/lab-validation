"""Wrapper around containerlab CLI commands."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lab_builder.config import get_profile
from lab_builder.models import NodeInfo


def deploy(topology_file: str | Path) -> list[NodeInfo]:
    """Deploy a containerlab topology and return discovered nodes."""
    topology_file = Path(topology_file)
    if not topology_file.exists():
        raise FileNotFoundError(f"Topology file not found: {topology_file}")

    result = subprocess.run(
        ["sudo", "containerlab", "deploy", "-t", str(topology_file), "--reconfigure"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"containerlab deploy failed (exit {result.returncode}):\n{result.stderr}"
        )
    print(result.stdout)

    return inspect(topology_file)


def inspect(topology_file: str | Path) -> list[NodeInfo]:
    """Inspect a running topology and return node information."""
    topology_file = Path(topology_file)

    result = subprocess.run(
        [
            "sudo",
            "containerlab",
            "inspect",
            "-t",
            str(topology_file),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"containerlab inspect failed (exit {result.returncode}):\n{result.stderr}"
        )

    # containerlab prints log lines to stdout before the JSON
    stdout = result.stdout
    json_start = stdout.find("{")
    if json_start == -1:
        json_start = stdout.find("[")
    if json_start == -1:
        raise RuntimeError(f"No JSON found in containerlab inspect output:\n{stdout}")
    data = json.loads(stdout[json_start:])

    # Output format is {"lab_name": [containers...]} — flatten all values
    if isinstance(data, dict):
        containers = []
        for value in data.values():
            if isinstance(value, list):
                containers.extend(value)
            else:
                containers.append(value)
    else:
        containers = data

    nodes = []
    for container in containers:
        kind = container.get("kind", "")
        full_name = container.get("name", "")
        lab_name = container.get("lab_name", "")
        # containerlab names are "clab-<lab_name>-<node>"; strip the prefix
        prefix = f"clab-{lab_name}-" if lab_name else ""
        if prefix and full_name.startswith(prefix):
            short_name = full_name[len(prefix) :]
        else:
            short_name = full_name

        mgmt_ip = container.get("ipv4_address", "").split("/")[0]
        if not mgmt_ip:
            mgmt_ip = container.get("management_ipv4", "").split("/")[0]

        try:
            profile = get_profile(kind)
        except ValueError:
            print(f"Skipping unsupported node kind: {kind} ({full_name})")
            continue

        nodes.append(
            NodeInfo(
                name=short_name,
                kind=kind,
                profile=profile,
                management_ip=mgmt_ip,
            )
        )

    return nodes


def destroy(topology_file: str | Path) -> None:
    """Destroy a containerlab topology."""
    topology_file = Path(topology_file)

    result = subprocess.run(
        ["sudo", "containerlab", "destroy", "-t", str(topology_file), "--cleanup"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"containerlab destroy failed (exit {result.returncode}):\n{result.stderr}"
        )
    print(result.stdout)
