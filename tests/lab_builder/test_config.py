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
