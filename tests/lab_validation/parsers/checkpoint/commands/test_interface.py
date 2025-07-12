"""
Tests of the Checkpoint model for show interfaces, using Checkpoint show data.
"""
from lab_validation.parsers.checkpoint.commands.interfaces import parse_show_interfaces
from lab_validation.parsers.checkpoint.models.interfaces import CheckpointInterface


def test_parse_interfaces() -> None:
    ifs = parse_show_interfaces(
        """Interface bond78
    state on
    mac-addr 0a:0b:0c:0d:0e:0f
    type bond
    link-state not available
    mtu 1500
    auto-negotiation Not configured
    speed N/A
    ipv6-autoconfig Not configured
    duplex N/A
    monitor-mode Not configured
    link-speed Not configured
    comments FW_OUTSIDE3
    ipv4-address Not Configured
    ipv6-address Not Configured
    ipv6-local-link-address Not Configured

Statistics:
    TX bytes:997602 packets:8247 errors:0 dropped:0 overruns:0 carrier:0
    RX bytes:993058 packets:8224 errors:0 dropped:0 overruns:0 frame:0

Interface bond78.4
    state on
    mac-addr 1a:1b:1c:1d:1e:1f
    type vlan
    link-state not available
    mtu 1500
    auto-negotiation Not configured
    speed N/A (bond78)
    ipv6-autoconfig Not configured
    duplex N/A (bond78)
    monitor-mode Not configured
    link-speed Not configured
    comments
    ipv4-address 1.1.1.1/24
    ipv6-address Not Configured
    ipv6-local-link-address Not Configured

Statistics:
    TX bytes:16828 packets:394 errors:0 dropped:0 overruns:0 carrier:0
    RX bytes:16842 packets:396 errors:0 dropped:0 overruns:0 frame:0


Interface eth0
    state on
    mac-addr 2a:2b:2c:2d:2e:2f
    type ethernet
    link-state link up
    mtu 1500
    auto-negotiation on
    speed 1000M
    ipv6-autoconfig Not configured
    duplex full
    monitor-mode Not configured
    link-speed 1000M/full
    comments
    ipv4-address 2.2.2.2/16
    ipv6-address Not Configured
    ipv6-local-link-address Not Configured

Statistics:
    TX bytes:3771632 packets:19831 errors:0 dropped:0 overruns:0 carrier:0
    RX bytes:76174366 packets:59222 errors:6 dropped:0 overruns:0 frame:0
"""
    )
    assert ifs == [
        CheckpointInterface(
            name="bond78", state=True, type="bond", mtu=1500, speed=None, prefix=None
        ),
        CheckpointInterface(
            name="bond78.4",
            state=True,
            type="vlan",
            mtu=1500,
            speed=None,
            prefix="1.1.1.1/24",
        ),
        CheckpointInterface(
            name="eth0",
            state=True,
            type="ethernet",
            mtu=1500,
            speed=1e9,
            prefix="2.2.2.2/16",
        ),
    ]
