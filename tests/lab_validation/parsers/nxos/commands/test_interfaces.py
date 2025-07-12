from lab_validation.parsers.nxos.commands.interfaces import parse_show_interface
from lab_validation.parsers.nxos.models.interfaces import NxosInterface


def test_parse_record() -> None:
    input_text = """Ethernet1/2 is up
admin state is up, Dedicated Interface
  Hardware: 1000/10000 Ethernet, address: 0022.beee.ffff (bia 0022.beee.ffff)
  Description: some description
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  Port mode is trunk
  full-duplex, 10 Gb/s, media type is 10G
  Beacon is turned off
  Auto-Negotiation is turned on, FEC mode is Auto
  Input flow-control is off, output flow-control is off
  Auto-mdix is turned off
  Rate mode is dedicated
  Switchport monitor is off
  EtherType is 0x8100
  EEE (efficient-ethernet) : n/a
  Last link flapped 52week(s) 6day(s)
  Last clearing of "show interface" counters never
  1 interface resets
  30 seconds input rate 12024 bits/sec, 15 packets/sec
  30 seconds output rate 560 bits/sec, 0 packets/sec
  Load-Interval #2: 5 minute (300 seconds)
    input rate 12.40 Kbps, 14 pps; output rate 488 bps, 0 pps
  RX
    279358201 unicast packets  497103634 multicast packets  78802922 broadcast packets
    855264757 input packets  463384312396 bytes
    267499565 jumbo packets  0 storm suppression packets
    0 runts  0 giants  0 CRC  0 no buffer
    0 input error  0 short frame  0 overrun   0 underrun  0 ignored
    0 watchdog  0 bad etype drop  0 bad proto drop  0 if down drop
    0 input with dribble  0 input discard
    0 Rx pause
  TX
    0 unicast packets  17612612 multicast packets  0 broadcast packets
    17612612 output packets  2463101780 bytes
    0 jumbo packets
    0 output error  0 collision  0 deferred  0 late collision
    0 lost carrier  0 no carrier  0 babble  0 output discard
    0 Tx pause"""
    interfaces = parse_show_interface(input_text)
    assert interfaces == [
        NxosInterface(
            name="Ethernet1/2",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=10000000 * 1000,
            mode="trunk",
        )
    ]


def test_parse_multi_record() -> None:
    # truncate the records
    input_text = """Ethernet1/2 is up
admin state is up, Dedicated Interface
  Hardware: 1000/10000 Ethernet, address: 0022.beee.ffff (bia 0022.beee.ffff)
  Description: some description
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast

  Ethernet1/3 is up
admin state is up, Dedicated Interface
  Hardware: 1000/10000 Ethernet, address: 0022.beee.ffff (bia 0022.beee.ffff)
  Description: some description
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  Port mode is access
    """
    interfaces = parse_show_interface(input_text)
    assert interfaces == [
        NxosInterface(
            name="Ethernet1/2",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=10000000 * 1000,
            mode=None,
        ),
        NxosInterface(
            name="Ethernet1/3",
            admin=True,
            line=True,
            mtu=1500,
            bandwidth=10000000 * 1000,
            mode="access",
        ),
    ]
