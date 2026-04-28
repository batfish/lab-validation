"""SSH device interaction via netmiko."""

from __future__ import annotations

import logging
import time

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException

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
        # Containerlab containers get new host keys on each deploy.
        ssh_strict=False,
        system_host_keys=False,
        alt_host_keys=False,
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


class SshPermanentError(Exception):
    """SSH error that will not resolve by retrying (e.g., auth failure)."""


def check_ssh_reachable(node: NodeInfo, timeout: int = 10) -> bool:
    """Check if SSH is reachable on a node.

    Raises SshPermanentError for errors that won't resolve by retrying.
    """
    try:
        conn = connect(node, timeout=timeout)
        conn.disconnect()
        return True
    except NetmikoAuthenticationException as e:
        raise SshPermanentError(f"authentication failed: {e}") from e
    except Exception:
        return False


def wait_for_ssh(
    node: NodeInfo,
    timeout: int = 900,
    interval: int = 15,
    max_auth_failures: int = 5,
) -> bool:
    """Wait until SSH is reachable on a node.

    Returns True if reachable within timeout, False otherwise.
    Raises SshPermanentError if authentication fails repeatedly (more than
    *max_auth_failures* consecutive times), indicating bad credentials
    rather than a device still booting.
    """
    # Suppress paramiko's transport thread tracebacks during retries.
    # Without this, every failed SSH attempt prints a multi-line exception
    # to stderr (from paramiko's background thread), flooding the output.
    paramiko_logger = logging.getLogger("paramiko.transport")
    original_level = paramiko_logger.level
    paramiko_logger.setLevel(logging.CRITICAL)

    deadline = time.time() + timeout
    attempt = 0
    consecutive_auth_failures = 0
    try:
        while time.time() < deadline:
            attempt += 1
            try:
                if check_ssh_reachable(node, timeout=10):
                    print(f"  {node.name}: SSH reachable (attempt {attempt})")
                    return True
                consecutive_auth_failures = 0
            except SshPermanentError:
                consecutive_auth_failures += 1
                remaining = int(deadline - time.time())
                print(
                    f"  {node.name}: SSH auth failed "
                    f"(attempt {attempt}, "
                    f"{consecutive_auth_failures}/{max_auth_failures}, "
                    f"{remaining}s remaining)"
                )
                if consecutive_auth_failures >= max_auth_failures:
                    raise
                time.sleep(interval)
                continue
            remaining = int(deadline - time.time())
            print(
                f"  {node.name}: SSH not ready "
                f"(attempt {attempt}, {remaining}s remaining)"
            )
            time.sleep(interval)
        return False
    finally:
        paramiko_logger.setLevel(original_level)
