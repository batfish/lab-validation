"""Tests for lab_builder.collector, focused on dynamic command expansion."""

from __future__ import annotations

import lab_builder.collector as collector
from lab_builder.collector import collect_node
from lab_builder.config import (
    NOKIA_SRSIM,
    VendorProfile,
    command_to_filename,
)
from lab_builder.models import NodeInfo

# A discovery command output naming two VPRNs (the live SR-SIM 26.3.R1 shape).
_VPRN_DISCOVERY_JSON = """{
    "nokia-state:vprn": [
        {"service-name": "RED", "oper-service-id": 100},
        {"service-name": "BLUE", "oper-service-id": 200}
    ]
}"""


def _sros_node() -> NodeInfo:
    return NodeInfo(
        name="r1",
        kind="nokia_srsim",
        profile=NOKIA_SRSIM,
        management_ip="172.20.20.2",
    )


def _fake_run_command(responses: dict[str, str]):
    """Build a run_command stub that returns canned text keyed by command.

    Unlisted commands return "{}" (the SR OS empty-state shape), so a test only
    needs to spell out the commands it cares about.
    """

    def _run(node: NodeInfo, command: str, timeout: int = 60) -> str:
        return responses.get(command, "{}")

    return _run


def test_collect_node_discovers_and_expands_vprns(tmp_path, monkeypatch) -> None:
    # The SR OS profile enumerates VPRNs from the device, then collects each
    # VPRN's route-table and interface state under the per-VPRN filename the
    # SrosValidator discovers by glob.
    responses = {
        "info json /state service vprn * oper-service-id": _VPRN_DISCOVERY_JSON,
        'info json /state service vprn "RED" route-table': '{"red-rt": true}',
        'info json /state service vprn "RED" interface *': '{"red-if": true}',
        'info json /state service vprn "BLUE" route-table': '{"blue-rt": true}',
        'info json /state service vprn "BLUE" interface *': '{"blue-if": true}',
    }
    monkeypatch.setattr(collector, "run_command", _fake_run_command(responses))

    result = collect_node(_sros_node(), tmp_path)

    node_dir = tmp_path / "r1"
    # Discovery output is saved as part of the snapshot.
    assert (node_dir / "info_json_state_service_vprn_oper-service-id.txt").is_file()
    # Per-VPRN files exist for both discovered names, with the expected content.
    for name, tag in [("RED", "red"), ("BLUE", "blue")]:
        rt = node_dir / f"info_json_state_service_vprn_{name}_route-table.txt"
        intf = node_dir / f"info_json_state_service_vprn_{name}_interface.txt"
        assert rt.read_text() == f'{{"{tag}-rt": true}}'
        assert intf.read_text() == f'{{"{tag}-if": true}}'
        assert rt.name in result.files
        assert intf.name in result.files
    assert not result.errors


def test_collect_node_no_vprns_collects_no_vprn_files(tmp_path, monkeypatch) -> None:
    # A device with no VPRN yields an empty discovery list and therefore no
    # per-VPRN files -- an improvement over the old hardcoded "red" probe, which
    # wrote an empty {} file on every node regardless.
    responses = {
        "info json /state service vprn * oper-service-id": '{"nokia-state:vprn": []}',
    }
    monkeypatch.setattr(collector, "run_command", _fake_run_command(responses))

    result = collect_node(_sros_node(), tmp_path)

    node_dir = tmp_path / "r1"
    vprn_files = list(node_dir.glob("info_json_state_service_vprn_*_route-table.txt"))
    assert vprn_files == []
    # The discovery command itself still ran and was saved.
    assert (node_dir / "info_json_state_service_vprn_oper-service-id.txt").is_file()
    assert not result.errors


def test_collect_node_discovery_failure_is_recorded_not_fatal(
    tmp_path, monkeypatch
) -> None:
    # If the discovery command errors, the group expands to nothing and the
    # error is recorded; static commands are unaffected.
    def _run(node: NodeInfo, command: str, timeout: int = 60) -> str:
        if "service vprn" in command:
            raise RuntimeError("boom")
        return "{}"

    monkeypatch.setattr(collector, "run_command", _run)

    result = collect_node(_sros_node(), tmp_path)

    node_dir = tmp_path / "r1"
    assert list(node_dir.glob("info_json_state_service_vprn_*")) == []
    assert any("oper-service-id" in e for e in result.errors)
    # A static command still produced a file.
    assert (node_dir / "info_json_state_system.txt").is_file()


def test_collect_node_unparseable_discovery_yields_no_expansion(
    tmp_path, monkeypatch
) -> None:
    responses = {
        "info json /state service vprn * oper-service-id": "not json at all",
    }
    monkeypatch.setattr(collector, "run_command", _fake_run_command(responses))

    result = collect_node(_sros_node(), tmp_path)

    node_dir = tmp_path / "r1"
    assert list(node_dir.glob("info_json_state_service_vprn_*_route-table.txt")) == []
    # The (unparseable) discovery output was still saved; no error -- an empty
    # or malformed enumeration just means "no instances".
    assert (node_dir / "info_json_state_service_vprn_oper-service-id.txt").is_file()
    assert not result.errors


def test_collect_node_no_dynamic_groups(tmp_path, monkeypatch) -> None:
    # A profile without dynamic groups behaves exactly like the static path.
    profile = VendorProfile(
        name="x",
        containerlab_kind="x",
        default_username="u",
        default_password="p",
        netmiko_device_type="t",
        interface_prefix="",
        interface_offset=0,
        show_commands=["show version"],
    )
    node = NodeInfo(name="n", kind="x", profile=profile, management_ip="1.2.3.4")
    monkeypatch.setattr(
        collector, "run_command", _fake_run_command({"show version": "v1"})
    )

    result = collect_node(node, tmp_path)

    assert (tmp_path / "n" / "show_version.txt").read_text() == "v1"
    assert result.files == ["show_version.txt"]


def test_expanded_filenames_match_validator_glob() -> None:
    # The per-VPRN filenames the collector writes must match the pattern the
    # SrosValidator globs (info_json_state_service_vprn_<name>_route-table.txt
    # and _interface.txt) so discovery flows straight through to validation.
    group = NOKIA_SRSIM.dynamic_command_groups[0]
    for template in group.command_templates:
        filename = command_to_filename(template.format(name="RED"))
        assert filename.startswith("info_json_state_service_vprn_RED_")
        assert filename.endswith(("_route-table.txt", "_interface.txt"))
