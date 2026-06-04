"""Vendor profiles and constants for lab builder."""

from __future__ import annotations

from dataclasses import dataclass, field


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
    # SR OS MD-CLI does not support Junos-style "| display json"; these are the
    # plain-text show commands, verified against a running SR-SIM.
    show_commands=[
        "admin show configuration",
        "show router interface",
        "show router route-table",
        "show router bgp summary",
        "show router bgp routes",
        "show version",
        "show router ospf neighbor",
        "show router isis adjacency",
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

    Example: "show route | display json" -> "show_route_|_display_json.txt"
    """
    return command.replace(" ", "_") + ".txt"
