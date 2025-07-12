# coding: utf-8
from lab_validation.parsers.junos.grammar.interface import (
    _logical_name_line,
    _logical_record,
    _physical_name_line,
    _physical_record,
    _physical_type_line,
    show_interface,
)


def test_show_interface_coverage() -> None:
    interfaces = show_interface().parseString(
        """
Physical interface: gr-0/0/0, Enabled, Physical link is Up
  Interface index: 645, SNMP ifIndex: 504
  Type: GRE, Link-level type: GRE, MTU: Unlimited, Speed: 800mbps
  Device flags   : Present Running
  Interface flags: Point-To-Point SNMP-Traps
  Input rate     : 0 bps (0 pps)
  Output rate    : 0 bps (0 pps)

Physical interface: bme0, Enabled, Physical link is Up
  Interface index: 64, SNMP ifIndex: 37
  Type: Ethernet, Link-level type: Ethernet, MTU: 2000
  Device flags   : Present Running
  Link flags     : None
  Current address: 02:00:00:00:00:0a, Hardware address: 02:00:00:00:00:0a
  Last flapped   : Never
    Input packets : 0
    Output packets: 4

  Logical interface bme0.0 (Index 6) (SNMP ifIndex 220)
    Flags: Up 0x4000000 Encapsulation: ENET2
    Input packets : 0
    Output packets: 4
    Protocol inet, MTU: 1986
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Is-Primary
      Addresses, Flags: Primary Is-Default Is-Preferred Is-Primary
        Destination: 128/2, Local: 128.0.0.1, Broadcast: 191.255.255.255
      Addresses, Flags: Primary
        Destination: 128/2, Local: 128.0.0.4, Broadcast: 191.255.255.255
      Addresses, Flags: Primary
        Destination: 128/2, Local: 128.0.0.16, Broadcast: 191.255.255.255
      Addresses, Flags: Primary
        Destination: 128/2, Local: 128.0.0.63, Broadcast: 191.255.255.255

Physical interface: cbp0, Enabled, Physical link is Up
  Interface index: 643, SNMP ifIndex: 501
  Type: Ethernet, Link-level type: Ethernet, MTU: 9192
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:fb:14, Hardware address: 02:05:86:71:fb:14
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: dsc, Enabled, Physical link is Up
  Interface index: 5, SNMP ifIndex: 5
  Type: Software-Pseudo, MTU: Unlimited
  Device flags   : Present Running
  Interface flags: Point-To-Point SNMP-Traps
  Link flags     : None
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: em0, Enabled, Physical link is Up
  Interface index: 8, SNMP ifIndex: 17
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Current address: 0c:ef:e6:97:ab:00, Hardware address: 0c:ef:e6:97:ab:00
  Last flapped   : 2019-11-11 16:16:56 UTC (04:45:27 ago)
    Input packets : 3272
    Output packets: 2551

  Logical interface em0.0 (Index 7) (SNMP ifIndex 18)
    Flags: Up SNMP-Traps 0x4000000 Encapsulation: ENET2
    Input packets : 3272
    Output packets: 2551
    Protocol inet, MTU: 1500
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 1, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Sendbcast-pkt-to-re
      Addresses, Flags: Is-Preferred Is-Primary
        Destination: 10.10.50/24, Local: 10.10.50.2, Broadcast: 10.10.50.255

Physical interface: em1, Enabled, Physical link is Up
  Interface index: 9, SNMP ifIndex: 23
  Type: Ethernet, Link-level type: Ethernet, MTU: 9500, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Current address: 0c:ef:e6:97:ab:01, Hardware address: 0c:ef:e6:97:ab:01
  Last flapped   : 2019-11-11 16:16:57 UTC (04:45:26 ago)
    Input packets : 0
    Output packets: 1150

  Logical interface em1.0 (Index 3) (SNMP ifIndex 24)
    Flags: Up SNMP-Traps 0x4000 Encapsulation: ENET2
    Input packets : 0
    Output packets: 1150
    Protocol inet, MTU: 9486
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 1, Curr new hold cnt: 1, NH drop cnt: 0
      Flags: Sendbcast-pkt-to-re, Is-Primary
      Addresses, Flags: Is-Preferred Is-Primary
        Destination: 169.254.0/24, Local: 169.254.0.2, Broadcast: 169.254.0.255

Physical interface: em2, Enabled, Physical link is Up
  Interface index: 71, SNMP ifIndex: 116
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:02, Hardware address: 0c:ef:e6:97:ab:02
  Last flapped   : 2019-11-11 16:16:57 UTC (04:45:26 ago)
    Input packets : 0
    Output packets: 22

  Logical interface em2.32768 (Index 4) (SNMP ifIndex 118)
    Flags: Up SNMP-Traps Encapsulation: ENET2
    Input packets : 0
    Output packets: 22
    Protocol inet, MTU: 1500
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Is-Primary
      Addresses, Flags: Primary Preferred Is-Default Is-Preferred Is-Primary
        Destination: 192.168.1/24, Local: 192.168.1.2, Broadcast: 192.168.1.255

Physical interface: em3, Enabled, Physical link is Up
  Interface index: 70, SNMP ifIndex: 152
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:03, Hardware address: 0c:ef:e6:97:ab:03
  Last flapped   : 2019-11-11 16:16:57 UTC (04:45:26 ago)
    Input packets : 0
    Output packets: 0

Physical interface: em4, Enabled, Physical link is Up
  Interface index: 69, SNMP ifIndex: 154
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:04, Hardware address: 0c:ef:e6:97:ab:04
  Last flapped   : 2019-11-11 16:16:57 UTC (04:45:26 ago)
    Input packets : 0
    Output packets: 0

  Logical interface em4.32768 (Index 5) (SNMP ifIndex 502)
    Flags: Up SNMP-Traps Encapsulation: ENET2
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: 1500
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: None
      Addresses, Flags: Primary Preferred Is-Preferred Is-Primary
        Destination: 192.0.2/24, Local: 192.0.2.2, Broadcast: 192.0.2.255

Physical interface: em5, Enabled, Physical link is Up
  Interface index: 68, SNMP ifIndex: 156
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:05, Hardware address: 0c:ef:e6:97:ab:05
  Last flapped   : 2019-11-11 16:16:58 UTC (04:45:25 ago)
    Input packets : 0
    Output packets: 0

Physical interface: em6, Enabled, Physical link is Up
  Interface index: 67, SNMP ifIndex: 158
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:06, Hardware address: 0c:ef:e6:97:ab:06
  Last flapped   : 2019-11-11 16:16:58 UTC (04:45:25 ago)
    Input packets : 0
    Output packets: 0

Physical interface: em7, Enabled, Physical link is Up
  Interface index: 66, SNMP ifIndex: 160
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514, Speed: 1000mbps
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 0c:ef:e6:97:ab:07, Hardware address: 0c:ef:e6:97:ab:07
  Last flapped   : 2019-11-11 16:16:58 UTC (04:45:25 ago)
    Input packets : 0
    Output packets: 0

Physical interface: esi, Enabled, Physical link is Up
  Interface index: 642, SNMP ifIndex: 503
  Type: Software-Pseudo, Link-level type: VxLAN-Tunnel-Endpoint, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: gre, Enabled, Physical link is Up
  Interface index: 10, SNMP ifIndex: 8
  Type: GRE, Link-level type: GRE, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Interface flags: Point-To-Point SNMP-Traps
    Input packets : 0
    Output packets: 0

Physical interface: ipip, Enabled, Physical link is Up
  Interface index: 11, SNMP ifIndex: 9
  Type: IPIP, Link-level type: IP-over-IP, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Interface flags: SNMP-Traps
    Input packets : 0
    Output packets: 0

Physical interface: irb, Enabled, Physical link is Up
  Interface index: 640, SNMP ifIndex: 505
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:fb:00, Hardware address: 02:05:86:71:fb:00
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: jsrv, Enabled, Physical link is Up
  Interface index: 646, SNMP ifIndex: 508
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514
  Device flags   : Present Running
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:fb:00, Hardware address: 02:05:86:71:fb:00
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

  Logical interface jsrv.1 (Index 545) (SNMP ifIndex 509)
    Flags: Up 0x24004000 Encapsulation: unknown
    Bandwidth: 1000mbps
    Routing Instance: None Bridging Domain: None
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: 1514
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Is-Primary
      Addresses, Flags: Primary Is-Default Is-Preferred Is-Primary
        Destination: 128/2, Local: 128.0.0.127, Broadcast: 191.255.255.255

Physical interface: lo0, Enabled, Physical link is Up
  Interface index: 6, SNMP ifIndex: 6
  Type: Loopback, MTU: Unlimited
  Device flags   : Present Running Loopback
  Interface flags: SNMP-Traps
  Link flags     : None
  Last flapped   : Never
    Input packets : 20802
    Output packets: 20802

  Logical interface lo0.0 (Index 552) (SNMP ifIndex 16)
    Flags: SNMP-Traps Encapsulation: Unspecified
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: Unlimited
    Max nh cache: 0, New hold nh limit: 0, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Sendbcast-pkt-to-re
      Addresses, Flags: Is-Default Is-Primary
        Local: 192.168.123.6
    Protocol inet6, MTU: Unlimited
    Max nh cache: 0, New hold nh limit: 0, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: None
        Local: fe80::205:860f:fc71:fb00

  Logical interface lo0.10 (Index 558) (SNMP ifIndex 510)
    Flags: SNMP-Traps Encapsulation: Unspecified
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: Unlimited
    Max nh cache: 0, New hold nh limit: 0, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Sendbcast-pkt-to-re
      Addresses, Flags: Is-Default Is-Primary
        Local: 1.1.6.10

  Logical interface lo0.20 (Index 559) (SNMP ifIndex 511)
    Flags: SNMP-Traps Encapsulation: Unspecified
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: Unlimited
    Max nh cache: 0, New hold nh limit: 0, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Sendbcast-pkt-to-re
      Addresses, Flags: Is-Default Is-Primary
        Local: 1.1.6.20

  Logical interface lo0.16385 (Index 555) (SNMP ifIndex 22)
    Flags: SNMP-Traps Encapsulation: Unspecified
    Input packets : 20686
    Output packets: 20686
    Protocol inet, MTU: Unlimited
    Max nh cache: 0, New hold nh limit: 0, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: None

Physical interface: lsi, Enabled, Physical link is Up
  Interface index: 4, SNMP ifIndex: 4
  Type: Software-Pseudo, Link-level type: LSI, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Link flags     : None
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: mtun, Enabled, Physical link is Up
  Interface index: 65, SNMP ifIndex: 12
  Type: Multicast-GRE, Link-level type: GRE, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Interface flags: SNMP-Traps
    Input packets : 0
    Output packets: 0

Physical interface: pimd, Enabled, Physical link is Up
  Interface index: 26, SNMP ifIndex: 11
  Type: PIMD, Link-level type: PIM-Decapsulator, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
    Input packets : 0
    Output packets: 0

Physical interface: pime, Enabled, Physical link is Up
  Interface index: 25, SNMP ifIndex: 10
  Type: PIME, Link-level type: PIM-Encapsulator, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
    Input packets : 0
    Output packets: 0

Physical interface: pip0, Enabled, Physical link is Up
  Interface index: 644, SNMP ifIndex: 506
  Type: Ethernet, Link-level type: Ethernet, MTU: 9192
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:f6:df, Hardware address: 02:05:86:71:f6:df
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: tap, Enabled, Physical link is Up
  Interface index: 12, SNMP ifIndex: 7
  Type: Software-Pseudo, Link-level type: Interface-Specific, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Interface flags: SNMP-Traps
  Link flags     : None
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: vme, Enabled, Physical link is Down
  Interface index: 72, SNMP ifIndex: 35
  Type: Mgmt-VLAN, Link-level type: Mgmt-VLAN, MTU: 1514
  Device flags   : Present Running
  Interface flags: Hardware-Down SNMP-Traps
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:fb:01, Hardware address: 02:05:86:71:fb:01
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

Physical interface: vtep, Enabled, Physical link is Up
  Interface index: 641, SNMP ifIndex: 507
  Type: Software-Pseudo, Link-level type: VxLAN-Tunnel-Endpoint, MTU: Unlimited, Speed: Unlimited
  Device flags   : Present Running
  Link type      : Full-Duplex
  Link flags     : None
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

    """
    )
    assert len(interfaces) == 36


