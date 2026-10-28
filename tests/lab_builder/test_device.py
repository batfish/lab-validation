"""Tests for lab_builder.device SSH waiting."""

from __future__ import annotations

import pytest

from lab_builder import device, health
from lab_builder.config import FRR
from lab_builder.device import SshConfigError, wait_for_ssh
from lab_builder.models import NodeInfo

# What netmiko 4.8 raises for use_keys=True without a key_file.
KEY_FILE_ERROR = (
    "\nuse_keys has been set to True, but specified key_file does not exist:\n\n"
    "use_keys: True\nkey_file: None\n"
)


@pytest.fixture()
def frr_node() -> NodeInfo:
    return NodeInfo(name="r0", kind="frr", profile=FRR, management_ip="1.2.3.4")


@pytest.fixture()
def bad_connect(monkeypatch) -> list[int]:
    calls: list[int] = []

    def connect(node, timeout=30):
        calls.append(timeout)
        raise ValueError(KEY_FILE_ERROR)

    monkeypatch.setattr(device, "connect", connect)
    monkeypatch.setattr(device.time, "sleep", lambda s: None)
    return calls


def test_connect_passes_key_file_for_key_profiles(monkeypatch, frr_node) -> None:
    kwargs: dict = {}
    monkeypatch.setattr(device, "ConnectHandler", lambda **kw: kwargs.update(kw))
    device.connect(frr_node)
    assert kwargs["use_keys"] is True
    assert kwargs["key_file"] == str(device.SSH_KEY_FILE)


def test_wait_for_ssh_fails_fast_on_config_error(bad_connect, frr_node) -> None:
    with pytest.raises(SshConfigError, match="key_file does not exist"):
        wait_for_ssh(frr_node, timeout=900, interval=15)
    assert len(bad_connect) == 1


def test_convergence_reports_config_error(bad_connect, frr_node) -> None:
    [status] = health.wait_for_convergence([frr_node], timeout=600)
    assert not status.healthy
    assert "key_file does not exist" in status.details
    assert len(bad_connect) == 1
