"""Tests for the Junos bgp_active_path check.

The JSON is `show route table KNOB.inet.0 203.0.113.0/24 exact detail |
display json` from vJunos-router 25.4R1.12 while building the
junos_bgp_cluster_length_before_originator_id lab, pruned to the keys
the parser reads.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from lab_builder import validate
from lab_builder.config import VJUNOS_ROUTER
from lab_builder.models import NodeInfo


def _entry(
    active: bool, originator: str, clusters: str, reason: str | None
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "active-tag": [{"data": "*"}] if active else [{}],
        "protocol-name": [{"data": "BGP"}],
        "bgp-path-attributes": [
            {
                "attr-cluster-list": [{"attr-value": [{"data": clusters}]}],
                "attr-originator-id": [{"attr-value": [{"data": originator}]}],
            }
        ],
    }
    if reason is not None:
        entry["inactive-reason"] = [{"data": reason}]
    return entry


ROUTE_JSON = {
    "route-information": [
        {
            "route-table": [
                {
                    "table-name": [{"data": "KNOB.inet.0"}],
                    "rt": [
                        {
                            "rt-destination": [{"data": "203.0.113.0"}],
                            "rt-entry": [
                                _entry(True, "10.255.0.9", " 10.255.1.2", None),
                                _entry(
                                    False,
                                    "10.255.0.1",
                                    " 10.255.1.3 10.255.1.4",
                                    "Not Best in its group - Cluster list length",
                                ),
                            ],
                        }
                    ],
                }
            ]
        }
    ]
}


class TestParseBgpPaths:
    def test_paths(self) -> None:
        assert validate.parse_junos_bgp_paths(ROUTE_JSON, "KNOB.inet.0") == [
            validate.JunosBgpPath(True, "10.255.0.9", ["10.255.1.2"], None),
            validate.JunosBgpPath(
                False,
                "10.255.0.1",
                ["10.255.1.3", "10.255.1.4"],
                "Not Best in its group - Cluster list length",
            ),
        ]

    def test_other_table(self) -> None:
        assert validate.parse_junos_bgp_paths(ROUTE_JSON, "inet.0") == []

    def test_no_route(self) -> None:
        assert (
            validate.parse_junos_bgp_paths({"route-information": [{}]}, "inet.0") == []
        )


@pytest.fixture()
def junos_node() -> NodeInfo:
    return NodeInfo(
        name="dut",
        kind="juniper_vjunosrouter",
        profile=VJUNOS_ROUTER,
        management_ip="1.2.3.4",
    )


class TestCheckBgpActivePath:
    @pytest.fixture(autouse=True)
    def _fake_device(self, monkeypatch) -> None:
        self.sent: list[str] = []

        def run_command(node: NodeInfo, command: str) -> str:
            self.sent.append(command)
            return json.dumps(ROUTE_JSON)

        monkeypatch.setattr(validate, "run_command", run_command)

    def test_expected_path_and_reason(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_active_path(
            junos_node,
            "KNOB.inet.0",
            "203.0.113.0/24",
            "10.255.0.9",
            "Not Best in its group - Cluster list length",
        )
        assert result.passed, result.detail
        assert self.sent == [
            "show route table KNOB.inet.0 203.0.113.0/24 exact detail | display json"
        ]

    def test_other_path_active(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_active_path(
            junos_node, "KNOB.inet.0", "203.0.113.0/24", "10.255.0.1", None
        )
        assert not result.passed

    def test_wrong_reason(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_active_path(
            junos_node,
            "KNOB.inet.0",
            "203.0.113.0/24",
            "10.255.0.9",
            "Not Best in its group - Router ID",
        )
        assert not result.passed

    def test_route_missing(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_active_path(
            junos_node, "inet.0", "203.0.113.0/24", "10.255.0.9", None
        )
        assert not result.passed
