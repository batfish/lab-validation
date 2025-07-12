from lab_validation.parsers.fortios.models.interfaces import (
    FortiosInterface,
    FortiosPhysicalInterface,
)
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.FortiosValidator import (
    _compare_interfaces,
    _get_ip_str,
    _get_speed,
)


def test_get_speed() -> None:
    # bps
    assert _get_speed(speed=2, bru="bps") == 2

    # kbps
    assert _get_speed(speed=2, bru="kbps") == 2e3

    # Mbps
    assert _get_speed(speed=2, bru="Mbps") == 2e6

    # Gbps
    assert _get_speed(speed=2, bru="Gbps") == 2e9

    # Undefined
    assert _get_speed(speed=None, bru=None) is None


def test_get_ip_str() -> None:
    assert _get_ip_str("10.10.10.10", "255.255.255.252") == "10.10.10.10/30"
    assert _get_ip_str("192.168.0.1", "255.255.0.0") == "192.168.0.1/16"

    # Not set
    assert _get_ip_str("0.0.0.0", "0.0.0.0") is None
    assert _get_ip_str(None, None) is None


def test_compare_interface_equal() -> None:
    """Test interface comparison with equivalent, non-physical interface data."""
    vs_interface = FortiosInterface(
        name="ssl.root",
        mode=None,
        ip_addr="0.0.0.0",
        ip_mask="0.0.0.0",
        status="up",
        type="tunnel",
    )
    bf_interface = InterfaceProperties(
        name="ssl.root",
        access_vlan=None,
        active=True,
        all_prefixes=[],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=10000000000.0,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    assert _compare_interfaces(vs_interface, None, bf_interface) == {}


def test_compare_interface_equal_physical() -> None:
    """Test interface comparison with equivalent, physical interface data."""

    # Equivalent interfaces that are up
    vs_interface = FortiosInterface(
        name="port1",
        mode="static",
        ip_addr="10.10.10.1",
        ip_mask="255.255.255.0",
        status="up",
        type="physical",
    )
    vs_physical_interface = FortiosPhysicalInterface(
        name="port1",
        mode="static",
        ip_addr="10.10.10.1",
        ip_mask="255.255.255.0",
        ipv6_addr="::/0",
        status="up",
        speed=10000,
        bit_rate_unit="Mbps",
        duplex="full",
    )

    bf_interface = InterfaceProperties(
        name="port1",
        access_vlan=None,
        active=True,
        all_prefixes=["10.10.10.1/24"],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=10000000000.0,  # 10 Gbps
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )

    assert _compare_interfaces(vs_interface, vs_physical_interface, bf_interface) == {}

    # Equivalent interfaces that are down
    vs_interface = FortiosInterface(
        name="port1",
        mode="static",
        ip_addr=None,
        ip_mask=None,
        status="down",
        type="physical",
    )
    vs_physical_interface = FortiosPhysicalInterface(
        name="port1",
        mode="static",
        ip_addr=None,
        ip_mask=None,
        ipv6_addr=None,
        status="down",
        speed=None,
        bit_rate_unit=None,
        duplex=None,
    )
    bf_interface = InterfaceProperties(
        name="port1",
        access_vlan=None,
        active=False,
        all_prefixes=[],
        allowed_vlans=None,
        bandwidth=10000000,
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=10000000000.0,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    assert _compare_interfaces(vs_interface, vs_physical_interface, bf_interface) == {}


def test_compare_interface_not_equal() -> None:
    """Test interface comparison with interface data that is not equivalent."""
    vs_interface = FortiosInterface(
        name="port1",
        mode="static",
        ip_addr="10.10.10.10",
        ip_mask="255.255.255.0",
        status="up",
        type="physical",
    )
    vs_physical_interface = FortiosPhysicalInterface(
        name="port1",
        mode="static",
        ip_addr="10.10.10.10",
        ip_mask="255.255.255.0",
        ipv6_addr="::/0",
        status="up",
        speed=1000,
        bit_rate_unit="bps",
        duplex="full",
    )

    bf_params_equal = {
        "name": "port1",
        "access_vlan": None,
        "active": True,
        "all_prefixes": ["10.10.10.10/24"],
        "allowed_vlans": None,
        "bandwidth": 10000000,
        "description": None,
        "native_vlan": None,
        "mtu": 1500,
        "speed": 1e3,
        "switchport": False,
        "switchport_mode": None,
        "vrf": "default",
    }

    # Universal interface data:
    # Mismatched active
    new_bf_params = {**bf_params_equal, "active": False}
    assert _compare_interfaces(
        vs_interface, vs_physical_interface, InterfaceProperties(**new_bf_params)
    ) == {"active": f"Batfish: False, Fortios: status=up"}

    # Mismatched ip addresses
    new_bf_params = {**bf_params_equal, "all_prefixes": ["10.10.10.11/24"]}
    assert _compare_interfaces(
        vs_interface, vs_physical_interface, InterfaceProperties(**new_bf_params)
    ) == {"ipv4 address": f"Batfish: ['10.10.10.11/24'], Fortios: 10.10.10.10/24"}

    # Physical-only interface data:
    # Mismatched speed
    new_bf_params = {**bf_params_equal, "speed": 1e4}
    assert _compare_interfaces(
        vs_interface, vs_physical_interface, InterfaceProperties(**new_bf_params)
    ) == {"speed": f"Batfish: 10000.0, Fortios: 1000"}
