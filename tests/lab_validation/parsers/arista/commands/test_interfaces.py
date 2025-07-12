from lab_validation.parsers.arista.commands.interfaces import parse_show_interfaces_json
from lab_validation.parsers.arista.models.interfaces import AristaInterface


def test_parse_show_interfaces_json() -> None:
    text = """
    {"interfaces":{
        "Management1": {
            "lastStatusChangeTimestamp": 1573670631.5172014,
            "lanes": 0,
            "name": "Management1",
            "interfaceStatus": "connected",
            "autoNegotiate": "success",
            "burnedInAddress": "0c:ef:e6:c7:98:00",
            "loopbackMode": "loopbackNone",
            "interfaceStatistics": {"inBitsRate": 0.0, "inPktsRate": 0.0, "outBitsRate": 49.24217191943765, "updateInterval": 300.0, "outPktsRate": 0.06955059291553908},
            "mtu": 1500,
            "hardware": "ethernet",
            "duplex": "duplexFull",
             "bandwidth": 1000000000,
             "forwardingModel": "routed",
             "lineProtocolStatus": "up",
             "interfaceCounters": {"outBroadcastPkts": 0, "outUcastPkts": 6075, "totalOutErrors": 0, "inMulticastPkts": 0, "counterRefreshTime": 1573852832.580422, "inBroadcastPkts": 0, "outputErrorsDetail": {"deferredTransmissions": 0, "txPause": 0, "collisions": 0, "lateCollisions": 0}, "inOctets": 0, "outDiscards": 0, "outOctets": 1075262, "inUcastPkts": 0, "inTotalPkts": 0, "inputErrorsDetail": {"runtFrames": 0, "rxPause": 0, "fcsErrors": 0, "alignmentErrors": 0, "giantFrames": 0, "symbolErrors": 0}, "linkStatusChanges": 3, "outMulticastPkts": 6075, "totalInErrors": 0, "inDiscards": 0},
             "interfaceAddress": [],
             "physicalAddress": "0c:ef:e6:c7:98:00",
             "description": ""
        },
        "Ethernet1": {
            "lastStatusChangeTimestamp": 1573670631.5172014,
            "lanes": 0,
            "name": "Ethernet1",
            "interfaceStatus": "connected",
            "autoNegotiate": "success",
            "burnedInAddress": "0c:ef:e6:c7:98:00",
            "loopbackMode": "loopbackNone",
            "interfaceStatistics": {"inBitsRate": 0.0, "inPktsRate": 0.0, "outBitsRate": 49.24217191943765, "updateInterval": 300.0, "outPktsRate": 0.06955059291553908},
            "mtu": 1514,
            "hardware": "ethernet",
            "duplex": "duplexFull",
             "bandwidth": 1,
             "forwardingModel": "routed",
             "lineProtocolStatus": "down",
             "interfaceCounters": {"outBroadcastPkts": 0, "outUcastPkts": 6075, "totalOutErrors": 0, "inMulticastPkts": 0, "counterRefreshTime": 1573852832.580422, "inBroadcastPkts": 0, "outputErrorsDetail": {"deferredTransmissions": 0, "txPause": 0, "collisions": 0, "lateCollisions": 0}, "inOctets": 0, "outDiscards": 0, "outOctets": 1075262, "inUcastPkts": 0, "inTotalPkts": 0, "inputErrorsDetail": {"runtFrames": 0, "rxPause": 0, "fcsErrors": 0, "alignmentErrors": 0, "giantFrames": 0, "symbolErrors": 0}, "linkStatusChanges": 3, "outMulticastPkts": 6075, "totalInErrors": 0, "inDiscards": 0},
             "interfaceAddress": [],
             "physicalAddress": "0c:ef:e6:c7:98:00",
             "description": ""
        }
    }}
    """

    routes = parse_show_interfaces_json(text)
    assert routes == [
        AristaInterface(
            name="Management1",
            mtu=1500,
            bandwidth=1000000000,
            line=True,
        ),
        AristaInterface(name="Ethernet1", mtu=1514, bandwidth=1, line=False),
    ]
