from lab_validation.parsers.nxos.commands.interfaces import get_admin_state
from lab_validation.parsers.nxos.grammar.interface import (
    _get_admin_line,
    _get_iface_line,
    interface_block,
)


def test_interface_line() -> None:
    result = _get_iface_line().parseString("Ethernet1/1 is up")
    assert result.name == "Ethernet1/1"
    assert result.line_state == "up"

    result = _get_iface_line().parseString("mgmt0 is up")
    assert result.name == "mgmt0"
    assert result.line_state == "up"

    result = _get_iface_line().parseString("Ethernet1/1 is down")
    assert result.name == "Ethernet1/1"
    assert result.line_state == "down"

    result = _get_iface_line().parseString(
        "Ethernet1/4 is down (Administratively down)"
    )
    assert result.name == "Ethernet1/4"
    assert result.line_state == "down"

    result = _get_iface_line().parseString("Ethernet1/3 is down (Link not connected)")
    assert result.name == "Ethernet1/3"
    assert result.line_state == "down"


def test_get_iface_line_vlan() -> None:
    """test iface vlan line parsing"""
    result = _get_iface_line().parseString(
        "Vlan200 is up, line protocol is up, autostate enabled"
    )
    assert result.name == "Vlan200"
    assert result.admin_state == "up"
    assert result.line_state == "up"

    result = _get_iface_line().parseString(
        "Vlan1 is down (Administratively down), line protocol is down, autostate enabled"
    )
    assert result.name == "Vlan1"
    assert result.admin_state == "down"
    assert result.line_state == "down"

    result = _get_iface_line().parseString(
        "Vlan10 is down (VLAN/BD is down), line protocol is down, autostate enabled"
    )
    assert result.name == "Vlan10"
    assert result.admin_state == "down"
    assert result.line_state == "down"

    result = _get_iface_line().parseString(
        "Vlan506 is down (VLAN/BD does not exist), line protocol is down, autostate enabled"
    )
    assert result.name == "Vlan506"
    assert result.admin_state == "down"
    assert result.line_state == "down"


def test_admin_line() -> None:
    result = _get_admin_line().parseString("admin state is up, Dedicated Interface")
    assert result.admin_state == "up"

    result = _get_admin_line().parseString("admin state is down, Dedicated Interface")
    assert result.admin_state == "down"


def test_parse_record_no_mode() -> None:
    input_text = """
   mgmt0 is up
admin state is up,
  Hardware: Ethernet, address: 0cef.e67a.9100 (bia 0cef.e67a.9100)
  MTU 1500 bytes, BW 1000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA, medium is broadcast
  full-duplex, 1000 Mb/s
  Auto-Negotiation is turned on
  Auto-mdix is turned off
  EtherType is 0x0000
  1 minute input rate 0 bits/sec, 0 packets/sec
  1 minute output rate 0 bits/sec, 0 packets/sec
  Rx
    0 input packets 0 unicast packets 0 multicast packets
    0 broadcast packets 0 bytes
  Tx
    284 output packets 0 unicast packets 284 multicast packets
    0 broadcast packets 61336 bytes
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "mgmt0"
    assert interface.admin_state == "up"
    assert interface.line_state == "up"
    assert interface.mtu == 1500
    assert interface.bw == 1000000
    assert interface.mode == ""


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
    interface = interface_block().parseString(input_text)
    assert interface.name == "Ethernet1/2"
    assert interface.admin_state == "up"
    assert interface.line_state == "up"
    assert interface.mtu == 1500
    assert interface.bw == 10000000
    assert interface.mode == "trunk"


def test_parse_record_without_admin_state() -> None:
    input_text = """
Ethernet1/1 is up
 Dedicated Interface
  Belongs to Po111
  Hardware: 100/1000/10000 Ethernet, address: 1c6a.7a4b.b5e8 (bia 1c6a.7a4b.b5e8)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA
  Port mode is trunk
  full-duplex, 10 Gb/s, media type is 10G
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "Ethernet1/1"
    assert interface.admin_state == ""
    assert interface.line_state == "up"
    assert interface.mtu == 1500
    assert interface.bw == 10000000
    assert interface.mode == "trunk"

    input_text = """
Ethernet1/4 is down (Administratively down)
 Dedicated Interface
  Hardware: 100/1000/10000 Ethernet, address: 1c6a.7a4b.b5eb (bia 1c6a.7a4b.b5eb)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA
  Port mode is access
  Full-duplex, 10 Gb/s, media type is 10G
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "Ethernet1/4"
    assert interface.admin_state == ""
    assert interface.line_state == "down"
    assert interface.mtu == 1500
    assert interface.bw == 10000000
    assert interface.mode == "access"

    input_text = """
Ethernet1/8 is down (Link not connected)
 Dedicated Interface
  Hardware: 100/1000/10000 Ethernet, address: 1c6a.7a4b.b5ef (bia 1c6a.7a4b.b5ef)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA
  Port mode is trunk
  Full-duplex, 10 Gb/s, media type is 10G
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "Ethernet1/8"
    assert interface.admin_state == ""
    assert interface.line_state == "down"
    assert interface.mtu == 1500
    assert interface.bw == 10000000
    assert interface.mode == "trunk"

    input_text = """
Ethernet1/16 is down (SFP not inserted)
 Dedicated Interface
  Hardware: 100/1000/10000 Ethernet, address: 1c6a.7a4b.b5f7 (bia 1c6a.7a4b.b5f7)
  MTU 1500 bytes, BW 10000000 Kbit, DLY 10 usec
  reliability 255/255, txload 1/255, rxload 1/255
  Encapsulation ARPA
  Port mode is access
  Full-duplex, 10 Gb/s
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "Ethernet1/16"
    assert interface.admin_state == ""
    assert interface.line_state == "down"
    assert interface.mtu == 1500
    assert interface.bw == 10000000
    assert interface.mode == "access"


def test_get_admin_state() -> None:
    admin_state = None
    port_status_reason = "(Administratively down)"
    assert get_admin_state(admin_state, port_status_reason) is False

    admin_state = None
    port_status_reason = "(Link not connected)"
    assert get_admin_state(admin_state, port_status_reason) is True

    admin_state = "down"
    port_status_reason = "(Link not connected)"
    assert get_admin_state(admin_state, port_status_reason) is False

    admin_state = "up"
    port_status_reason = "(Link not connected)"
    assert get_admin_state(admin_state, port_status_reason) is True
