"""SSH device interaction via netmiko."""

from __future__ import annotations

import time

from netmiko import ConnectHandler  # type: ignore[import-untyped,import-not-found]

from lab_builder.models import NodeInfo


def connect(node: NodeInfo, timeout: int = 30) -> ConnectHandler:
    """Create a netmiko SSH connection to a node."""
    return ConnectHandler(
        device_type=node.profile.netmiko_device_type,
        host=node.management_ip,
        port=node.ssh_port,
        username=node.username,
        password=node.password,
        timeout=timeout,
        session_timeout=120,
    )


def run_command(node: NodeInfo, command: str, timeout: int = 60) -> str:
    """Run a single command on a node and return the output."""
    conn = connect(node)
    try:
        output: str = conn.send_command(command, read_timeout=timeout)
        return output
    finally:
        conn.disconnect()


def push_config(node: NodeInfo, config_lines: list[str]) -> str:
    """Push configuration lines (set format) to a Junos device and commit.

    Returns the commit output.
    """
    conn = connect(node)
    try:
        conn.config_mode()
        for line in config_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            conn.send_command_timing(stripped)
        output: str = conn.send_command_timing("commit")
        conn.exit_config_mode()
        return output
    finally:
        conn.disconnect()


def check_ssh_reachable(node: NodeInfo, timeout: int = 10) -> bool:
    """Check if SSH is reachable on a node."""
    try:
        conn = connect(node, timeout=timeout)
        conn.disconnect()
        return True
    except Exception:
        return False


def wait_for_ssh(node: NodeInfo, timeout: int = 900, interval: int = 15) -> bool:
    """Wait until SSH is reachable on a node.

    Returns True if reachable within timeout, False otherwise.
    """
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        if check_ssh_reachable(node, timeout=10):
            print(f"  {node.name}: SSH reachable (attempt {attempt})")
            return True
        remaining = int(deadline - time.time())
        print(
            f"  {node.name}: SSH not ready (attempt {attempt}, {remaining}s remaining)"
        )
        time.sleep(interval)
    return False
