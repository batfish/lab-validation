"""
Tests of the common IOS model for show interfaces, using IOS show data.
"""

from lab_validation.parsers.ios.commands.interfaces import (
    _convert_speed,
    parse_show_interfaces,
)


def test_parse_interfaces() -> None:
    ifs = parse_show_interfaces(
        """GigabitEthernet1 is up, line protocol is up
  Hardware is CSR vNIC, address is 0cef.e6a2.dd00 (bia 0cef.e6a2.dd00)
  Internet address is 192.168.122.2/24
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, loopback not set
  Keepalive set (10 sec)
  Full Duplex, 1000Mbps, link type is auto, media type is RJ45
  output flow-control is unsupported, input flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:00, output 00:00:18, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/375/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 5000 bits/sec, 2 packets/sec
  5 minute output rate 3000 bits/sec, 2 packets/sec
     22857 packets input, 3254176 bytes, 0 no buffer
     Received 0 broadcasts (0 IP multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 0 multicast, 0 pause input
     15337 packets output, 3269033 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out"""
    )
    assert ifs == {
        "GigabitEthernet1": {
            "bandwidth": 1000000,
            "enabled": True,
            "ipv4": {"192.168.122.2/24": None},
            "line_protocol": "up",
            "mtu": 1500,
        }
    }


def test_parse_show_interfaces_subinterface() -> None:
    result = parse_show_interfaces(
        """
        GigabitEthernet0/0.313 is up, line protocol is up
  Hardware is iGbE, address is 0ce2.f1d3.0100 (bia 0ce2.f1d3.0100)
  Internet address is 1.2.3.4/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation 802.1Q Virtual LAN, Vlan ID  313.
  ARP type: ARPA, ARP Timeout 04:00:00
  Keepalive set (10 sec)
  Last clearing of "show interface" counters never
        """
    )
    assert result == {
        "GigabitEthernet0/0.313": {
            "bandwidth": 1000000,
            "enabled": True,
            "ipv4": {"1.2.3.4/30": None},
            "line_protocol": "up",
            "mtu": 1500,
        }
    }


def test_parse_show_interfaces_multi_interface() -> None:
    "Test parsing for multiple different types of interfaces"
    result = parse_show_interfaces(
        """
GigabitEthernet0/0 is up, line protocol is up
  Hardware is iGbE, address is 0ce2.f1d3.0100 (bia 0ce2.f1d3.0100)
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation 802.1Q Virtual LAN, Vlan ID  1., loopback not set
  Keepalive set (10 sec)
  Auto Duplex, Auto Speed, link type is auto, media type is RJ45
  output flow-control is unsupported, input flow-control is unsupported
  ARP type: ARPA, ARP Timeout 04:00:00
  Last input 00:00:00, output 00:00:00, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/40 (size/max)
  5 minute input rate 2000 bits/sec, 3 packets/sec
  5 minute output rate 2000 bits/sec, 3 packets/sec
     419300 packets input, 29754759 bytes, 0 no buffer
     Received 12 broadcasts (0 IP multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored
     0 watchdog, 0 multicast, 0 pause input
     388593 packets output, 27533775 bytes, 0 underruns
     0 output errors, 0 collisions, 1 interface resets
     5308 unknown protocol drops
     0 babbles, 0 late collision, 0 deferred
     0 lost carrier, 0 no carrier, 0 pause output
     0 output buffer failures, 0 output buffers swapped out
GigabitEthernet0/0.313 is up, line protocol is up
  Hardware is iGbE, address is 0ce2.f1d3.0100 (bia 0ce2.f1d3.0100)
  Internet address is 1.2.3.4/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation 802.1Q Virtual LAN, Vlan ID  313.
  ARP type: ARPA, ARP Timeout 04:00:00
  Keepalive set (10 sec)
  Last clearing of "show interface" counters never
GigabitEthernet0/0.314 is up, line protocol is up
  Hardware is iGbE, address is 0ce2.f1d3.0100 (bia 0ce2.f1d3.0100)
  Internet address is 5.6.7.8/30
  MTU 1500 bytes, BW 1000000 Kbit/sec, DLY 10 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation 802.1Q Virtual LAN, Vlan ID  314.
  ARP type: ARPA, ARP Timeout 04:00:00
  Keepalive set (10 sec)
  Last clearing of "show interface" counters never
Loopback123 is up, line protocol is up
  Hardware is Loopback
  Internet address is 192.168.123.2/32
  MTU 1514 bytes, BW 8000000 Kbit/sec, DLY 5000 usec,
     reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation LOOPBACK, loopback not set
  Keepalive set (10 sec)
  Last input never, output never, output hang never
  Last clearing of "show interface" counters never
  Input queue: 0/75/0/0 (size/max/drops/flushes); Total output drops: 0
  Queueing strategy: fifo
  Output queue: 0/0 (size/max)
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     0 packets input, 0 bytes, 0 no buffer
     Received 0 broadcasts (0 IP multicasts)
     0 runts, 0 giants, 0 throttles
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored, 0 abort
     0 packets output, 0 bytes, 0 underruns
     0 output errors, 0 collisions, 0 interface resets
     0 unknown protocol drops
     0 output buffer failures, 0 output buffers swapped out
        """
    )
    assert result == {
        "GigabitEthernet0/0": {
            "bandwidth": 1000000,
            "enabled": True,
            "ipv4": {},
            "line_protocol": "up",
            "mtu": 1500,
        },
        "GigabitEthernet0/0.313": {
            "bandwidth": 1000000,
            "enabled": True,
            "ipv4": {"1.2.3.4/30": None},
            "line_protocol": "up",
            "mtu": 1500,
        },
        "GigabitEthernet0/0.314": {
            "bandwidth": 1000000,
            "enabled": True,
            "ipv4": {"5.6.7.8/30": None},
            "line_protocol": "up",
            "mtu": 1500,
        },
        "Loopback123": {
            "bandwidth": 8000000,
            "enabled": True,
            "ipv4": {"192.168.123.2/32": None},
            "line_protocol": "up",
            "mtu": 1514,
        },
    }


def test_convert_speed() -> None:
    assert _convert_speed("5mbps") == 5e6
    assert _convert_speed("5Mbps") == 5e6
    assert _convert_speed("5kbps") == 5e3
    assert _convert_speed("501gbps") == 501e9
    assert _convert_speed(None) is None
    assert _convert_speed("123456") == 123456.0
