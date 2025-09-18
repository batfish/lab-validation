"""
Tests of IosXr interface show data extraction.
"""

from lab_validation.parsers.iosxr.commands.interfaces import parse_show_interfaces
from lab_validation.parsers.iosxr.models.interfaces import IosXrInterface


def test_parse_show_interfaces_multi_interface() -> None:
    """Test parsing for multiple different types of interfaces"""
    result = parse_show_interfaces(
        """Loopback123 is up, line protocol is up
  Interface state transitions: 1
  Hardware is Loopback interface(s)
  Internet address is 192.168.123.2/32
  MTU 1500 bytes, BW 0 Kbit
     reliability Unknown, txload Unknown, rxload Unknown
  Encapsulation Loopback,  loopback not set,
  Last link flapped 00:12:57
  Last input Unknown, output Unknown
  Last clearing of "show interface" counters Unknown
  Input/output data rate is disabled.
GigabitEthernet0/0/0/1 is up, line protocol is up
  Interface state transitions: 1
  Hardware is GigabitEthernet, address is 0c38.bb88.a104 (bia 0c38.bb88.a104)
  Description: Azure-EAST
  Internet address is Unknown
  MTU 1514 bytes, BW 1000000 Kbit (Max: 1000000 Kbit)
     reliability 255/255, txload 0/255, rxload 0/255
  Encapsulation ARPA,
  Duplex unknown, 1000Mb/s, link type is force-up
  output flow control is off, input flow control is off
  loopback not set,
  Last link flapped 00:12:08
  Last input 00:00:00, output 00:00:00
  Last clearing of "show interface" counters never
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     77 packets input, 6641 bytes, 0 total input drops
     0 drops for unrecognized upper-level protocol
     Received 0 broadcast packets, 0 multicast packets
              0 runts, 0 giants, 0 throttles, 0 parity
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored, 0 abort
     66 packets output, 9845 bytes, 0 total output drops
     Output 0 broadcast packets, 0 multicast packets
     0 output errors, 0 underruns, 0 applique, 0 resets
     0 output buffer failures, 0 output buffers swapped out
     0 carrier transitions
GigabitEthernet0/0/0/1.35 is up, line protocol is up
  Interface state transitions: 1
  Hardware is VLAN sub-interface(s), address is 0c38.bb88.a104
  Description: Azure-EAST
  Internet address is 10.103.127.5/30
  MTU 1518 bytes, BW 1000000 Kbit (Max: 1000000 Kbit)
     reliability 255/255, txload 0/255, rxload 0/255
  Encapsulation 802.1Q Virtual LAN, VLAN Id 35,  loopback not set,
  Last link flapped 00:12:08
  ARP type ARPA, ARP timeout 04:00:00
  Last input 00:00:39, output 00:00:39
  Last clearing of "show interface" counters never
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     31 packets input, 2181 bytes, 0 total input drops
     0 drops for unrecognized upper-level protocol
     Received 1 broadcast packets, 0 multicast packets
     31 packets output, 2257 bytes, 0 total output drops
     Output 1 broadcast packets, 0 multicast packets
GigabitEthernet0/0/0/2 is administratively down, line protocol is administratively down
  Interface state transitions: 0
  Hardware is GigabitEthernet, address is 0c38.bb88.a105 (bia 0c38.bb88.a105)
  Internet address is Unknown
  MTU 1514 bytes, BW 1000000 Kbit (Max: 1000000 Kbit)
     reliability 255/255, txload 0/255, rxload 0/255
  Encapsulation ARPA,
  Duplex unknown, 1000Mb/s, link type is force-up
  output flow control is off, input flow control is off
  loopback not set,
  Last input never, output never
  Last clearing of "show interface" counters never
  5 minute input rate 0 bits/sec, 0 packets/sec
  5 minute output rate 0 bits/sec, 0 packets/sec
     0 packets input, 0 bytes, 0 total input drops
     0 drops for unrecognized upper-level protocol
     Received 0 broadcast packets, 0 multicast packets
              0 runts, 0 giants, 0 throttles, 0 parity
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored, 0 abort
     0 packets output, 0 bytes, 0 total output drops
     Output 0 broadcast packets, 0 multicast packets
     0 output errors, 0 underruns, 0 applique, 0 resets
     0 output buffer failures, 0 output buffers swapped out
     0 carrier transitions
GigabitEthernet0/0/0/3 is up, line protocol is up
  Interface state transitions: 1
  Dampening enabled: penalty 0, not suppressed
    half-life:        5        reuse:             1000
    suppress:         2000     max-suppress-time: 20
    restart-penalty:  0
  Hardware is GigabitEthernet, address is 0c74.3a46.d804 (bia 0c74.3a46.d804)
  Description: something
  Internet address is Unknown
  MTU 9220 bytes, BW 1000000 Kbit (Max: 1000000 Kbit)
     reliability 255/255, txload 0/255, rxload 0/255
  Encapsulation ARPA,
  Duplex unknown, 1000Mb/s, link type is force-up
  output flow control is off, input flow control is off
  loopback not set,
  Last link flapped 00:13:53
  Last input 00:00:00, output 00:00:00
  Last clearing of "show interface" counters never
  30 second input rate 1000 bits/sec, 2 packets/sec
  30 second output rate 0 bits/sec, 0 packets/sec
     1383 packets input, 99568 bytes, 0 total input drops
     0 drops for unrecognized upper-level protocol
     Received 0 broadcast packets, 0 multicast packets
              0 runts, 0 giants, 0 throttles, 0 parity
     0 input errors, 0 CRC, 0 frame, 0 overrun, 0 ignored, 0 abort
     78 packets output, 9042 bytes, 0 total output drops
     Output 0 broadcast packets, 0 multicast packets
     0 output errors, 0 underruns, 0 applique, 0 resets
     0 output buffer failures, 0 output buffers swapped out
     0 carrier transitions
"""
    )
    assert result == [
        IosXrInterface(
            name="Loopback123",
            admin_state="up",
            line_protocol="up",
            prefix="192.168.123.2/32",
            mtu=1500,
            bw=0,
        ),
        IosXrInterface(
            name="GigabitEthernet0/0/0/1",
            admin_state="up",
            line_protocol="up",
            prefix=None,
            mtu=1514,
            bw=1000000,
        ),
        IosXrInterface(
            name="GigabitEthernet0/0/0/1.35",
            admin_state="up",
            line_protocol="up",
            prefix="10.103.127.5/30",
            mtu=1518,
            bw=1000000,
        ),
        IosXrInterface(
            name="GigabitEthernet0/0/0/2",
            admin_state="down",
            line_protocol="down",
            prefix=None,
            mtu=1514,
            bw=1000000,
        ),
        IosXrInterface(
            name="GigabitEthernet0/0/0/3",
            admin_state="up",
            line_protocol="up",
            prefix=None,
            mtu=9220,
            bw=1000000,
        ),
    ]
