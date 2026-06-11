"""Tests for lab_builder.config helpers."""

from __future__ import annotations

from lab_builder.config import NOKIA_SRSIM, command_to_filename


class TestCommandToFilename:
    def test_spaces_become_underscores(self) -> None:
        assert command_to_filename("show version") == "show_version.txt"

    def test_pipe_convention_preserved(self) -> None:
        # Junos/EOS piped JSON commands keep the "|" token.
        assert (
            command_to_filename("show route | display json")
            == "show_route_|_display_json.txt"
        )

    def test_hyphen_preserved(self) -> None:
        assert command_to_filename("show running-config") == "show_running-config.txt"

    def test_state_path_slashes_collapse(self) -> None:
        # SR OS state paths contain "/"; it must NOT leak into the filename and
        # create a spurious subdirectory.
        assert (
            command_to_filename("info /state router bgp neighbor json")
            == "info_state_router_bgp_neighbor_json.txt"
        )

    def test_no_leading_underscore_from_slash(self) -> None:
        assert command_to_filename("/state system") == "state_system.txt"

    def test_quotes_and_wildcard_stripped(self) -> None:
        # SR OS list paths use quoted keys and a "*" wildcard; neither is filename-safe.
        assert (
            command_to_filename('info /state router "Base" interface *')
            == "info_state_router_Base_interface.txt"
        )

    def test_sros_profile_filenames_are_flat_and_unique(self) -> None:
        names = [command_to_filename(c) for c in NOKIA_SRSIM.show_commands]
        assert all("/" not in n for n in names), names
        assert len(set(names)) == len(names), "filename collision"


class TestNokiaSrsimProfile:
    def test_no_hardcoded_vprn_name_in_show_commands(self) -> None:
        # VPRN state is collected dynamically (the names are discovered from the
        # device), so no specific VPRN name -- formerly the literal "red" -- may
        # be baked into the static command list.
        for cmd in NOKIA_SRSIM.show_commands:
            assert "service vprn" not in cmd, cmd

    def test_vprn_discovery_group_is_wired(self) -> None:
        groups = NOKIA_SRSIM.dynamic_command_groups
        assert len(groups) == 1
        group = groups[0]
        # Discovery enumerates names from the state tree's vprn list.
        assert group.discovery_command.startswith("info json /state service vprn *")
        assert group.discovery_json_key == "nokia-state:vprn"
        assert group.name_field == "service-name"
        # Each template has a single {name} slot and targets the per-VPRN state
        # paths the SrosValidator consumes.
        templates = group.command_templates
        assert any("route-table" in t for t in templates)
        assert any("interface *" in t for t in templates)
        for t in templates:
            assert t.count("{name}") == 1, t
            assert t.format(name="RED").startswith(
                'info json /state service vprn "RED" '
            )

    def test_state_commands_use_info_json_with_modifier_before_path(self) -> None:
        # SR OS JSON output is `info json /state ...` -- the `json` modifier comes
        # BEFORE the path. Putting it AFTER (`info /state ... json`) makes SR OS parse
        # `json` as an element name and fail with "Unknown element 'json'"; that bug is
        # what produced the (wrong) "SR-SIM has no JSON" finding. Guard against its return.
        state_cmds = [c for c in NOKIA_SRSIM.show_commands if "/state" in c]
        assert state_cmds, "expected SR OS state-capture commands"
        for cmd in state_cmds:
            assert cmd.startswith("info json /state"), cmd
            assert not cmd.rstrip().endswith(" json"), (
                f"json must precede the path: {cmd}"
            )
