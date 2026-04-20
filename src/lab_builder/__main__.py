"""CLI entry point for lab_builder: python -m lab_builder <subcommand>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lab_builder import containerlab as clab
from lab_builder.collector import collect_all, collect_node
from lab_builder.device import push_config as device_push_config
from lab_builder.health import wait_for_convergence
from lab_builder.snapshot import build_snapshot


def cmd_deploy(args: argparse.Namespace) -> None:
    nodes = clab.deploy(args.topology)
    print(f"\nDeployed {len(nodes)} nodes:")
    for n in nodes:
        print(f"  {n.name}: {n.kind} @ {n.management_ip}")


def cmd_inspect(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    print(f"{len(nodes)} nodes:")
    for n in nodes:
        print(f"  {n.name}: {n.kind} @ {n.management_ip}")


def cmd_health_check(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    statuses = wait_for_convergence(nodes, timeout=args.timeout)
    all_ok = all(s.healthy for s in statuses)
    for s in statuses:
        marker = "OK" if s.healthy else "FAIL"
        print(f"  {s.node}: [{marker}] {s.details}")
    if not all_ok:
        sys.exit(1)


def cmd_collect(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    output_dir = Path(args.output_dir)
    collect_all(nodes, output_dir)


def cmd_recollect(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    output_dir = Path(args.output_dir)
    matches = [n for n in nodes if n.name == args.node]
    if not matches:
        names = [n.name for n in nodes]
        print(f"Error: node '{args.node}' not found. Available: {names}")
        sys.exit(1)
    collect_node(matches[0], output_dir)


def cmd_push_config(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    matches = [n for n in nodes if n.name == args.node]
    if not matches:
        names = [n.name for n in nodes]
        print(f"Error: node '{args.node}' not found. Available: {names}")
        sys.exit(1)

    config_path = Path(args.config_file)
    config_lines = config_path.read_text().strip().splitlines()
    print(f"Pushing {len(config_lines)} config lines to {args.node}...")
    output = device_push_config(matches[0], config_lines)
    print(output)


def cmd_build_snapshot(args: argparse.Namespace) -> None:
    nodes = clab.inspect(args.topology)
    build_snapshot(
        name=args.name,
        nodes=nodes,
        collected_dir=Path(args.collected_dir),
        snapshots_dir=Path(args.snapshots_dir),
    )


def cmd_destroy(args: argparse.Namespace) -> None:
    clab.destroy(args.topology)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lab_builder",
        description="Build lab-validation snapshots using containerlab",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # deploy
    p = sub.add_parser("deploy", help="Deploy a containerlab topology")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.set_defaults(func=cmd_deploy)

    # inspect
    p = sub.add_parser("inspect", help="Inspect running topology")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.set_defaults(func=cmd_inspect)

    # health-check
    p = sub.add_parser("health-check", help="Wait for convergence")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    p.set_defaults(func=cmd_health_check)

    # collect
    p = sub.add_parser("collect", help="Collect show commands from all nodes")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.add_argument("--output-dir", required=True, help="Directory for collected data")
    p.set_defaults(func=cmd_collect)

    # recollect
    p = sub.add_parser("recollect", help="Re-collect show commands from one node")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.add_argument("node", help="Node name to recollect")
    p.add_argument("--output-dir", required=True, help="Directory for collected data")
    p.set_defaults(func=cmd_recollect)

    # push-config
    p = sub.add_parser("push-config", help="Push config to a node")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.add_argument("node", help="Node name")
    p.add_argument("config_file", help="File with set-format config lines")
    p.set_defaults(func=cmd_push_config)

    # build-snapshot
    p = sub.add_parser("build-snapshot", help="Package collected data as snapshot")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.add_argument("--name", required=True, help="Snapshot name")
    p.add_argument("--collected-dir", required=True, help="Collected data directory")
    p.add_argument(
        "--snapshots-dir",
        default="snapshots",
        help="Snapshots directory (default: snapshots)",
    )
    p.set_defaults(func=cmd_build_snapshot)

    # destroy
    p = sub.add_parser("destroy", help="Destroy a containerlab topology")
    p.add_argument("topology", help="Path to .clab.yml file")
    p.set_defaults(func=cmd_destroy)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
