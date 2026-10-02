"""Tests for the Junos bgp_peer_bufsize check.

Fixture JSON is trimmed from `show bgp neighbor 192.0.2.1 | display json`
on vJunos-router 25.4R1.12 while building the junos_bgp_socket_buffers
lab.
"""

from __future__ import annotations

import json

import pytest

from lab_builder import validate
from lab_builder.config import VJUNOS_ROUTER
from lab_builder.models import NodeInfo


def _neighbor_json(options: dict[str, str]) -> str:
    return json.dumps(
        {
            "bgp-information": [
                {
                    "bgp-peer": [
                        {
                            "peer-address": [{"data": "192.0.2.1+42771"}],
                            "peer-state": [{"data": "Established"}],
                            "bgp-option-information": [
                                {
                                    "holdtime": [{"data": "90"}],
                                    **{k: [{"data": v}] for k, v in options.items()},
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    )


BOTH = _neighbor_json({"receive-buffer-size": "262144", "send-buffer-size": "262144"})
RECEIVE_ONLY = _neighbor_json({"receive-buffer-size": "65536"})


@pytest.fixture()
def junos_node() -> NodeInfo:
    return NodeInfo(
        name="dut",
        kind="juniper_vjunosrouter",
        profile=VJUNOS_ROUTER,
        management_ip="1.2.3.4",
    )


class TestCheckBgpPeerBufsize:
    @pytest.fixture(autouse=True)
    def _fake_device(self, monkeypatch) -> None:
        self.output = BOTH
        self.sent: list[str] = []

        def run_command(node: NodeInfo, command: str) -> str:
            self.sent.append(command)
            return self.output

        monkeypatch.setattr(validate, "run_command", run_command)

    def test_both_match(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_peer_bufsize(
            junos_node, "192.0.2.1", 262144, 262144
        )
        assert result.passed, result.detail
        assert self.sent == ["show bgp neighbor 192.0.2.1 | display json"]

    def test_size_mismatch(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_peer_bufsize(
            junos_node, "192.0.2.1", 131072, 262144
        )
        assert not result.passed

    def test_absent_field_expected_none(self, junos_node: NodeInfo) -> None:
        self.output = RECEIVE_ONLY
        result = validate._junos_check_bgp_peer_bufsize(
            junos_node, "192.0.2.1", 65536, None
        )
        assert result.passed, result.detail

    def test_absent_field_expected_value(self, junos_node: NodeInfo) -> None:
        self.output = RECEIVE_ONLY
        result = validate._junos_check_bgp_peer_bufsize(
            junos_node, "192.0.2.1", 65536, 65536
        )
        assert not result.passed

    def test_peer_not_found(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_peer_bufsize(
            junos_node, "198.51.100.1", 262144, 262144
        )
        assert not result.passed
        assert "peer not found" in result.detail