def test_show_interface() -> None:
    interfaces = show_interface().parseString(
        """
Physical interface: jsrv, Enabled, Physical link is Up
  Interface index: 646, SNMP ifIndex: 508
  Type: Ethernet, Link-level type: Ethernet, MTU: 1514
  Device flags   : Present Running
  Link type      : Full-Duplex
  Link flags     : None
  Current address: 02:05:86:71:20:00, Hardware address: 02:05:86:71:20:00
  Last flapped   : Never
    Input packets : 0
    Output packets: 0

  Logical interface jsrv.1 (Index 548) (SNMP ifIndex 509)
    Flags: Up 0x24004000 Encapsulation: unknown
    Bandwidth: 1000mbps
    Routing Instance: None Bridging Domain: None
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: 1514
    Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
      Flags: Is-Primary
      Addresses, Flags: Primary Is-Default Is-Preferred Is-Primary
        Destination: 128/2, Local: 128.0.0.127, Broadcast: 191.255.255.255
        """
    )
    assert len(interfaces) == 2
    interface = interfaces[0]
    assert (
        interface.admin_state == "Enabled"
        and interface.line_state == "Up"
        and interface.mtu == "1514"
        and interface.name == "jsrv"
    )

    interface = interfaces[1]
    assert (
        interface.bw == "1000mbps"
        and interface.mtu == "1514"
        and interface.name == "jsrv.1"
    )


