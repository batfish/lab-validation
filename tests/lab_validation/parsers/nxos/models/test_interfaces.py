from lab_validation.parsers.nxos.models.interfaces import NxosInterface


def test_is_physical() -> None:
    kwargs = {
        "bandwidth": 1_000_000_000,
        "mtu": 1500,
        "admin": True,
        "line": True,
        "mode": "trunk",
    }
    assert NxosInterface(name="Ethernet1", **kwargs).is_physical()
    assert NxosInterface(name="Ethernet1/2", **kwargs).is_physical()
    assert NxosInterface(name="Ethernet1/2/3", **kwargs).is_physical()
    assert not NxosInterface(name="Ethernet1.4", **kwargs).is_physical()
    assert not NxosInterface(name="Ethernet1/2.4", **kwargs).is_physical()
    assert not NxosInterface(name="loopback3", **kwargs).is_physical()
    assert not NxosInterface(name="Port-channel1", **kwargs).is_physical()
    assert not NxosInterface(name="Vlan100", **kwargs).is_physical()
