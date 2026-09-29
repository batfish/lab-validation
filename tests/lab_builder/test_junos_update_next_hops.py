"""Tests for the Junos bgp_update_next_hops check.

Fixture output is real `show log <file> | match "BGP RECV"` text captured
from vJunos-router 25.4R1.12 while building the
junos_bgp_disable_linklocal_addr lab.
"""

from __future__ import annotations

import pytest

from lab_builder import validate
from lab_builder.config import VJUNOS_ROUTER
from lab_builder.models import NodeInfo

# One UPDATE per session: LINK12 without disable-linklocal-addr, LINK13 with.
TRACE = """\
Sep 29 16:58:40.495435 BGP RECV 2001:db8:12::1+50437 -> 2001:db8:12::2+179
Sep 29 16:58:40.495465 BGP RECV message type 2 (Update) length 84
Sep 29 16:58:40.495470 BGP RECV Update PDU length 84
Sep 29 16:58:40.495856 BGP RECV flags 0x40 code Origin(1): IGP, length(1)
Sep 29 16:58:40.495865 BGP RECV flags 0x40 code ASPath(2) (4-byte-cap) length 6: 65001
Sep 29 16:58:40.495870 BGP RECV flags 0x90 code MP_reach(14): length(44) AFI/SAFI 2/1
Sep 29 16:58:40.495879 BGP RECV \tnhop 2001:db8:12::1 len 16
Sep 29 16:58:40.495884 BGP RECV \tnhop fe80::aac1:abff:fedf:b0e2 len 16
Sep 29 16:58:40.495893 BGP RECV \t2001:db8:100::/48
Sep 29 16:58:40.496016 BGP RECV 2001:db8:13::1+57803 -> 2001:db8:13::2+179
Sep 29 16:58:40.496021 BGP RECV message type 2 (Update) length 68
Sep 29 16:58:40.496023 BGP RECV Update PDU length 68
Sep 29 16:58:40.496026 BGP RECV flags 0x40 code Origin(1): IGP, length(1)
Sep 29 16:58:40.496030 BGP RECV flags 0x40 code ASPath(2) (4-byte-cap) length 6: 65001
Sep 29 16:58:40.496033 BGP RECV flags 0x90 code MP_reach(14): length(28) AFI/SAFI 2/1
Sep 29 16:58:40.496037 BGP RECV \tnhop 2001:db8:13::1 len 16
Sep 29 16:58:40.496041 BGP RECV \t2001:db8:200::/48
"""


class TestParseTraceUpdateNextHops:
    def test_global_and_link_local(self) -> None:
        assert validate.parse_junos_trace_update_next_hops(
            TRACE, "2001:db8:12::1", "2001:db8:100::/48"
        ) == ["2001:db8:12::1", "fe80::aac1:abff:fedf:b0e2"]

    def test_global_only(self) -> None:
        assert validate.parse_junos_trace_update_next_hops(
            TRACE, "2001:db8:13::1", "2001:db8:200::/48"
        ) == ["2001:db8:13::1"]

    def test_prefix_from_other_neighbor(self) -> None:
        assert (
            validate.parse_junos_trace_update_next_hops(
                TRACE, "2001:db8:13::1", "2001:db8:100::/48"
            )
            is None
        )


@pytest.fixture()
def junos_node() -> NodeInfo:
    return NodeInfo(
        name="receiver",
        kind="juniper_vjunosrouter",
        profile=VJUNOS_ROUTER,
        management_ip="1.2.3.4",
    )


class TestCheckBgpUpdateNextHops:
    @pytest.fixture(autouse=True)
    def _fake_device(self, monkeypatch) -> None:
        self.sent: list[str] = []

        def run_command(node: NodeInfo, command: str) -> str:
            self.sent.append(command)
            return TRACE if command.startswith("show log") else ""

        monkeypatch.setattr(validate, "run_command", run_command)
        monkeypatch.setattr(validate.time, "sleep", lambda s: None)

    def test_link_local_expected_and_present(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_update_next_hops(
            junos_node,
            "2001:db8:12::1",
            "2001:db8:100::/48",
            "bgp-updates",
            ["2001:db8:12::1"],
            link_local=True,
        )
        assert result.passed, result.detail
        assert self.sent[:2] == [
            "clear log bgp-updates",
            "clear bgp neighbor 2001:db8:12::1 soft-inbound",
        ]

    def test_link_local_unexpected(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_update_next_hops(
            junos_node,
            "2001:db8:12::1",
            "2001:db8:100::/48",
            "bgp-updates",
            ["2001:db8:12::1"],
            link_local=False,
        )
        assert not result.passed

    def test_link_local_expected_and_absent(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_update_next_hops(
            junos_node,
            "2001:db8:13::1",
            "2001:db8:200::/48",
            "bgp-updates",
            ["2001:db8:13::1"],
            link_local=True,
        )
        assert not result.passed

    def test_no_update_traced(self, junos_node: NodeInfo) -> None:
        result = validate._junos_check_bgp_update_next_hops(
            junos_node,
            "2001:db8:14::1",
            "2001:db8:300::/48",
            "bgp-updates",
            ["2001:db8:14::1"],
            link_local=False,
            timeout=0,
        )
        assert not result.passed
        assert "no UPDATE traced" in result.detail