def test_physical_record() -> None:
    result = _physical_record().parseString(
        """
        Physical interface: bme0, Enabled, Physical link is Up
      Interface index: 64, SNMP ifIndex: 37
      Type: Ethernet, Link-level type: Ethernet, MTU: 2000, Speed: 10mbps
      Device flags   : Present Running
      Link flags     : None
      Current address: 02:00:00:00:00:0a, Hardware address: 02:00:00:00:00:0a
      Last flapped   : Never
        Input packets : 0
        Output packets: 4
        """
    )
    assert result.name == "bme0"
    assert result.admin_state == "Enabled"
    assert result.line_state == "Up"
    assert result.mtu == "2000"
    assert result.speed == "10mbps"
    assert result.type == "Physical interface"


def test_physical_record_no_link_level() -> None:
    result = _physical_record().parseString(
        """
        Physical interface: dsc, Enabled, Physical link is Up
          Interface index: 5, SNMP ifIndex: 5
          Type: Software-Pseudo, MTU: Unlimited
          Device flags   : Present Running
          Interface flags: Point-To-Point SNMP-Traps
          Link flags     : None
          Last flapped   : Never
            Input packets : 0
            Output packets: 0
        """
    )
    assert result.name == "dsc"
    assert result.admin_state == "Enabled"
    assert result.line_state == "Up"
    assert result.mtu == "Unlimited"
    assert result.bw == ""
    assert result.type == "Physical interface"


