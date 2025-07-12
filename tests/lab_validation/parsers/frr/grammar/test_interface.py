from lab_validation.parsers.frr.grammar.interface import (
    _get_bandwidth,
    _get_iface_line,
    _get_iface_line_admin_down,
    _get_iface_line_admin_up,
    _get_mtu_speed,
    interface_block,
)


def test_interface_line() -> None:
    result = _get_iface_line_admin_up().parseString(
        "Interface lo is up, line protocol is up"
    )
    assert result.name == "lo"
    assert result.admin_state == "up"
    assert result.line_state == "up"

    result = _get_iface_line_admin_up().parseString(
        "Interface swp1 is up, line protocol is down"
    )
    assert result.name == "swp1"
    assert result.admin_state == "up"
    assert result.line_state == "down"

    result = _get_iface_line_admin_down().parseString("Interface swp1 is down")
    assert result.name == "swp1"
    assert result.admin_state == "down"

    # Testing appropriate line is being selected
    input_text = """
    Interface swp1 is down
    Interface swp1 is up, line protocol is down
    """
    result = _get_iface_line().parseString(input_text)
    assert result.name == "swp1"
    assert result.admin_state == "down"


def test_get_mtu_speed() -> None:
    result = _get_mtu_speed().parseString("mtu 1500 speed 1000")
    assert result.mtu == 1500
    assert result.speed == 1000


def test_get_bandwidth() -> None:
    result = _get_bandwidth().parseString("bandwidth 100 Mbps")
    assert result.bandwidth == 100
    assert result.bit_rate_unit == "Mbps"


def test_interface_block_admin_up() -> None:
    input_text = """
Interface swp1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  PTM status: disabled
  vrf: default
  index 3 metric 0 mtu 1500 speed 1000
  flags: <UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:01:7a:c6
  inet 10.127.0.1/31
  inet6 fe80::a00:27ff:fe01:7ac6/64
  Interface Type Other
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "swp1"
    assert interface.admin_state == "up"
    assert interface.line_state == "up"
    assert interface.mtu == 1500
    assert interface.speed == 1000


def test_interface_block_admin_down() -> None:
    input_text = """
Interface swp6 is down
  Link ups:       1    last: 2020/01/21 19:12:05.78
  Link downs:     6    last: 2020/01/22 01:46:14.67
  PTM status: disabled
  vrf: default
  index 8 metric 0 mtu 1500 speed 1000
  flags: <BROADCAST,PROMISC,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:a9:5f:fe
  Interface Type Other
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "swp6"
    assert interface.admin_state == "down"
    assert interface.mtu == 1500
    assert interface.speed == 1000
    assert interface.line_state == ""


def test_interface_block_user_defined_bandwidth() -> None:
    input_text = """
Interface swp1 is up, line protocol is up
  Link ups:       0    last: (never)
  Link downs:     0    last: (never)
  PTM status: disabled
  vrf: default
  index 3 metric 0 mtu 1500 speed 1000
  flags: <UP,BROADCAST,RUNNING,MULTICAST>
  Type: Ethernet
  HWaddr: 08:00:27:0f:c3:1c
  bandwidth 100 Mbps
  inet 10.127.0.9/31
  inet6 fe80::a00:27ff:fe0f:c31c/64
  Interface Type Other
    """
    interface = interface_block().parseString(input_text)
    assert interface.name == "swp1"
    assert interface.admin_state == "up"
    assert interface.mtu == 1500
    assert interface.speed == 1000
    assert interface.bandwidth == 100
    assert interface.line_state == "up"
