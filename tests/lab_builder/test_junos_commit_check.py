"""Tests for Junos commit-check result classification.

Fixture output is real CLI text captured from vJunos-router 25.4R1.12
while building the junos_route_communities lab.
"""

from __future__ import annotations

import pytest

from lab_builder import device, validate
from lab_builder.config import VJUNOS_ROUTER
from lab_builder.models import NodeInfo

# Response to "set routing-options static route 10.99.0.0/24 community
# target:65001:1": the CLI rejects the line, so nothing is loaded.
SET_SYNTAX_ERROR = """\
                                                ^
error: syntax error, expecting '[' or <data>: target:65001:1

[edit]
"""

# Response to "set routing-options disable-linklocal-addr", captured while
# building junos_bgp_disable_linklocal_addr: an unknown keyword produces a
# bare "syntax error." with no "error:" prefix.
SET_BARE_SYNTAX_ERROR = """\
                                  ^
syntax error.

[edit]
"""

# Responses to "set protocols bgp receive-buffer 4294967296" and
# "set protocols bgp receive-buffer 64kb", captured while building
# junos_bgp_socket_buffers: invalid numeric values print only the caret
# line and a message, with no "error" or "syntax error" text.
SET_VALUE_OUT_OF_RANGE = """\
^
Value 4294967296 is not within range (0..4294967295) at '4294967296'

[edit]
"""

SET_INVALID_TRAILING_DATA = """\
^
Invalid trailing data 'b' for numeric value: '64kb' at '64kb'

[edit]
"""

COMMIT_CHECK_SUCCEEDS = "configuration check succeeds\n"


class FakeConnection:
    def __init__(self, set_output: str, commit_output: str) -> None:
        self.set_output = set_output
        self.commit_output = commit_output
        self.sent: list[str] = []

    def config_mode(self) -> None:
        pass

    def exit_config_mode(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def send_command_timing(self, command: str) -> str:
        self.sent.append(command)
        return self.set_output if command.startswith("set ") else "[edit]\n"

    def send_command(self, command: str, **kwargs) -> str:
        self.sent.append(command)
        return self.commit_output


@pytest.fixture()
def junos_node() -> NodeInfo:
    return NodeInfo(
        name="dut",
        kind="juniper_vjunosrouter",
        profile=VJUNOS_ROUTER,
        management_ip="1.2.3.4",
    )


def _patch_connect(monkeypatch, conn: FakeConnection) -> None:
    monkeypatch.setattr(device, "connect", lambda node: conn)


class TestJunosCommitCheck:
    def test_set_syntax_error_is_rejection(
        self, monkeypatch, junos_node: NodeInfo
    ) -> None:
        conn = FakeConnection(SET_SYNTAX_ERROR, COMMIT_CHECK_SUCCEEDS)
        _patch_connect(monkeypatch, conn)
        result = validate._check_commit_rejects(
            junos_node,
            ["set routing-options static route 10.99.0.0/24 community target:65001:1"],
            "syntax error",
        )
        assert result.passed, result.detail
        assert "rollback 0" in conn.sent

    def test_bare_set_syntax_error_is_rejection(
        self, monkeypatch, junos_node: NodeInfo
    ) -> None:
        conn = FakeConnection(SET_BARE_SYNTAX_ERROR, COMMIT_CHECK_SUCCEEDS)
        _patch_connect(monkeypatch, conn)
        result = validate._check_commit_rejects(
            junos_node,
            ["set routing-options disable-linklocal-addr"],
            "syntax error",
        )
        assert result.passed, result.detail
        assert "commit check" not in conn.sent

    def test_set_syntax_error_fails_accepts(
        self, monkeypatch, junos_node: NodeInfo
    ) -> None:
        conn = FakeConnection(SET_SYNTAX_ERROR, COMMIT_CHECK_SUCCEEDS)
        _patch_connect(monkeypatch, conn)
        result = validate._check_commit_accepts(
            junos_node,
            ["set routing-options static route 10.99.0.0/24 community target:65001:1"],
        )
        assert not result.passed

    def test_clean_set_and_commit_check_succeeds(
        self, monkeypatch, junos_node: NodeInfo
    ) -> None:
        conn = FakeConnection("[edit]\n", COMMIT_CHECK_SUCCEEDS)
        _patch_connect(monkeypatch, conn)
        result = validate._check_commit_accepts(
            junos_node,
            ["set routing-options aggregate route 10.98.0.0/16 community large:1:2:3"],
        )
        assert result.passed, result.detail

    @pytest.mark.parametrize(
        "set_output, expected_error",
        [
            (SET_VALUE_OUT_OF_RANGE, "not within range"),
            (SET_INVALID_TRAILING_DATA, "Invalid trailing data"),
        ],
    )
    def test_set_value_error_is_rejection(
        self, monkeypatch, junos_node: NodeInfo, set_output: str, expected_error: str
    ) -> None:
        conn = FakeConnection(set_output, COMMIT_CHECK_SUCCEEDS)
        _patch_connect(monkeypatch, conn)
        result = validate._check_commit_rejects(
            junos_node, ["set protocols bgp receive-buffer 4294967296"], expected_error
        )
        assert result.passed, result.detail
        assert "commit check" not in conn.sent
