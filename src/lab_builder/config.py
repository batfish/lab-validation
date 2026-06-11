"""Vendor profiles and constants for lab builder."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DynamicCommandGroup:
    """A two-phase, device-driven command expansion for the collector.

    Some operational state lives under a per-instance subtree whose instance
    names are not known until the device is queried (e.g. SR OS service VPRNs:
    each VPRN's route-table/interface state is at ``/state service vprn
    "<name>" ...``, and the set of ``<name>`` depends on the running config).
    Hardcoding the names means a lab whose VPRN is not literally the expected
    name is silently never collected.

    A DynamicCommandGroup runs ``discovery_command`` once, reads the list of
    instance names out of its JSON, then expands each of ``command_templates``
    (a ``{name}`` placeholder per discovered name) into a concrete command the
    collector runs like any other. This mirrors the dynamic per-VRF handling
    other vendors get for free from their ``... vrf all`` commands; SR OS has
    no ``vrf all`` form for these state paths, so the collector discovers the
    names itself.
    """

    # Command whose JSON output enumerates the instances (run once).
    discovery_command: str
    # Top-level JSON key holding the list of instance objects.
    discovery_json_key: str
    # Field in each instance object that holds the instance name.
    name_field: str
    # Per-instance command templates; "{name}" is replaced with each name.
    command_templates: list[str]


@dataclass(frozen=True)
class VendorProfile:
    """Configuration for a specific network OS in containerlab."""

    name: str
    containerlab_kind: str
    default_username: str
    default_password: str
    netmiko_device_type: str
    # Containerlab ethN to device interface name.
    # eth0 is always management; data interfaces start at eth1.
    interface_prefix: str
    interface_offset: int  # eth1 maps to <prefix>0/0/<offset>
    show_commands: list[str] = field(default_factory=list)
    # Device-driven command expansion run after show_commands (see
    # DynamicCommandGroup). Empty for vendors whose per-instance state is
    # reachable with a single wildcard/"vrf all" command.
    dynamic_command_groups: list[DynamicCommandGroup] = field(default_factory=list)
    config_command: str = ""
    boot_timeout_seconds: int = 600


# Startup configs for vrnetlab Juniper nodes must be in curly-brace format,
# not set format. They get concatenated with the vrnetlab init.conf and loaded
# as a config disk. The collected "show configuration | display set" output
# is what goes into the lab-validation snapshot.

VJUNOS_ROUTER = VendorProfile(
    name="junos",
    containerlab_kind="juniper_vjunosrouter",
    default_username="admin",
    default_password="admin@123",
    netmiko_device_type="juniper_junos",
    interface_prefix="ge-0/0/",
    interface_offset=0,  # eth1 -> ge-0/0/0, eth2 -> ge-0/0/1, ...
    show_commands=[
        "show configuration | display set",
        "show route instance | display json",
        "show interfaces | display json",
        "show route | display json",
        "show route protocol bgp detail | display json",
        "show version | display json",
        "show bgp neighbor | display json",
        "show ospf neighbor | display json",
        "show isis adjacency | display json",
    ],
    config_command="show configuration | display set",
    boot_timeout_seconds=900,
)

VJUNOS_SWITCH = VendorProfile(
    name="junos",
    containerlab_kind="juniper_vjunosswitch",
    default_username="admin",
    default_password="admin@123",
    netmiko_device_type="juniper_junos",
    interface_prefix="ge-0/0/",
    interface_offset=0,
    show_commands=VJUNOS_ROUTER.show_commands,
    config_command=VJUNOS_ROUTER.config_command,
    boot_timeout_seconds=900,
)

VJUNOS_EVOLVED = VendorProfile(
    name="junos",
    containerlab_kind="juniper_vjunosevolved",
    default_username="admin",
    default_password="admin@123",
    netmiko_device_type="juniper_junos",
    interface_prefix="et-0/0/",
    interface_offset=0,
    show_commands=VJUNOS_ROUTER.show_commands,
    config_command=VJUNOS_ROUTER.config_command,
    boot_timeout_seconds=1200,
)

CRPD = VendorProfile(
    name="junos",
    containerlab_kind="juniper_crpd",
    default_username="root",
    default_password="clab123",
    netmiko_device_type="juniper_junos",
    interface_prefix="eth",
    interface_offset=1,  # cRPD uses linux interface names directly
    show_commands=VJUNOS_ROUTER.show_commands,
    config_command=VJUNOS_ROUTER.config_command,
    boot_timeout_seconds=60,
)

ARISTA_CEOS = VendorProfile(
    name="arista",
    containerlab_kind="arista_ceos",
    default_username="admin",
    default_password="admin",
    netmiko_device_type="arista_eos",
    interface_prefix="Ethernet",
    interface_offset=1,  # eth1 -> Ethernet1, eth2 -> Ethernet2, ...
    show_commands=[
        "show running-config",
        "show interfaces | json",
        "show ip route vrf all | json",
        "show ip bgp vrf all | json",
        "show ip bgp neighbors vrf all | json",
        "show bgp evpn | json",
        "show version | json",
        "show ip ospf neighbor | json",
        "show isis neighbors | json",
        "show vrf | json",
    ],
    config_command="show running-config",
    boot_timeout_seconds=300,
)

# Nokia SR-SIM is a native container (loaded via `docker load`), not a
# VM-in-container. A simple 2-node lab uses the integrated model with the
# default SR-1 chassis (single container per node). Datapath ports are named
# L/M/c/P on SR OS; containerlab link endpoints encode this as eL-M-cC-P
# (see _eth_to_vendor_interface), so this profile does not use the
# prefix+offset interface model. SR-SIM will not boot without a license
# mounted at /nokia/license/license.txt (provided via the clab `license:` key).
NOKIA_SRSIM = VendorProfile(
    name="sros",
    containerlab_kind="nokia_srsim",
    default_username="admin",
    default_password="admin",
    netmiko_device_type="nokia_sros",
    interface_prefix="",  # unused; SR OS ports are mapped from eL-M-cC-P
    interface_offset=0,
    # SR OS exposes operational data in a separate "state" tree, navigable like config
    # (MD-CLI User Guide §3.3). The `info` command renders it; the `json` MODIFIER emits
    # indented JSON IETF format keyed by the nokia-state YANG modules -- the SR OS analog
    # of Junos `show | display json`. The validator deserializes that JSON against the
    # state YANG (no pyparsing of show tables). We ALSO keep a few plain-text `show ...`
    # outputs for human cross-reading.
    #
    # JSON word order matters: modifiers come BEFORE the path -- `info json /state ...`
    # (cf. guide `info detail /state system`). Our earlier "SR-SIM has no JSON" finding
    # was a syntax bug: we put `json` AFTER the path (`info /state ... json`), which SR OS
    # parsed as a bogus element name and rejected with "MGMT_CORE #2201: Unknown element
    # 'json'". CONFIRMED LIVE on SR-SIM 26.3.R1 (2026-06-05 re-collect): all 7 state paths
    # return valid JSON keyed by the nokia-state YANG. Only `show` cannot pipe to json on
    # SR OS; JSON is an `info`-family feature. (26.3.R1 MD-CLI Quick Reference, Table 4.)
    #
    # List nodes (interface, neighbor) require a `*` wildcard to dump all entries;
    # container nodes (system, route-table, bgp rib) take no key. ospf/isis return empty
    # when not configured.
    show_commands=[
        "admin show configuration",  # config: MD-CLI brace form (parsed by Batfish)
        # Structured state as JSON (nokia-state YANG) -- machine-parsed by the validator:
        "info json /state system",
        'info json /state router "Base" interface *',
        'info json /state router "Base" route-table',
        'info json /state router "Base" bgp neighbor *',
        'info json /state router "Base" bgp rib',
        'info json /state router "Base" ospf *',
        'info json /state router "Base" isis *',
        # VPRN (multi-VRF) state is collected dynamically -- see
        # dynamic_command_groups below -- because the VPRN names are not known
        # until the device is queried.
        # Plain-text (human-readable, cross-check):
        "show version",
        "show router interface",
        "show router route-table",
        "show router bgp summary",
        "show router bgp routes",
        "show router ospf neighbor",
        "show router isis adjacency",
    ],
    # VPRN (multi-VRF) state. A non-Base router instance is a `service vprn`
    # whose state lives under `/state service vprn "<name>" ...` (same
    # nokia-state schema as the Base route-table/interface trees). Unlike the
    # `vrf all` form other vendors expose, SR OS has no single command that
    # dumps every VPRN's route-table unwrapped, so the collector first
    # enumerates the VPRN names (the `oper-service-id` wildcard returns just
    # name + id per VPRN -- a small payload) and then collects each VPRN's
    # route-table and interface state under the same per-VPRN filename the
    # SrosValidator already discovers by glob. A device with no VPRN yields no
    # names and therefore no files (vs. the old hardcoded `"red"` probe that
    # wrote an empty `{}` on every node). CONFIRMED LIVE on SR-SIM 26.3.R1
    # (2026-06-11): the discovery wildcard returns
    # {"nokia-state:vprn": [{"service-name": "RED", "oper-service-id": 100}, ...]}
    # and the per-VPRN paths return the unwrapped nokia-state:unicast /
    # nokia-state:interface shapes the parsers expect.
    dynamic_command_groups=[
        DynamicCommandGroup(
            discovery_command="info json /state service vprn * oper-service-id",
            discovery_json_key="nokia-state:vprn",
            name_field="service-name",
            command_templates=[
                'info json /state service vprn "{name}" route-table',
                'info json /state service vprn "{name}" interface *',
            ],
        ),
    ],
    config_command="admin show configuration",
    boot_timeout_seconds=600,
)

CISCO_N9KV = VendorProfile(
    name="nx",
    containerlab_kind="cisco_n9kv",
    default_username="admin",
    default_password="admin",
    netmiko_device_type="cisco_nxos",
    interface_prefix="Ethernet1/",
    interface_offset=1,  # eth1 -> Ethernet1/1, eth2 -> Ethernet1/2, ...
    show_commands=[
        "show running-config",
        "show interface",
        "show ip route vrf all",
        "show ip bgp vrf all",
        "show ip bgp all neighbor",
        "show version",
        "show vrf",
    ],
    config_command="show running-config",
    boot_timeout_seconds=900,
)

VENDOR_PROFILES: dict[str, VendorProfile] = {
    "juniper_vjunosrouter": VJUNOS_ROUTER,
    "juniper_vjunosswitch": VJUNOS_SWITCH,
    "juniper_vjunosevolved": VJUNOS_EVOLVED,
    "juniper_crpd": CRPD,
    "arista_ceos": ARISTA_CEOS,
    "cisco_n9kv": CISCO_N9KV,
    "nokia_srsim": NOKIA_SRSIM,
}


def get_profile(containerlab_kind: str) -> VendorProfile:
    """Get the vendor profile for a containerlab kind."""
    if containerlab_kind not in VENDOR_PROFILES:
        supported = ", ".join(VENDOR_PROFILES.keys())
        raise ValueError(
            f"Unsupported containerlab kind: {containerlab_kind}. "
            f"Supported: {supported}"
        )
    return VENDOR_PROFILES[containerlab_kind]


def command_to_filename(command: str) -> str:
    """Convert a show command to the filename convention used by lab-validation.

    Spaces and path slashes collapse to underscores (so SR OS state paths like
    "info /state router bgp neighbor" do not create spurious subdirectories). Shell-
    unfriendly characters from SR OS MD-CLI paths -- double quotes around list keys and
    the "*" list-wildcard -- are stripped. The "|" of piped commands is preserved (it is
    part of the established Junos/EOS filename convention).

    Examples:
        "show route | display json"                  -> "show_route_|_display_json.txt"
        'info json /state router "Base" interface *' -> "info_json_state_router_Base_interface.txt"
    """
    cleaned = command.replace('"', "").replace("*", "")
    return re.sub(r"[ /]+", "_", cleaned).strip("_") + ".txt"
