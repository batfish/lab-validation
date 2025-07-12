from lab_validation.parsers.checkpoint.models.interfaces import CheckpointInterface
from lab_validation.validators.batfish_models.interface_properties import (
    InterfaceProperties,
)
from lab_validation.validators.CheckpointGaiaValidator import CheckpointGaiaValidator


def test_interface_props_equal() -> None:
    bf = InterfaceProperties(
        name="eth0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.1.1.1/24"],
        allowed_vlans=None,
        bandwidth=int(1e9),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1e9,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    cp = CheckpointInterface(
        name="eth0",
        state=True,
        type="ethernet",
        mtu=1500,
        speed=1e9,
        prefix="1.1.1.1/24",
    )
    assert CheckpointGaiaValidator._compare_interfaces(cp, bf) == {}


def test_interface_state_not_equal() -> None:
    bf = InterfaceProperties(
        name="eth0",
        access_vlan=None,
        active=False,
        all_prefixes=["1.1.1.1/24"],
        allowed_vlans=None,
        bandwidth=int(1e8),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1e9,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    cp = CheckpointInterface(
        name="eth0",
        state=True,
        type="ethernet",
        mtu=1500,
        speed=1e9,
        prefix="1.1.1.1/24",
    )
    assert CheckpointGaiaValidator._compare_interfaces(cp, bf) == {
        "active": "Batfish: False, Checkpoint: True",
    }


def test_interface_speed_not_equal() -> None:
    bf = InterfaceProperties(
        name="eth0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.1.1.1/24"],
        allowed_vlans=None,
        bandwidth=int(1e8),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1000,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    cp = CheckpointInterface(
        name="eth0",
        state=True,
        type="ethernet",
        mtu=1500,
        speed=1e9,
        prefix="1.1.1.1/24",
    )
    assert CheckpointGaiaValidator._compare_interfaces(cp, bf) == {
        "speed": "Batfish: 1000, Checkpoint: 1000000000.0",
    }


def test_interface_address_not_equal() -> None:
    bf = InterfaceProperties(
        name="eth0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.1.1.1/24"],
        allowed_vlans=None,
        bandwidth=int(1e8),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1e9,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    cp = CheckpointInterface(
        name="eth0",
        state=True,
        type="ethernet",
        mtu=1500,
        speed=1e9,
        prefix="1.1.1.2/24",
    )
    assert CheckpointGaiaValidator._compare_interfaces(cp, bf) == {
        "ipv4 address": "Batfish: ['1.1.1.1/24'], Checkpoint: 1.1.1.2/24",
    }


def test_interface_mtu_not_equal() -> None:
    bf = InterfaceProperties(
        name="eth0",
        access_vlan=None,
        active=True,
        all_prefixes=["1.1.1.1/24"],
        allowed_vlans=None,
        bandwidth=int(1e8),
        description=None,
        native_vlan=None,
        mtu=1500,
        speed=1e9,
        switchport=False,
        switchport_mode=None,
        vrf="default",
    )
    cp = CheckpointInterface(
        name="eth0",
        state=True,
        type="ethernet",
        mtu=2000,
        speed=1e9,
        prefix="1.1.1.1/24",
    )
    assert CheckpointGaiaValidator._compare_interfaces(cp, bf) == {
        "mtu": "Batfish: 1500, Checkpoint: 2000",
    }


def test_interface_props_missing_and_extra() -> None:
    bf_ifaces = [
        InterfaceProperties(
            name="eth1",
            access_vlan=None,
            active=False,
            all_prefixes=["1.1.1.1/24"],
            allowed_vlans=None,
            bandwidth=int(1e8),
            description=None,
            native_vlan=None,
            mtu=1500,
            speed=1000,
            switchport=False,
            switchport_mode=None,
            vrf="default",
        )
    ]
    cp_ifaces = [
        CheckpointInterface(
            name="eth0",
            state=True,
            type="ethernet",
            mtu=2000,
            speed=1e9,
            prefix="1.1.1.2/24",
        )
    ]
    assert CheckpointGaiaValidator._compare_all_interfaces(cp_ifaces, bf_ifaces) == {
        "eth0": f"Missing interface in Batfish: {cp_ifaces[0]}",
        "eth1": f"Extra interface in Batfish: {bf_ifaces[0]}",
    }