def test_physical_name_line() -> None:
    result = _physical_name_line().parseString(
        "Physical interface: gr-0/0/0, Enabled, Physical link is Up"
    )
    assert result.name == "gr-0/0/0"
    assert result.admin_state == "Enabled"
    assert result.line_state == "Up"
    assert result.type == "Physical interface"


def test_physical_type_line() -> None:
    result = _physical_type_line().parseString(
        "Type: GRE, Link-level type: GRE, MTU: Unlimited, Speed: 800mbps"
    )
    assert result.speed == "800mbps"
    assert result.mtu == "Unlimited"

    result = _physical_type_line().parseString(
        "Type: GRE, Link-level type: GRE, MTU: 2000"
    )
    assert "speed" not in result
    assert result.mtu == "2000"


def test_logical_record_with_bw() -> None:
    result = _logical_record().parseString(
        """Logical interface jsrv.1 (Index 548) (SNMP ifIndex 509)
    Flags: Up 0x24004000 Encapsulation: unknown
    Bandwidth: 1000mbps
    Routing Instance: None Bridging Domain: None
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: 1514
        """
    )
    assert result.name == "jsrv.1"
    assert result.mtu == "1514"
    assert result.bw == "1000mbps"
    assert result.type == "Logical interface"
    assert result.admin_state == "Up"


def test_logical_record_no_bw() -> None:
    result = _logical_record().parseString(
        """
      Logical interface bme0.0 (Index 6) (SNMP ifIndex 220)
        Flags: Up 0x4000000 Encapsulation: ENET2
        Input packets : 0
        Output packets: 4
        Protocol inet, MTU: 1986
        Max nh cache: 75000, New hold nh limit: 75000, Curr nh cnt: 0, Curr new hold cnt: 0, NH drop cnt: 0
          Flags: Is-Primary
          Addresses, Flags: Primary Is-Default Is-Preferred Is-Primary
            Destination: 128/2, Local: 128.0.0.1, Broadcast: 191.255.255.255
          Addresses, Flags: Primary
            Destination: 128/2, Local: 128.0.0.4, Broadcast: 191.255.255.255
          Addresses, Flags: Primary
            Destination: 128/2, Local: 128.0.0.16, Broadcast: 191.255.255.255
          Addresses, Flags: Primary
            Destination: 128/2, Local: 128.0.0.63, Broadcast: 191.255.255.255
        """
    )
    assert result.name == "bme0.0"
    assert result.mtu == "1986"
    assert result.bw == ""
    assert result.type == "Logical interface"
    assert result.admin_state == "Up"


def test_logical_record_admin_state_down() -> None:
    result = _logical_record().parseString(
        """Logical interface jsrv.1 (Index 548) (SNMP ifIndex 509)
    Flags: Down 0x24004000 Encapsulation: unknown
    Bandwidth: 1000mbps
    Routing Instance: None Bridging Domain: None
    Input packets : 0
    Output packets: 0
    Protocol inet, MTU: 1514
        """
    )
    assert result.name == "jsrv.1"
    assert result.mtu == "1514"
    assert result.bw == "1000mbps"
    assert result.type == "Logical interface"
    assert result.admin_state == "Down"


def test_logical_name_line() -> None:
    result = _logical_name_line().parseString(
        "Logical interface bme0.0 (Index 4) (SNMP ifIndex 220)\n"
    )
    assert result.name == "bme0.0"
    assert result.type == "Logical interface"
