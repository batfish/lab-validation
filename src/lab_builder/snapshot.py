"""Package collected data into a lab-validation snapshot."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from lab_builder.config import command_to_filename
from lab_builder.models import NodeInfo


def build_snapshot(
    name: str,
    nodes: list[NodeInfo],
    collected_dir: Path,
    snapshots_dir: Path,
) -> Path:
    """Build a lab-validation snapshot from collected data.

    Creates the standard directory structure:
        snapshots/<name>/
        ├── configs/<hostname>/show_configuration_|_display_set.txt
        ├── show/host_nos.txt
        ├── show/<hostname>/<show_command>.txt
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

    print(f"Snapshot created at: {snapshot_dir}")
    return snapshot_dir
