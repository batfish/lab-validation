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
        "show route protocol bgp | display json",
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

VENDOR_PROFILES: dict[str, VendorProfile] = {
    "juniper_vjunosrouter": VJUNOS_ROUTER,
    "juniper_vjunosswitch": VJUNOS_SWITCH,
    "juniper_vjunosevolved": VJUNOS_EVOLVED,
    "juniper_crpd": CRPD,
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
